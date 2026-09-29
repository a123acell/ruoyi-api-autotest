# -*- coding: utf-8 -*-
"""测试用例：写接口正向链路（新增 / 修改 / 删除）

补齐「只覆盖了 GET 查询、缺少 POST/PUT/DELETE 正向用例」的缺口。每条用例都是一条完整链路：

    正向操作 → 断言成功 → 落库校验（直连 MySQL 交叉验证）→ 反向校验（重复新增 / 越权删除等）→ 数据清理

清理逻辑放在 finally 中，且清理走数据库硬删除，保证用例断言失败也不会残留测试数据，可重复执行。
用例编号沿用测试用例文档中的既有编号（USER-009 / USER-015 / ROLE-004 / POST-004 / DEPT-005），
与设计用例一一对应，保持双向追溯。
"""
import allure
import pytest

from config import (PROBE_DEPT_NAME, PROBE_DEPT_PARENT_NAME, PROBE_NICKNAME,
                    PROBE_PASSWORD, PROBE_POST_CODE, PROBE_POST_NAME,
                    PROBE_ROLE_KEY, PROBE_ROLE_NAME, PROBE_USERNAME,
                    PROBE_WEAK_PASSWORD)
from utils.db_check import query, update

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"

# 若依默认顶级部门（若依科技）的 dept_id
DEFAULT_ROOT_DEPT_ID = 100


def _purge_user(user_name):
    """硬删除遗留的探针用户及其角色关联，保证用例可重复执行"""
    for (user_id,) in query("SELECT user_id FROM sys_user WHERE user_name = %s", (user_name,)):
        update("DELETE FROM sys_user_role WHERE user_id = %s", (user_id,))
        update("DELETE FROM sys_user WHERE user_id = %s", (user_id,))


def _purge_role(role_key):
    """硬删除遗留的探针角色及其菜单/用户关联"""
    for (role_id,) in query("SELECT role_id FROM sys_role WHERE role_key = %s", (role_key,)):
        update("DELETE FROM sys_role_menu WHERE role_id = %s", (role_id,))
        update("DELETE FROM sys_user_role WHERE role_id = %s", (role_id,))
        update("DELETE FROM sys_role WHERE role_id = %s", (role_id,))


def _purge_post(post_code):
    """硬删除遗留的探针岗位（sys_post 为物理删除表）"""
    update("DELETE FROM sys_post WHERE post_code = %s", (post_code,))


def _purge_dept(dept_name):
    """硬删除遗留的探针部门及其角色关联"""
    for (dept_id,) in query("SELECT dept_id FROM sys_dept WHERE dept_name = %s", (dept_name,)):
        update("DELETE FROM sys_role_dept WHERE dept_id = %s", (dept_id,))
        update("DELETE FROM sys_dept WHERE dept_id = %s", (dept_id,))


def _create_user(api):
    """前置：新增探针用户，返回 userId"""
    payload = {
        "userName": PROBE_USERNAME,
        "nickName": PROBE_NICKNAME,
        "password": PROBE_PASSWORD,
        "status": "0",
    }
    resp = api.post("/system/user", json=payload)
    assert resp.get("code") == 200, f"前置新增探针用户失败：{resp}"
    rows = query("SELECT user_id FROM sys_user WHERE user_name = %s", (PROBE_USERNAME,))
    assert rows, f"前置新增用户未落库：{PROBE_USERNAME}"
    return rows[0][0]


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("新增用户")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("USER-009 新增用户：账号唯一性校验")
@allure.description("正向链路：POST 新增探针用户成功 → 校验落库（sys_user 存在且 del_flag=0）→ "
                    "同账号重复新增被唯一性校验拦截 → 清理探针数据。")
def test_user_create_unique(api):
    _purge_user(PROBE_USERNAME)
    payload = {
        "userName": PROBE_USERNAME,
        "nickName": PROBE_NICKNAME,
        "password": PROBE_PASSWORD,
        "status": "0",
    }
    try:
        with allure.step(f"POST /system/user 新增探针用户 {PROBE_USERNAME}"):
            created = api.post("/system/user", json=payload)
        with allure.step("断言正向新增成功"):
            assert created.get("code") == 200, f"正向新增用户失败：{created}"
        with allure.step("落库校验：sys_user 存在该账号且 del_flag=0"):
            rows = query("SELECT del_flag FROM sys_user WHERE user_name = %s", (PROBE_USERNAME,))
            assert rows, f"接口返回成功但数据库未落库：{PROBE_USERNAME}"
            assert rows[0][0] == "0", f"新增用户 del_flag 应为 0，实际 {rows[0][0]}"
        with allure.step("POST /system/user 重复提交同一账号"):
            duplicated = api.post("/system/user", json=payload)
        with allure.step("断言唯一性校验拦截（返回失败）"):
            assert duplicated.get("code") != 200, f"重复账号不应新增成功：{duplicated}"
    finally:
        _purge_user(PROBE_USERNAME)
    with allure.step("确认探针用户已清理"):
        left = query("SELECT COUNT(*) FROM sys_user WHERE user_name = %s", (PROBE_USERNAME,))
        assert left[0][0] == 0, f"探针数据未清理干净：{left}"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("重置密码")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("USER-015 重置密码接口：弱密码校验缺失")
@allure.description("正向链路：前置新增探针用户 → PUT resetPwd 重置为合规密码成功，校验 sys_user.password "
                    "哈希已更新；再重置为 4 位弱密码，复现「弱密码校验缺失、可直接入库」的缺陷 → 清理。")
def test_reset_password_weak_check(api):
    _purge_user(PROBE_USERNAME)
    try:
        with allure.step(f"前置：新增探针用户 {PROBE_USERNAME}"):
            user_id = _create_user(api)
            before_hash = query("SELECT password FROM sys_user WHERE user_id = %s", (user_id,))[0][0]
        with allure.step("PUT /system/user/resetPwd 重置为合规密码"):
            reset = api.put(
                "/system/user/resetPwd",
                json={"userId": user_id, "password": PROBE_PASSWORD},
            )
        with allure.step("断言正向重置成功"):
            assert reset.get("code") == 200, f"正向重置密码失败：{reset}"
        with allure.step("落库校验：sys_user.password 哈希已更新"):
            after_hash = query("SELECT password FROM sys_user WHERE user_id = %s", (user_id,))[0][0]
            assert after_hash != before_hash, "重置密码后数据库中的密码哈希未发生变化"
        with allure.step("PUT /system/user/resetPwd 重置为 4 位弱密码"):
            weak = api.put(
                "/system/user/resetPwd",
                json={"userId": user_id, "password": PROBE_WEAK_PASSWORD},
            )
        with allure.step("断言复现「弱密码校验缺失」（仍返回成功）"):
            assert weak.get("code") == 200, f"预期复现弱密码可入库，实际被拦截：{weak}"
    finally:
        _purge_user(PROBE_USERNAME)
    with allure.step("确认探针用户已清理"):
        left = query("SELECT COUNT(*) FROM sys_user WHERE user_name = %s", (PROBE_USERNAME,))
        assert left[0][0] == 0, f"探针数据未清理干净：{left}"


@allure.epic(EPIC)
@allure.feature("角色管理")
@allure.story("新增角色")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("ROLE-004 新增角色：权限字符唯一性校验")
@allure.description("正向链路：POST 新增探针角色成功 → 校验落库（sys_role 存在且 del_flag=0）→ "
                    "同权限字符重复新增被拦截 → 清理探针数据。")
def test_role_create_unique(api):
    _purge_role(PROBE_ROLE_KEY)
    # menuIds 必须是非 null 数组：若依 insertRoleMenu 会直接遍历该字段，传 null 会 NPE 返回 500
    payload = {
        "roleName": PROBE_ROLE_NAME,
        "roleKey": PROBE_ROLE_KEY,
        "roleSort": 1,
        "status": "0",
        "menuIds": [],
    }
    try:
        with allure.step(f"POST /system/role 新增探针角色 {PROBE_ROLE_KEY}"):
            created = api.post("/system/role", json=payload)
        with allure.step("断言正向新增成功"):
            assert created.get("code") == 200, f"正向新增角色失败：{created}"
        with allure.step("落库校验：sys_role 存在该权限字符且 del_flag=0"):
            rows = query("SELECT del_flag FROM sys_role WHERE role_key = %s", (PROBE_ROLE_KEY,))
            assert rows, f"接口返回成功但数据库未落库：{PROBE_ROLE_KEY}"
            assert rows[0][0] == "0", f"新增角色 del_flag 应为 0，实际 {rows[0][0]}"
        with allure.step("POST /system/role 重复提交同一权限字符"):
            duplicated = api.post("/system/role", json=payload)
        with allure.step("断言唯一性校验拦截（返回失败）"):
            assert duplicated.get("code") != 200, f"重复权限字符不应新增成功：{duplicated}"
    finally:
        _purge_role(PROBE_ROLE_KEY)
    with allure.step("确认探针角色已清理"):
        left = query("SELECT COUNT(*) FROM sys_role WHERE role_key = %s", (PROBE_ROLE_KEY,))
        assert left[0][0] == 0, f"探针数据未清理干净：{left}"


@allure.epic(EPIC)
@allure.feature("岗位管理")
@allure.story("新增岗位")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("POST-004 新增岗位：岗位编码唯一性校验")
@allure.description("正向链路：POST 新增探针岗位成功 → 校验落库（sys_post 存在该编码）→ "
                    "同编码重复新增被拦截 → 清理探针数据。")
def test_post_create_unique(api):
    _purge_post(PROBE_POST_CODE)
    payload = {
        "postCode": PROBE_POST_CODE,
        "postName": PROBE_POST_NAME,
        "postSort": 1,
        "status": "0",
    }
    try:
        with allure.step(f"POST /system/post 新增探针岗位 {PROBE_POST_CODE}"):
            created = api.post("/system/post", json=payload)
        with allure.step("断言正向新增成功"):
            assert created.get("code") == 200, f"正向新增岗位失败：{created}"
        with allure.step("落库校验：sys_post 存在该岗位编码"):
            rows = query("SELECT post_id FROM sys_post WHERE post_code = %s", (PROBE_POST_CODE,))
            assert rows, f"接口返回成功但数据库未落库：{PROBE_POST_CODE}"
        with allure.step("POST /system/post 重复提交同一岗位编码"):
            duplicated = api.post("/system/post", json=payload)
        with allure.step("断言唯一性校验拦截（返回失败）"):
            assert duplicated.get("code") != 200, f"重复岗位编码不应新增成功：{duplicated}"
    finally:
        _purge_post(PROBE_POST_CODE)
    with allure.step("确认探针岗位已清理"):
        left = query("SELECT COUNT(*) FROM sys_post WHERE post_code = %s", (PROBE_POST_CODE,))
        assert left[0][0] == 0, f"探针数据未清理干净：{left}"


@allure.epic(EPIC)
@allure.feature("部门管理")
@allure.story("删除部门")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("DEPT-005 删除有子部门的父部门被拦截")
@allure.description("正向链路：POST 新增叶子部门 → DELETE 删除成功并校验落库（del_flag=2）→ "
                    "再构造父子部门，删除父部门被层级保护拦截 → 清理探针数据。")
def test_dept_delete_guard(api):
    _purge_dept(PROBE_DEPT_NAME)
    _purge_dept(PROBE_DEPT_PARENT_NAME)
    try:
        with allure.step(f"POST /system/dept 新增叶子部门 {PROBE_DEPT_NAME}"):
            created = api.post(
                "/system/dept",
                json={"deptName": PROBE_DEPT_NAME, "parentId": DEFAULT_ROOT_DEPT_ID,
                      "orderNum": 1, "status": "0"},
            )
        with allure.step("断言正向新增成功"):
            assert created.get("code") == 200, f"正向新增部门失败：{created}"
        with allure.step("落库校验：sys_dept 存在该部门且 del_flag=0"):
            rows = query("SELECT dept_id, del_flag FROM sys_dept WHERE dept_name = %s", (PROBE_DEPT_NAME,))
            assert rows, f"接口返回成功但数据库未落库：{PROBE_DEPT_NAME}"
            leaf_id, del_flag = rows[0]
            assert del_flag == "0", f"新增部门 del_flag 应为 0，实际 {del_flag}"
        with allure.step(f"DELETE /system/dept/{leaf_id} 删除叶子部门"):
            deleted = api.delete(f"/system/dept/{leaf_id}")
        with allure.step("断言正向删除成功"):
            assert deleted.get("code") == 200, f"正向删除部门失败：{deleted}"
        with allure.step("落库校验：该部门已软删除（del_flag=2）"):
            rows = query("SELECT del_flag FROM sys_dept WHERE dept_id = %s", (leaf_id,))
            assert rows and rows[0][0] == "2", f"删除后 del_flag 应为 2，实际 {rows}"
        with allure.step(f"构造父子部门：新增父部门 {PROBE_DEPT_PARENT_NAME}"):
            parent = api.post(
                "/system/dept",
                json={"deptName": PROBE_DEPT_PARENT_NAME, "parentId": DEFAULT_ROOT_DEPT_ID,
                      "orderNum": 1, "status": "0"},
            )
            assert parent.get("code") == 200, f"新增父部门失败：{parent}"
            parent_id = query("SELECT dept_id FROM sys_dept WHERE dept_name = %s",
                              (PROBE_DEPT_PARENT_NAME,))[0][0]
            child = api.post(
                "/system/dept",
                json={"deptName": PROBE_DEPT_NAME, "parentId": parent_id,
                      "orderNum": 1, "status": "0"},
            )
            assert child.get("code") == 200, f"新增子部门失败：{child}"
        with allure.step(f"DELETE /system/dept/{parent_id} 删除有子部门的父部门"):
            blocked = api.delete(f"/system/dept/{parent_id}")
        with allure.step("断言被层级保护拦截（存在子部门不允许删除）"):
            assert blocked.get("code") != 200, f"有子部门的父部门不应删除成功：{blocked}"
    finally:
        _purge_dept(PROBE_DEPT_NAME)
        _purge_dept(PROBE_DEPT_PARENT_NAME)
    with allure.step("确认探针部门已清理"):
        left = query("SELECT COUNT(*) FROM sys_dept WHERE dept_name IN (%s, %s)",
                     (PROBE_DEPT_NAME, PROBE_DEPT_PARENT_NAME))
        assert left[0][0] == 0, f"探针数据未清理干净：{left}"