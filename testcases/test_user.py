# -*- coding: utf-8 -*-
"""测试用例：用户管理模块（含数据驱动分页）"""
import allure
import pytest
import requests

from config import BASE_URL

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("列表分页")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("USER-004 分页参数数据驱动校验 pageNum={pageNum} pageSize={pageSize}")
@allure.description("数据驱动：5 组分页参数组合下，用户列表接口均正常返回 rows 与 total。")
@pytest.mark.smoke
@pytest.mark.parametrize("pageNum,pageSize", [(1, 10), (1, 1), (2, 3), (1, 50), (1, 100)])
def test_user_list_pagination(auth_headers, pageNum, pageSize):
    with allure.step(f"GET /system/user/list?pageNum={pageNum}&pageSize={pageSize}"):
        resp = requests.get(
            f"{BASE_URL}/system/user/list",
            headers=auth_headers,
            params={"pageNum": pageNum, "pageSize": pageSize},
            timeout=10,
        ).json()
    with allure.step("断言 code=200、rows 为数组、包含 total"):
        assert resp.get("code") == 200, f"用户列表返回异常：{resp}"
        assert isinstance(resp.get("rows"), list)
        assert "total" in resp


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("详情查询")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("USER-006 查询单个用户详情返回 userName=admin")
@pytest.mark.smoke
def test_user_detail(auth_headers):
    with allure.step("GET /system/user/1"):
        resp = requests.get(f"{BASE_URL}/system/user/1", headers=auth_headers, timeout=10).json()
    with allure.step("断言返回 admin 用户信息"):
        assert resp.get("code") == 200
        assert resp.get("data", {}).get("userName") == "admin"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("认证边界")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("USER-023 未认证访问用户列表返回 401")
@pytest.mark.smoke
def test_user_list_no_token():
    with allure.step("不携带 Token 调用 GET /system/user/list"):
        resp = requests.get(f"{BASE_URL}/system/user/list", timeout=10).json()
    with allure.step("断言返回 401"):
        assert resp.get("code") == 401