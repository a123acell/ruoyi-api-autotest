# -*- coding: utf-8 -*-
"""测试用例：缺陷复现与登记

说明：本文件如实断言系统当前的真实行为，作为缺陷的「回归证据」固化下来。
当开发修复缺陷后，这些用例会由「通过」转为「失败」，从而提醒测试人员更新缺陷状态，
形成「缺陷发现 → 修复 → 回归验证」的闭环。
"""
import allure
import requests

from config import BASE_URL

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("缺陷复现")
@allure.story("空指针异常")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("BUG-01 查询不存在的用户详情抛空指针异常并泄露技术细节")
@allure.description("GET /system/user/99999 返回 500，msg 中包含 NPE 堆栈信息"
                    "（Cannot invoke \"SysUser.getRoles()\" because \"sysUser\" is null）。"
                    "预期应为友好提示（如「用户不存在」或 404），而非 500 + 技术细节泄露。")
@allure.issue("BUG-01", "查询不存在的用户详情抛空指针异常")
def test_bug_user_detail_nullpointer(auth_headers):
    with allure.step("GET /system/user/99999（不存在的用户 ID）"):
        resp = requests.get(f"{BASE_URL}/system/user/99999", headers=auth_headers, timeout=10).json()
    with allure.step("断言复现 500 且 msg 含 NPE 技术细节"):
        assert resp.get("code") == 500
        assert "null" in resp.get("msg", "")


@allure.epic(EPIC)
@allure.feature("缺陷复现")
@allure.story("错误码语义不清")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("BUG-08 删除不存在的用户返回通用 500，无法区分业务场景")
@allure.description("DELETE /system/user/99999 返回通用 500「操作失败」，前端无法区分"
                    "「记录不存在」与「系统异常」，影响错误提示的准确性。")
@allure.issue("BUG-08", "删除不存在的用户返回通用 500")
def test_bug_delete_nonexist_user(auth_headers):
    with allure.step("DELETE /system/user/99999"):
        resp = requests.delete(f"{BASE_URL}/system/user/99999", headers=auth_headers, timeout=10).json()
    with allure.step("断言复现通用 500"):
        assert resp.get("code") == 500


@allure.epic(EPIC)
@allure.feature("缺陷复现")
@allure.story("错误码语义不清")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("BUG-09 修改不存在用户的状态返回通用 500")
@allure.description("PUT /system/user/changeStatus 传入不存在的 userId，同样返回通用 500「操作失败」。")
@allure.issue("BUG-09", "修改不存在用户的状态返回通用 500")
def test_bug_change_status_nonexist_user(auth_headers):
    with allure.step("PUT /system/user/changeStatus（userId=99999）"):
        resp = requests.put(
            f"{BASE_URL}/system/user/changeStatus",
            headers=auth_headers,
            json={"userId": 99999, "status": "1"},
            timeout=10,
        ).json()
    with allure.step("断言复现通用 500"):
        assert resp.get("code") == 500