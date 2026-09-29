# -*- coding: utf-8 -*-
"""测试用例：菜单、部门、岗位等基础数据模块"""
import allure
import pytest

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"

# 设计用例 MENU-001「菜单列表与菜单树查询」覆盖两个接口，合并为一条用例、两个参数化实例
MENU_ENDPOINTS = [
    ("菜单列表", "/system/menu/list"),
    ("菜单树选择", "/system/menu/treeselect"),
]


@allure.epic(EPIC)
@allure.feature("菜单管理")
@allure.story("菜单查询")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("MENU-001 菜单列表与菜单树查询：{name}")
@pytest.mark.smoke
@pytest.mark.parametrize("name,path", MENU_ENDPOINTS)
def test_menu_list_and_treeselect(api, name, path):
    with allure.step(f"GET {path}"):
        resp = api.get(path)
    with allure.step("断言 code=200 且 data 为数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("data"), list)


@allure.epic(EPIC)
@allure.feature("部门管理")
@allure.story("部门查询")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("DEPT-001 部门列表正常返回")
@pytest.mark.smoke
def test_dept_list(api):
    with allure.step("GET /system/dept/list"):
        resp = api.get("/system/dept/list")
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
def test_post_list_pagination(api, pageNum, pageSize):
    with allure.step(f"GET /system/post/list?pageNum={pageNum}&pageSize={pageSize}"):
        resp = api.get("/system/post/list", params={"pageNum": pageNum, "pageSize": pageSize})
    with allure.step("断言 code=200 且 rows 为数组"):
        assert resp.get("code") == 200
        assert isinstance(resp.get("rows"), list)