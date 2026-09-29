# -*- coding: utf-8 -*-
"""测试用例：异常输入容错与查询注入防护（用户列表接口）

覆盖三类「非正常输入」，补齐「只测了合法参数、缺少异常/边界输入」的缺口：

  1. 分页参数越界与非法值：pageNum 小于 1 / 超过总页数，pageSize 取 0、负数、超大值、非数字；
  2. 查询关键字异常：200 字符超长关键字、LIKE 通配符；
  3. 查询注入尝试：排序字段拼接注入、查询条件注入。

所有预期值均来自 probe/probe_abnormal.py 的真实实测，不做臆测；断言优先看业务码与数据条数，
不依赖后端提示文案，避免开发改一句提示语就误挂。
"""
import allure
import pytest

from utils.db_check import query

EPIC = "RuoYi 后台管理系统 · 接口自动化测试"

# 分页断言用到的每页条数（与用例数据对应，便于反推合法页）
PAGE_SIZE = 2


def _user_total():
    """当前未删除用户总数。作为分页断言的数据基准，避免把用户数写死在用例里。"""
    return query("SELECT COUNT(*) FROM sys_user WHERE del_flag = '0'")[0][0]


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("分页异常输入")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("USER-005 分页合理化：越界 pageNum={pageNum} 被自动纠正而非报错")
@allure.description("PageHelper 开启 reasonable 后：pageNum<1 自动取第 1 页，超过总页数自动取最后一页。"
                    "用例不仅断言不报错，还比对该越界页与对应合法页返回的记录完全一致，"
                    "证明是被「纠正」而非「返回任意数据」。属框架特性，不作为缺陷。")
@pytest.mark.parametrize("pageNum", [0, -1, 9999])
def test_pagination_page_num_out_of_range(api, pageNum):
    total = _user_total()
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    expected_page = 1 if pageNum < 1 else pages
    with allure.step(f"GET /system/user/list?pageNum={pageNum}&pageSize={PAGE_SIZE}"):
        resp = api.get("/system/user/list", params={"pageNum": pageNum, "pageSize": PAGE_SIZE})
    with allure.step("断言 code=200 且 total 与数据库一致"):
        assert resp.get("code") == 200, f"越界页码不应报错：{resp}"
        assert resp.get("total") == total, f"total 应与库中用户数一致：{resp}"
    with allure.step("断言返回非空且不超过每页条数（说明已落到合法页）"):
        rows = resp.get("rows") or []
        assert 0 < len(rows) <= PAGE_SIZE, f"越界页码应被纠正到合法页，实际 rows={len(rows)}"
    with allure.step(f"断言与该越界页对应的合法页 pageNum={expected_page} 记录完全一致"):
        legal = api.get("/system/user/list", params={"pageNum": expected_page, "pageSize": PAGE_SIZE})
        assert [r["userId"] for r in rows] == [r["userId"] for r in legal["rows"]], \
            f"pageNum={pageNum} 应等价于 pageNum={expected_page}"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("分页异常输入")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("USER-025 分页参数非法值容错 pageSize={pageSize}")
@allure.description("pageSize 取 0 / 负数时不报错但返回空列表；取超大值、非数字（含小数、空串）时"
                    "被后端忽略并回落到默认每页 10 条。验证分页参数的类型与范围容错能力。")
@pytest.mark.parametrize("pageSize,expect_empty", [
    (0, True),
    (-1, True),
    (999999, False),
    ("abc", False),
    ("1.5", False),
])
def test_pagination_page_size_invalid(api, pageSize, expect_empty):
    total = _user_total()
    with allure.step(f"GET /system/user/list?pageNum=1&pageSize={pageSize}"):
        resp = api.get("/system/user/list", params={"pageNum": 1, "pageSize": pageSize})
    with allure.step("断言 code=200 且 total 不受 pageSize 影响"):
        assert resp.get("code") == 200, f"非法 pageSize 不应导致接口异常：{resp}"
        assert resp.get("total") == total, f"total 应与库中用户数一致：{resp}"
    rows = resp.get("rows") or []
    if expect_empty:
        with allure.step("断言非正数 pageSize 返回空列表（而非报错或返回全量）"):
            assert rows == [], f"pageSize={pageSize!r} 应返回空列表，实际 {len(rows)} 条"
    else:
        with allure.step("断言非法 pageSize 被忽略，回落到默认每页 10 条"):
            assert len(rows) == min(10, total), \
                f"pageSize={pageSize!r} 应回落到默认 10 条，实际 {len(rows)} 条"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("查询条件异常输入")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("USER-026 查询关键字异常容错：{name}")
@allure.description("200 字符超长关键字应正常返回空结果而不报错；LIKE 通配符 % 与 _ 按模糊匹配语义"
                    "命中全部记录，属框架既定行为（RuoYi 用 concat('%',?, '%') 做模糊匹配），"
                    "并非注入漏洞，用例固化该行为以防误判。")
@pytest.mark.parametrize("name,keyword,expect_all", [
    ("200 字符超长关键字", "a" * 200, False),
    ("LIKE 通配符 %", "%", True),
    ("LIKE 通配符 _", "_", True),
])
def test_query_keyword_abnormal(api, name, keyword, expect_all):
    total = _user_total()
    with allure.step(f"GET /system/user/list?userName={keyword!r}"):
        resp = api.get("/system/user/list", params={"userName": keyword})
    with allure.step("断言 code=200 且 rows 为数组（异常关键字不引发 500）"):
        assert resp.get("code") == 200, f"关键字 {name} 不应导致接口异常：{resp}"
        assert isinstance(resp.get("rows"), list)
    with allure.step("断言命中条数符合模糊匹配语义"):
        expected = total if expect_all else 0
        assert resp.get("total") == expected, \
            f"{name} 命中条数应为 {expected}，实际 {resp.get('total')}"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("查询注入防护")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("USER-021 排序字段 SQL 注入防护：orderByColumn={order_by}")
@allure.description("RuoYi 通过 SqlUtil 对 orderByColumn 做白名单校验，非法排序字段被拦截并返回失败，"
                    "且不返回任何数据，注入串不会被拼接进 SQL。")
@pytest.mark.parametrize("order_by", ["1,(select 1)", "user_id;drop"])
def test_order_by_column_injection_blocked(api, order_by):
    with allure.step(f"GET /system/user/list?orderByColumn={order_by}"):
        resp = api.get("/system/user/list", params={"orderByColumn": order_by, "isAsc": "desc"})
    with allure.step("断言非法排序字段被拦截（返回失败码且不返回数据）"):
        assert resp.get("code") == 500, f"非法排序字段应被拦截：{resp}"
        assert not resp.get("rows"), f"拦截时不应返回任何数据：{resp}"
    with allure.step("对照：合法排序字段正常返回，证明拦截来自白名单而非接口不可用"):
        legal = api.get("/system/user/list", params={"orderByColumn": "user_id", "isAsc": "desc"})
        assert legal.get("code") == 200, f"合法排序字段应正常返回：{legal}"


@allure.epic(EPIC)
@allure.feature("用户管理")
@allure.story("查询注入防护")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("USER-022 查询条件 SQL 注入防护：userName={payload}")
@allure.description("查询条件经 MyBatis #{} 预编译参数化处理，注入串被当作普通字符串，"
                    "命中 0 条记录而非返回全量数据，说明注入无效。")
@pytest.mark.parametrize("payload", ["' OR '1'='1", "1;DROP TABLE sys_user"])
def test_query_condition_injection_blocked(api, payload):
    with allure.step(f"GET /system/user/list?userName={payload}"):
        resp = api.get("/system/user/list", params={"userName": payload})
    with allure.step("断言注入串按普通字符串处理，命中 0 条（未返回全量）"):
        assert resp.get("code") == 200, f"注入串应作为普通字符串处理：{resp}"
        assert resp.get("total") == 0, f"注入串不应命中记录，实际 total={resp.get('total')}"
        assert len(resp.get("rows") or []) == 0