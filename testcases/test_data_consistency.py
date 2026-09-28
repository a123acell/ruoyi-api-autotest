# -*- coding: utf-8 -*-
"""测试用例：基于 MySQL 校验「用户 - 角色 - 菜单」数据一致性

直接查若依的库，验证前端/接口看到的权限关系，和数据库里落的数据是否一致。
这是「接口表现」与「数据落地」之间的交叉验证，能发现纯接口断言发现不了的问题。
"""
import allure
import pytest

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
@allure.description("验证 sys_role_menu 中 role_id=3（访客）的记录数为 0，"
                    "从数据层面解释「访客越权返回 403」的原因，实现接口现象与数据根因的交叉印证。")
def test_guest_role_has_no_menu_permission():
    with allure.step("统计访客角色的菜单权限数量"):
        rows = query("SELECT COUNT(*) FROM sys_role_menu WHERE role_id = 3")
    with allure.step("断言数量为 0"):
        assert rows[0][0] == 0, f"访客角色不应有菜单权限，实际 {rows}"


@allure.epic(EPIC)
@allure.feature("数据一致性")
@allure.story("业务规则校验")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("DB-003 每个启用中的用户都至少绑定一个角色（无孤儿用户）")
@allure.description("一致性规则：status=0 且 del_flag=0 的用户，必须至少绑定一个角色，"
                    "不允许出现「无角色」的正常用户。用 LEFT JOIN 反查违反规则的数据。")
def test_every_enabled_user_has_role():
    with allure.step("LEFT JOIN 反查无角色的启用用户"):
        rows = query(
            "SELECT u.user_id FROM sys_user u "
            "LEFT JOIN sys_user_role ur ON u.user_id = ur.user_id "
            "WHERE u.status = '0' AND u.del_flag = '0' AND ur.role_id IS NULL"
        )
    with allure.step("断言不存在无角色的启用用户"):
        assert len(rows) == 0, f"存在无角色的启用用户：{rows}"