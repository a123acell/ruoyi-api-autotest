# -*- coding: utf-8 -*-
"""测试用例：角色管理模块"""
import allure
import pytest

from config import ADMIN_ROLE_KEY
from utils.db_check import query

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("角色管理")
@allure.story("列表分页")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("ROLE-001 角色列表分页查询 pageNum={pageNum} pageSize={pageSize}")
@pytest.mark.smoke
@pytest.mark.parametrize("pageNum,pageSize", [(1, 10), (1, 1), (2, 3)])
def test_role_list_pagination(api, pageNum, pageSize):
    with allure.step(f"GET /system/role/list?pageNum={pageNum}&pageSize={pageSize}"):
        resp = api.get("/system/role/list", params={"pageNum": pageNum, "pageSize": pageSize})
    with allure.step("断言 code=200 且 rows 为数组"):
        assert resp.get("code") == 200, f"角色列表返回异常：{resp}"
        assert isinstance(resp.get("rows"), list)


@allure.epic(EPIC)
@allure.feature("角色管理")
@allure.story("详情查询")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("ROLE-002 查询超级管理员角色详情返回 roleKey=admin")
def test_role_detail(api):
    with allure.step(f"按 role_key={ADMIN_ROLE_KEY} 反查 role_id，避免写死自增主键"):
        rows = query("SELECT role_id FROM sys_role WHERE role_key = %s", (ADMIN_ROLE_KEY,))
        assert rows, f"未找到 role_key={ADMIN_ROLE_KEY} 的角色，请检查初始化数据"
        role_id = rows[0][0]
    with allure.step(f"GET /system/role/{role_id}"):
        resp = api.get(f"/system/role/{role_id}")
    with allure.step(f"断言 roleKey={ADMIN_ROLE_KEY}"):
        assert resp.get("code") == 200
        assert resp.get("data", {}).get("roleKey") == ADMIN_ROLE_KEY