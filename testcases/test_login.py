# -*- coding: utf-8 -*-
"""测试用例：登录鉴权模块"""
import base64
import json

import allure
import pytest
import redis

from common.api_client import ApiClient
from common.captcha import get_captcha_code, login
from config import (ADMIN_PASSWORD, ADMIN_USERNAME, REDIS_DB, REDIS_HOST,
                    REDIS_PORT)

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _jwt_payload(token: str) -> dict:
    seg = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))


def _tampered(real_token: str, kind: str) -> str:
    """基于真实 Token 构造四类非法 Token：改签名 / 改 payload / 结构畸形 / 空串"""
    head, payload, sig = real_token.split(".")
    if kind == "篡改签名":
        # 不能只改末位字符：base64url 末位字符的低位是填充位，解码时会被丢弃，
        # 改完可能解出同一串签名，Token 依然有效，用例就会偶发假阴性。
        # 这里对签名段整体逐字符替换，保证解出的字节必然不同。
        flipped = "".join("A" if ch != "A" else "B" for ch in sig)
        return f"{head}.{payload}.{flipped}"
    if kind == "篡改 payload":
        forged = _b64e(json.dumps({"login_user_key": "00000000-0000-0000-0000-000000000000"},
                                  separators=(",", ":")).encode())
        return f"{head}.{forged}.{sig}"
    if kind == "畸形 Token":
        return "abc"
    if kind == "空 Token":
        return ""
    raise ValueError(f"未知的非法 Token 类型：{kind}")


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("图形验证码")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("AUTH-001 获取图形验证码接口正常返回 uuid 与 base64 图片")
@allure.description("校验 GET /captchaImage 返回 code=200、uuid 非空，验证码明文写入 Redis；"
                    "该机制是后续「万能验证码」自动登录的基础。")
@pytest.mark.smoke
def test_captcha_image(api):
    with allure.step("GET /captchaImage"):
        resp = api.get("/captchaImage", auth=False)
    with allure.step("断言 code=200 且 uuid 非空"):
        assert resp.get("code") == 200
        assert resp.get("uuid"), "验证码接口没有返回 uuid"


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("账号密码登录")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("AUTH-002 正确账号+密码+验证码登录成功并返回 JWT Token")
@allure.description("从 Redis 读取验证码明文，绕过图形识别完成登录，验证返回 token 字段。")
@pytest.mark.smoke
def test_login_success():
    with allure.step("读取 Redis 验证码明文并 POST /login"):
        token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    with allure.step("断言成功返回 Token"):
        assert token, "登录失败，没有拿到 Token"


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("账号密码登录")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("AUTH-003 密码错误登录失败且不返回 Token")
def test_login_wrong_password(api):
    with allure.step("取验证码明文"):
        code, uuid = get_captcha_code()
    with allure.step("POST /login 提交错误密码"):
        resp = api.post(
            "/login",
            auth=False,
            json={"username": ADMIN_USERNAME, "password": "WrongPass123", "code": code, "uuid": uuid},
        )
    with allure.step("断言登录失败"):
        assert resp.get("code") == 500, f"错误密码应登录失败，实际 {resp}"


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("登录态获取")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("AUTH-007 携带有效 Token 获取当前登录用户信息与权限集合")
@pytest.mark.smoke
def test_get_info(api):
    with allure.step("GET /getInfo（客户端自动带上 Bearer Token）"):
        resp = api.get("/getInfo")
    with allure.step("断言 userName=admin 且返回权限集合"):
        assert resp.get("code") == 200
        assert resp.get("user", {}).get("userName") == ADMIN_USERNAME


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("登录态获取")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("AUTH-008 携带有效 Token 获取动态菜单路由")
@pytest.mark.smoke
def test_get_routers(api):
    with allure.step("GET /getRouters"):
        resp = api.get("/getRouters")
    with allure.step("断言返回路由数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("data"), list)


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("Token 安全")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("AUTH-010 伪造或篡改 Token 访问被拒绝：{kind}")
@allure.description("基于真实 Token 构造四类非法 Token：篡改签名、篡改 payload（保留原签名）、"
                    "结构畸形、空串。逐一访问 /getInfo，断言统一返回 401，"
                    "证明签名校验与会话校验有效，无法通过改写 Token 冒充身份。")
@pytest.mark.parametrize("kind", ["篡改签名", "篡改 payload", "畸形 Token", "空 Token"])
def test_token_tampered_rejected(api, token, kind):
    with allure.step(f"构造非法 Token：{kind}"):
        bad_token = _tampered(token, kind)
    with allure.step("GET /getInfo 携带该非法 Token（匿名请求，不触发自动重登）"):
        resp = api.get("/getInfo", auth=False,
                       headers={"Authorization": f"Bearer {bad_token}"})
    with allure.step("断言返回 401 认证失败"):
        assert resp.get("code") == 401, f"{kind} 应被拒绝，实际 {resp}"


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("Token 安全")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("AUTH-011 服务端会话失效后 Token 立即失效返回 401")
@allure.description("若依的登录态由 Redis 键 login_tokens:{uuid} 承载，Token 只是会话凭证。"
                    "用例独立登录一次（避免影响会话级共享 Token），确认可正常访问后删除该 Redis 会话键，"
                    "再断言原 Token 立即失效返回 401，验证「服务端可主动注销会话」这一安全能力。")
def test_token_invalid_after_session_removed():
    with allure.step("独立登录一次，拿到仅属于本用例的 Token"):
        fresh_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
        session_uuid = _jwt_payload(fresh_token)["login_user_key"]
        client = ApiClient().set_token(fresh_token)
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    try:
        with allure.step("失效前：确认该 Token 可正常访问 /getInfo"):
            assert client.get("/getInfo").get("code") == 200
        with allure.step(f"删除 Redis 会话键 login_tokens:{session_uuid}"):
            assert r.delete(f"login_tokens:{session_uuid}") == 1, "会话键不存在，前置条件不成立"
        with allure.step("断言原 Token 立即失效返回 401"):
            resp = client.get("/getInfo")
            assert resp.get("code") == 401, f"会话已失效，Token 不应继续可用：{resp}"
    finally:
        r.close()