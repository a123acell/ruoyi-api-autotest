# -*- coding: utf-8 -*-
"""测试用例：基于 MySQL 校验「用户 - 角色 - 菜单」数据一致性

直接查若依的库，验证前端/接口看到的权限关系，和数据库里落的数据是否一致。
这是「接口表现」与「数据落地」之间的交叉验证，能发现纯接口断言发现不了的问题。
"""
import allure
import pytest

from config import COMMON_ROLE_KEY, GUEST_ROLE_KEY
from utils.db_check import query

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("数据一致性")
@allure.story("用户-角色关联")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("DB-001 admin 用户正确关联「超级管理员(admin)」角色")
@allure.description("通过 sys_user JOIN sys_user_role JOIN sys_role 三表联查，"
                    "验证 admin 用户的角色关联关系与接口返回的权限集合一致。")
@pytest.mark.smoke
def test_admin_user_role_link():
    with allure.step("三表联查 admin 用户的角色 key"):
        rows = query(
            "SELECT u.user_name, r.role_key "
            "FROM sys_user u "
            "JOIN sys_user_role ur ON u.user_id = ur.user_id "
            "JOIN sys_role r ON ur.role_id = r.role_id "
            "WHERE u.user_name = 'admin'"
        )
    with allure.step("断言存在 (admin, admin) 关联"):
        assert ("admin", "admin") in rows, f"admin 用户角色关联异常：{rows}"


@allure.epic(EPIC)
@allure.feature("数据一致性")
@allure.story("角色-菜单关联")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("DB-002 访客角色未绑定任何菜单权限（403 的数据库层根因）")
@allure.description("先按 role_key=guest 反查访客角色 id，再验证 sys_role_menu 中该角色的记录数为 0，"
                    "从数据层面解释「访客越权返回 403」的原因，实现接口现象与数据根因的交叉印证。")
def test_guest_role_has_no_menu_permission():
    with allure.step(f"按 role_key={GUEST_ROLE_KEY} 反查访客角色 id"):
        rows = query("SELECT role_id FROM sys_role WHERE role_key = %s", (GUEST_ROLE_KEY,))
        assert rows, f"未找到 role_key={GUEST_ROLE_KEY} 的角色，请检查角色初始化"
        role_id = rows[0][0]
    with allure.step(f"统计访客角色（role_id={role_id}）的菜单权限数量"):
        rows = query("SELECT COUNT(*) FROM sys_role_menu WHERE role_id = %s", (role_id,))
    with allure.step("断言数量为 0"):
        assert rows[0][0] == 0, f"访客角色不应有菜单权限，实际 {rows}"


@allure.epic(EPIC)
@allure.feature("数据一致性")
@allure.story("角色-菜单关联")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("DB-003 角色-菜单授权接口与数据库落库交叉校验（无幻影权限）")
@allure.description("取一个有实际菜单授权的普通角色（role_key=common），把「接口返回的授权」与"
                    "「数据库 sys_role_menu 落库的授权」做双向比对：\n"
                    "① 接口 checkedKeys 必须是数据库已绑定菜单的子集，不允许出现「库里没绑、接口却返回」的幻影权限；\n"
                    "② 数据库已绑定但接口未回传的部分，恰好是被勾选菜单的父节点——RuoYi 的角色菜单树会过滤父节点"
                    "（父节点由前端树按子节点自动级联勾选），因此差额必须与「已绑定菜单的父节点集合」完全相等。\n"
                    "两条断言合起来即「接口授权与落库数据完全一致」，能发现纯接口断言看不到的授权错位。")
def test_role_menu_cross_check(api):
    with allure.step(f"按 role_key={COMMON_ROLE_KEY} 反查角色 id"):
        rows = query("SELECT role_id FROM sys_role WHERE role_key = %s", (COMMON_ROLE_KEY,))
        assert rows, f"未找到 role_key={COMMON_ROLE_KEY} 的角色，请检查角色初始化"
        role_id = rows[0][0]
    with allure.step(f"查数据库：该角色已绑定的菜单集合（sys_role_menu, role_id={role_id}）"):
        db_ids = {r[0] for r in query("SELECT menu_id FROM sys_role_menu WHERE role_id = %s", (role_id,))}
        assert db_ids, f"角色 {COMMON_ROLE_KEY} 未绑定任何菜单，无法做授权比对"
    with allure.step(f"调接口：GET /system/menu/roleMenuTreeselect/{role_id} 取 checkedKeys"):
        resp = api.get(f"/system/menu/roleMenuTreeselect/{role_id}")
        assert resp.get("code") == 200, f"查询角色菜单树失败：{resp}"
        api_ids = set(resp.get("checkedKeys") or [])
    with allure.step("断言① 接口返回的菜单不超出数据库已绑定范围（无幻影权限）"):
        assert api_ids <= db_ids, f"接口返回了数据库未绑定的菜单：{sorted(api_ids - db_ids)}"
    with allure.step("断言② 库中已绑定但接口未回传的，恰好是被勾选菜单的父节点"):
        placeholders = ",".join(["%s"] * len(db_ids))
        parents = {r[0] for r in query(
            f"SELECT DISTINCT parent_id FROM sys_menu WHERE menu_id IN ({placeholders})",
            tuple(db_ids),
        )} - {0}
        assert db_ids - api_ids == parents, (
            f"授权差额与父节点集合不一致；仅库有={sorted((db_ids - api_ids) - parents)}，"
            f"仅父节点={sorted(parents - (db_ids - api_ids))}"
        )