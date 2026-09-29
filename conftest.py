# -*- coding: utf-8 -*-
"""pytest 的 fixture 与钩子

请求统一走 common/api_client.py 的 ApiClient：
  - api       带 admin Token，Token 失效时自动重登一次
  - guest_api 带零权限访客 Token，用于 403 越权用例

另外两件事：
  - pytest_configure           统一日志格式：控制台看 INFO，文件留 DEBUG 全量，便于事后追溯
  - pytest_runtest_makereport  用例失败时，把最近几次「请求-响应」挂到 Allure 附件，直接看现场
"""
import json
import logging
import sys

import allure
import pytest

from common.api_client import RECENT_EXCHANGES, ApiClient
from common.captcha import login
from config import (ADMIN_PASSWORD, ADMIN_USERNAME, GUEST_PASSWORD,
                    GUEST_USERNAME)

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
LOG_FILE = "pytest.log"


def pytest_configure(config):
    """日志：控制台 INFO 以上，文件 DEBUG 全量。第三方库降噪到 WARNING。"""
    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            # mode="w"：每次运行重写，避免日志文件无限追加
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        ],
        force=True,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """用例（含前置 fixture）失败时，把最近几次请求/响应作为附件写入 Allure 报告。"""
    report = yield
    if report.failed and report.when in ("setup", "call"):
        for index, exchange in enumerate(reversed(RECENT_EXCHANGES), 1):
            allure.attach(
                json.dumps(exchange, ensure_ascii=False, indent=2),
                name=f"最近请求 {index}：{exchange['method']} {exchange['url']}",
                attachment_type=allure.attachment_type.JSON,
            )
    return report


@pytest.fixture(scope="session")
def token():
    """整个测试会话登录一次，返回 admin 的 Token"""
    return login(ADMIN_USERNAME, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def api(token):
    """带 admin Token 的请求客户端"""
    return ApiClient().set_token(
        token, renew_token=lambda: login(ADMIN_USERNAME, ADMIN_PASSWORD)
    )


@pytest.fixture(scope="module")
def guest_api():
    """带零权限访客 Token 的请求客户端"""
    return ApiClient().set_token(
        login(GUEST_USERNAME, GUEST_PASSWORD),
        renew_token=lambda: login(GUEST_USERNAME, GUEST_PASSWORD),
    )