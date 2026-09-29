# -*- coding: utf-8 -*-
"""测试用例：缺陷复现与登记

说明：本文件如实断言系统当前的真实行为，作为缺陷的「回归证据」固化下来。
当开发修复缺陷后，这些用例会由「通过」转为「失败」，从而提醒测试人员更新缺陷状态，
形成「缺陷发现 → 修复 → 回归验证」的闭环。
"""
import allure

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"

# 判定「msg 泄露技术细节」的标记：命中任一即说明后端把内部异常原文吐给了调用方。
# 不用某个具体文案（如 "null"）做匹配，否则开发改一句提示语就会误挂。
LEAK_MARKERS = ("Cannot invoke", "java.lang", "Exception", "at com.ruoyi")


@allure.epic(EPIC)
@allure.feature("缺陷复现")
@allure.story("空指针异常")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("BUG-01 查询不存在的用户详情抛空指针异常并泄露技术细节")
@allure.description("GET /system/user/99999 返回 500，msg 中包含 NPE 堆栈信息"
                    "（Cannot invoke \"SysUser.getRoles()\" because \"sysUser\" is null）。"
                    "预期应为友好提示（如「用户不存在」或 404），而非 500 + 技术细节泄露。")
@allure.issue("BUG-01", "查询不存在的用户详情抛空指针异常")
def test_bug_user_detail_nullpointer(api):
    with allure.step("GET /system/user/99999（不存在的用户 ID）"):
        resp = api.get("/system/user/99999")
    with allure.step("断言复现 500"):
        assert resp.get("code") == 500, f"预期 500，实际 {resp}"
    with allure.step("断言 msg 泄露技术细节（命中 Java 异常特征词即可）"):
        msg = resp.get("msg", "")
        assert any(marker in msg for marker in LEAK_MARKERS), \
            f"预期 msg 泄露技术细节，实际未命中任何特征词：{msg!r}"


@allure.epic(EPIC)
@allure.feature("缺陷复现")
@allure.story("错误码语义不清")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("BUG-08 删除不存在的用户返回通用 500，无法区分业务场景")
@allure.description("DELETE /system/user/99999 返回通用 500「操作失败」，前端无法区分"
                    "「记录不存在」与「系统异常」，影响错误提示的准确性。")
@allure.issue("BUG-08", "删除不存在的用户返回通用 500")
def test_bug_delete_nonexist_user(api):
    with allure.step("DELETE /system/user/99999"):
        resp = api.delete("/system/user/99999")
    with allure.step("断言复现通用 500"):
        assert resp.get("code") == 500


@allure.epic(EPIC)
@allure.feature("缺陷复现")
@allure.story("错误码语义不清")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("BUG-09 修改不存在用户的状态返回通用 500")
@allure.description("PUT /system/user/changeStatus 传入不存在的 userId，同样返回通用 500「操作失败」。")
@allure.issue("BUG-09", "修改不存在用户的状态返回通用 500")
def test_bug_change_status_nonexist_user(api):
    with allure.step("PUT /system/user/changeStatus（userId=99999）"):
        resp = api.put("/system/user/changeStatus", json={"userId": 99999, "status": "1"})
    with allure.step("断言复现通用 500"):
        assert resp.get("code") == 500