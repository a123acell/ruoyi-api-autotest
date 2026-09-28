# -*- coding: utf-8 -*-
"""测试用例：菜单、部门、岗位等基础数据模块"""
import allure
import pytest
import requests

from config import BASE_URL

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("菜单管理")
@allure.story("菜单查询")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("MENU-001 菜单列表正常返回")
def test_menu_list(auth_headers):
    with allure.step("GET /system/menu/list"):
        resp = requests.get(f"{BASE_URL}/system/menu/list", headers=auth_headers, timeout=10).json()
    with allure.step("断言 code=200 且 data 为数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("data"), list)


@allure.epic(EPIC)
@allure.feature("菜单管理")
@allure.story("菜单树")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("MENU-001 菜单树选择接口正常返回树形结构")
@pytest.mark.smoke
def test_menu_treeselect(auth_headers):
    with allure.step("GET /system/menu/treeselect"):
        resp = requests.get(f"{BASE_URL}/system/menu/treeselect", headers=auth_headers, timeout=10).json()
    with allure.step("断言 code=200 且 data 为数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("data"), list)


@allure.epic(EPIC)
@allure.feature("部门管理")
@allure.story("部门查询")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("DEPT-001 部门列表正常返回")
@pytest.mark.smoke
def test_dept_list(auth_headers):
    with allure.step("GET /system/dept/list"):
        resp = requests.get(f"{BASE_URL}/system/dept/list", headers=auth_headers, timeout=10).json()
    with allure.step("断言 code=200 且 data 为数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("data"), list)


@allure.epic(EPIC)
@allure.feature("岗位管理")
@allure.story("列表分页")
@allure.severity(allure.severity_level.MINOR)
@allure.title("POST-001 岗位列表分页查询 pageNum={pageNum} pageSize={pageSize}")
@pytest.mark.smoke
@pytest.mark.parametrize("pageNum,pageSize", [(1, 10), (1, 1)])
def test_post_list_pagination(auth_headers, pageNum, pageSize):
    with allure.step(f"GET /system/post/list?pageNum={pageNum}&pageSize={pageSize}"):
        resp = requests.get(
            f"{BASE_URL}/system/post/list",
            headers=auth_headers,
            params={"pageNum": pageNum, "pageSize": pageSize},
            timeout=10,
        ).json()
    with allure.step("断言 code=200 且 rows 为数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("rows"), list)