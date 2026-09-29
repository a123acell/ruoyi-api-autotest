# -*- coding: utf-8 -*-
"""测试用例：用户管理模块（含数据驱动分页）"""
import allure
import pytest

from config import ADMIN_USERNAME
from utils.db_check import query

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("列表分页")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("USER-004 分页参数数据驱动校验 pageNum={pageNum} pageSize={pageSize}")
@allure.description("数据驱动：5 组分页参数组合下，用户列表接口均正常返回 rows 与 total。")
@pytest.mark.smoke
@pytest.mark.parametrize("pageNum,pageSize", [(1, 10), (1, 1), (2, 3), (1, 50), (1, 100)])
def test_user_list_pagination(api, pageNum, pageSize):
    with allure.step(f"GET /system/user/list?pageNum={pageNum}&pageSize={pageSize}"):
        resp = api.get("/system/user/list", params={"pageNum": pageNum, "pageSize": pageSize})
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
def test_user_detail(api):
    with allure.step(f"按 user_name={ADMIN_USERNAME} 反查 user_id，避免写死自增主键"):
        rows = query("SELECT user_id FROM sys_user WHERE user_name = %s", (ADMIN_USERNAME,))
        assert rows, f"未找到账号 {ADMIN_USERNAME}，请检查初始化数据"
        user_id = rows[0][0]
    with allure.step(f"GET /system/user/{user_id}"):
        resp = api.get(f"/system/user/{user_id}")
    with allure.step(f"断言返回 {ADMIN_USERNAME} 的用户信息"):
        assert resp.get("code") == 200
        assert resp.get("data", {}).get("userName") == ADMIN_USERNAME