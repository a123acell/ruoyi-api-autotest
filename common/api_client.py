# -*- coding: utf-8 -*-
"""统一请求层：所有用例只跟 ApiClient 打交道，不直接调 requests。

集中管理五件事：
  1. base_url 拼接与默认超时，避免每个用例各写一遍 f"{BASE_URL}{path}" 和 timeout=10；
  2. 鉴权头注入：绑定了 Token 的客户端自动带 Authorization，匿名请求显式 auth=False；
  3. 统一响应解析：一律返回 body 的 JSON（若依的业务码在 body.code，HTTP 状态码恒为 200）；
  4. Token 失效自愈：带 Token 的请求遇到 401 自动重登一次并重试。匿名请求不重试，
     否则会把「未认证应返回 401」的用例刷成 200；
  5. 可观测性：每次请求计时并记日志，同时留档最近几次「请求-响应」，
     用例失败时由 conftest 挂到 Allure 附件，不用再靠复现去猜现场。
"""
import logging
import time
from collections import deque

import requests

from config import BASE_URL, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

# 最近若干次「请求-响应」交换。用例失败时由 conftest.pytest_runtest_makereport 读取并挂到 Allure。
# 只留最近 5 次，够定位问题又不会让报告变臃肿。
RECENT_EXCHANGES = deque(maxlen=5)


class ApiClient:
    """带会话复用、鉴权自愈与请求留痕的 HTTP 客户端。"""

    def __init__(self, base_url=BASE_URL, timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.token = None
        self._renew_token = None
        # 最近一次请求的耗时（毫秒），供响应时间断言使用（见 test_perf.py）
        self.last_elapsed_ms = None

    def set_token(self, token, renew_token=None):
        """绑定 Token。renew_token 是「重新登录并返回新 Token」的可调用对象，供 401 自愈使用。"""
        self.token = token
        self._renew_token = renew_token
        return self

    def request(self, method, path, auth=True, **kwargs):
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        kwargs.setdefault("timeout", self.timeout)
        if auth:
            kwargs["headers"] = self._headers(kwargs.get("headers"))

        data = self._send(method, url, kwargs)

        if auth and self.token and data.get("code") == 401 and self._renew_token:
            logger.warning("%s %s 返回 401，Token 可能已失效，重新登录后重试一次", method, url)
            self.token = self._renew_token()
            kwargs["headers"] = self._headers(kwargs.get("headers"))
            data = self._send(method, url, kwargs)
        return data

    def get(self, path, auth=True, **kwargs):
        return self.request("GET", path, auth=auth, **kwargs)

    def post(self, path, auth=True, **kwargs):
        return self.request("POST", path, auth=auth, **kwargs)

    def put(self, path, auth=True, **kwargs):
        return self.request("PUT", path, auth=auth, **kwargs)

    def delete(self, path, auth=True, **kwargs):
        return self.request("DELETE", path, auth=auth, **kwargs)

    def _send(self, method, url, kwargs):
        """发一次请求：计时、记日志、留档现场，返回解析后的响应体。"""
        started = time.perf_counter()
        resp = self.session.request(method, url, **kwargs)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        self.last_elapsed_ms = elapsed_ms

        data = self._parse(resp)
        logger.info("%s %s -> code=%s (%.1f ms)", method, url, data.get("code"), elapsed_ms)
        # 成功响应只留一行摘要，异常响应才把完整 body 写进日志，避免日志被正常报文淹没
        if data.get("code") != 200:
            logger.debug("非 200 响应体 %s %s: %s", method, url, data)
        RECENT_EXCHANGES.append({
            "method": method,
            "url": url,
            "request_body": kwargs.get("json") or kwargs.get("params"),
            "request_headers": self._masked(kwargs.get("headers")),
            "http_status": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "response": data,
        })
        return data

    def _headers(self, extra):
        headers = dict(extra or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def _masked(headers):
        """留档时把 Authorization 打码，避免 Token 明文进报告。"""
        masked = dict(headers or {})
        if "Authorization" in masked:
            masked["Authorization"] = "Bearer ***"
        return masked

    @staticmethod
    def _parse(resp):
        """正常响应取 JSON；网关返回 HTML 错误页等非 JSON 内容时，退回等价的字典结构。"""
        try:
            return resp.json()
        except ValueError:
            return {"code": resp.status_code, "msg": resp.text}