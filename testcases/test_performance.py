# -*- coding: utf-8 -*-
"""测试用例：接口响应时间阈值

请求层（common/api_client.py）已把每次请求耗时记到 ApiClient.last_elapsed_ms，
这里直接消费它做阈值断言：核心查询接口单次响应应低于 config.MAX_RESPONSE_MS
（默认 1000ms，可用环境变量 RY_MAX_RESPONSE_MS 覆盖）。

计时前先预热一次：首个请求含 TCP 建连、会话初始化等一次性开销，计入会放大噪声，
导致同一接口在快慢机器上结论不稳定。阈值也做成可配置，避免把某一台机器的标准写死。

本用例不打 smoke 标记：机器负载波动时阈值断言容易假失败，不适合放进提测门禁。
"""
import allure
import pytest

from config import MAX_RESPONSE_MS

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"


@allure.epic(EPIC)
@allure.feature("性能基线")
@allure.story("响应时间阈值")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("PERF-001 核心接口响应时间低于阈值：{path}")
@allure.description(f"预热一次后再计时，断言单次请求耗时小于 {MAX_RESPONSE_MS}ms。"
                    "阈值来自配置而非写死，可用 RY_MAX_RESPONSE_MS 按环境调整。")
@pytest.mark.parametrize("path", [
    "/getInfo",
    "/system/user/list",
    "/system/role/list",
    "/system/menu/list",
])
def test_response_time_within_threshold(api, path):
    with allure.step(f"预热 GET {path}，排除建连与首次加载开销"):
        warm = api.get(path)
        assert warm.get("code") == 200, f"预热请求失败，无法评估响应时间：{warm}"
    with allure.step(f"计时 GET {path}"):
        resp = api.get(path)
        elapsed = api.last_elapsed_ms
    with allure.step(f"断言 code=200 且耗时 {elapsed}ms < {MAX_RESPONSE_MS}ms"):
        assert resp.get("code") == 200, f"{path} 返回异常：{resp}"
        assert elapsed < MAX_RESPONSE_MS, (
            f"{path} 响应 {elapsed}ms，超过阈值 {MAX_RESPONSE_MS}ms；"
            f"若为环境差异请用 RY_MAX_RESPONSE_MS 调整"
        )