# -*- coding: utf-8 -*-
"""测试用例：越权与鉴权专项
核心结论：
  - 不带 Token 访问受限接口 → 401（未认证）
  - 低权限「访客」账号访问受限接口 → 403（无权限）

注意两个矩阵的接口集合不同：
  RESTRICTED 是「权限受限」接口，未认证 401、低权限 403，两个矩阵都用；
  AUTH_ONLY 是「仅需认证」的接口（如 /getInfo），低权限账号也能正常访问（实测 200），
  所以只进 401 矩阵，不能混进 403 矩阵，否则会把「无权限」的语义测错。
"""
import allure
import pytest

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

AUTH_ONLY = [
    ("当前用户信息", "/getInfo"),
]

NO_TOKEN_CASES = RESTRICTED + AUTH_ONLY


@allure.epic(EPIC)
@allure.feature("安全越权")
@allure.story("未认证访问（401）")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("SEC-001 未携带 Token 访问受限接口 {name} 返回 401")
@allure.description("对 8 个接口逐一验证：未认证请求必须被拦截并返回 401，不允许出现匿名可读。"
                    "该矩阵同时覆盖各业务模块的认证边界，因此模块用例不再重复实现同类断言。")
@pytest.mark.parametrize("name,path", NO_TOKEN_CASES)
def test_no_token_returns_401(api, name, path):
    with allure.step(f"不携带 Token 调用 GET {path}"):
        resp = api.get(path, auth=False)
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
def test_low_privilege_returns_403(guest_api, name, path):
    with allure.step(f"以 guest 账号调用 GET {path}"):
        resp = guest_api.get(path)
    with allure.step("断言返回 403 无权限"):
        assert resp.get("code") == 403, f"[{name}] 越权应返回 403，实际 {resp}"