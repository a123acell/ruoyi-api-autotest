# -*- coding: utf-8 -*-
"""测试用例：登录鉴权模块"""
import allure
import pytest
import requests

from config import BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD
from common.captcha import login, get_captcha_code

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("图形验证码")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("AUTH-001 获取图形验证码接口正常返回 uuid 与 base64 图片")
@allure.description("校验 GET /captchaImage 返回 code=200、uuid 非空，验证码明文写入 Redis；"
                    "该机制是后续「万能验证码」自动登录的基础。")
@pytest.mark.smoke
def test_captcha_image():
    with allure.step("GET /captchaImage"):
        resp = requests.get(f"{BASE_URL}/captchaImage", timeout=10).json()
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
def test_login_wrong_password():
    with allure.step("取验证码明文"):
        code, uuid = get_captcha_code()
    with allure.step("POST /login 提交错误密码"):
        resp = requests.post(
            f"{BASE_URL}/login",
            json={"username": ADMIN_USERNAME, "password": "WrongPass123", "code": code, "uuid": uuid},
            timeout=10,
        ).json()
    with allure.step("断言登录失败"):
        assert resp.get("code") == 500, f"错误密码应登录失败，实际 {resp}"


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("登录态获取")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("AUTH-007 携带有效 Token 获取当前登录用户信息与权限集合")
@pytest.mark.smoke
def test_get_info(auth_headers):
    with allure.step("GET /getInfo（Header 带 Bearer Token）"):
        resp = requests.get(f"{BASE_URL}/getInfo", headers=auth_headers, timeout=10).json()
    with allure.step("断言 userName=admin 且返回权限集合"):
        assert resp.get("code") == 200
        assert resp.get("user", {}).get("userName") == ADMIN_USERNAME


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("登录态获取")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("AUTH-008 携带有效 Token 获取动态菜单路由")
@pytest.mark.smoke
def test_get_routers(auth_headers):
    with allure.step("GET /getRouters"):
        resp = requests.get(f"{BASE_URL}/getRouters", headers=auth_headers, timeout=10).json()
    with allure.step("断言返回路由数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("data"), list)


@allure.epic(EPIC)
@allure.feature("登录鉴权")
@allure.story("认证边界")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("AUTH-009 未认证访问受保护接口返回 401")
def test_no_token_get_info():
    with allure.step("不携带任何 Token 调用 GET /getInfo"):
        resp = requests.get(f"{BASE_URL}/getInfo", timeout=10).json()
    with allure.step("断言返回 401"):
        assert resp.get("code") == 401