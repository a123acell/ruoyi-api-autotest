# -*- coding: utf-8 -*-
"""测试用例：越权与鉴权专项
核心结论：
  - 不带 Token 访问受限接口 → 401（未认证）
  - 低权限「访客」账号访问受限接口 → 403（无权限）
"""
import allure
import pytest
import requests

from config import BASE_URL
from common.captcha import login

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"

RESTRICTED = [
    ("用户列表", "/system/user/list"),
    ("角色列表", "/system/role/list"),
    ("菜单列表", "/system/menu/list"),
    ("部门列表", "/system/dept/list"),
    ("岗位列表", "/system/post/list"),
    ("字典类型", "/system/dict/type/list"),
    ("参数设置", "/system/config/list"),
]


@pytest.fixture(scope="module")
def guest_token():
    """访客账号（零权限）登录，用于 403 越权测试"""
    return login("guest", "admin123")


@allure.epic(EPIC)
@allure.feature("安全越权")
@allure.story("未认证访问（401）")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("SEC-001 未携带 Token 访问受限接口 {name} 返回 401")
@allure.description("对 7 个受限接口逐一验证：未认证请求必须被拦截并返回 401，不允许出现匿名可读。")
@pytest.mark.parametrize("name,path", RESTRICTED)
def test_no_token_returns_401(name, path):
    with allure.step(f"不携带 Token 调用 GET {path}"):
        resp = requests.get(f"{BASE_URL}{path}", timeout=10).json()
    with allure.step("断言返回 401 未认证"):
        assert resp.get("code") == 401, f"[{name}] 未认证应返回 401，实际 {resp}"


@allure.epic(EPIC)
@allure.feature("安全越权")
@allure.story("低权限越权（403）")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("SEC-002 低权限访客访问受限接口 {name} 返回 403")
@allure.description("以零权限 guest 账号登录后访问 7 个受限接口，验证 RBAC 权限边界生效，返回 403 而非放行。")
@pytest.mark.smoke
@pytest.mark.parametrize("name,path", RESTRICTED)
def test_low_privilege_returns_403(name, path, guest_token):
    with allure.step("以 guest 账号 Token 构造请求头"):
        headers = {"Authorization": f"Bearer {guest_token}"}
    with allure.step(f"调用 GET {path}"):
        resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=10).json()
    with allure.step("断言返回 403 无权限"):
        assert resp.get("code") == 403, f"[{name}] 越权应返回 403，实际 {resp}"