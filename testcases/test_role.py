# -*- coding: utf-8 -*-
"""测试用例：角色管理模块"""
import allure
import pytest
import requests

from config import BASE_URL

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("角色管理")
@allure.story("列表分页")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("ROLE-001 角色列表分页查询 pageNum={pageNum} pageSize={pageSize}")
@pytest.mark.smoke
@pytest.mark.parametrize("pageNum,pageSize", [(1, 10), (1, 1), (2, 3)])
def test_role_list_pagination(auth_headers, pageNum, pageSize):
    with allure.step(f"GET /system/role/list?pageNum={pageNum}&pageSize={pageSize}"):
        resp = requests.get(
            f"{BASE_URL}/system/role/list",
            headers=auth_headers,
            params={"pageNum": pageNum, "pageSize": pageSize},
            timeout=10,
        ).json()
    with allure.step("断言 code=200 且 rows 为数组"):
        assert resp.get("code") == 200, f"角色列表返回异常：{resp}"
        assert isinstance(resp.get("rows"), list)


@allure.epic(EPIC)
@allure.feature("角色管理")
@allure.story("详情查询")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("ROLE-002 查询超级管理员角色详情返回 roleKey=admin")
def test_role_detail(auth_headers):
    with allure.step("GET /system/role/1"):
        resp = requests.get(f"{BASE_URL}/system/role/1", headers=auth_headers, timeout=10).json()
    with allure.step("断言 roleKey=admin"):
        assert resp.get("code") == 200
        assert resp.get("data", {}).get("roleKey") == "admin"


@allure.epic(EPIC)
@allure.feature("角色管理")
@allure.story("认证边界")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("ROLE-007 未认证访问角色列表返回 401")
def test_role_list_no_token():
    with allure.step("不携带 Token 调用 GET /system/role/list"):
        resp = requests.get(f"{BASE_URL}/system/role/list", timeout=10).json()
    with allure.step("断言返回 401"):
        assert resp.get("code") == 401