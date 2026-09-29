# -*- coding: utf-8 -*-
"""一次性探针：实测异常输入与 Token 篡改的真实行为，用于确定用例的预期值。

这不是自动化用例，也不属于用例集：pytest.ini 的 testpaths 只收 testcases/，不会收集本文件。
它只做真实请求 + 打印，不写任何交付物，作用是为 testcases/test_abnormal.py 与
testcases/test_login.py 的预期值提供可复核的实测出处，避免「预期值靠臆测」。

前置：若依后端 / Redis / MySQL 均已启动（与跑用例的前置一致），本脚本需要连库与连 Redis。
用法：在仓库根目录执行  python probe/probe_abnormal.py
"""
import base64
import hashlib
import hmac
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 仓库根目录，供 import config / common / utils 使用
sys.path.insert(0, ROOT)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import redis

from common.api_client import ApiClient
from common.captcha import login
from config import (ADMIN_PASSWORD, ADMIN_ROLE_KEY, ADMIN_USERNAME, REDIS_DB,
                    REDIS_HOST, REDIS_PORT)
from utils.db_check import query

api = ApiClient()
token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
api.set_token(token)


def b64e(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def b64d(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def forge(uuid: str, secret: str, alg="HS512", digest=hashlib.sha512) -> str:
    header = b64e(json.dumps({"typ": "JWT", "alg": alg}, separators=(",", ":")).encode())
    payload = b64e(json.dumps({"login_user_key": uuid}, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), header + b"." + payload, digest).digest()
    return (header + b"." + payload + b"." + b64e(sig)).decode()


def payload_of(tok: str) -> dict:
    return json.loads(b64d(tok.split(".")[1]))


def show(label, resp, extra=""):
    if isinstance(resp, dict):
        print(f"  {label:<44} code={resp.get('code')} rows={len(resp.get('rows') or [])} "
              f"total={resp.get('total')} msg={str(resp.get('msg'))[:60]} {extra}")
    else:
        print(f"  {label:<44} {resp} {extra}")


print("=" * 78)
print("[A1-1] 分页异常输入（GET /system/user/list）")
print("=" * 78)
for pn, ps in [(1, 10), (0, 10), (-1, 10), (99999, 10), (1, 0), (1, -1), (1, 999999), (1, "abc")]:
    r = api.get("/system/user/list", params={"pageNum": pn, "pageSize": ps})
    show(f"pageNum={pn!r} pageSize={ps!r}", r)

print("=" * 78)
print("[A1-2] 查询条件注入 / 超长关键字")
print("=" * 78)
show("userName=\"' OR '1'='1\"", api.get("/system/user/list", params={"userName": "' OR '1'='1"}))
show("userName=\"1;DROP TABLE sys_user\"", api.get("/system/user/list", params={"userName": "1;DROP TABLE sys_user"}))
show("orderByColumn=\"1,(select 1)\"", api.get("/system/user/list", params={"orderByColumn": "1,(select 1)"}))
show("orderByColumn=\"user_id;drop\"", api.get("/system/user/list", params={"orderByColumn": "user_id;drop"}))
show("orderByColumn=\"user_id desc\"(合法基线)", api.get("/system/user/list", params={"orderByColumn": "user_id", "isAsc": "desc"}))
show("userName=200 字符", api.get("/system/user/list", params={"userName": "a" * 200}))
show("userName=\"%\"(通配符)", api.get("/system/user/list", params={"userName": "%"}))
print("  当前用户总数核对:", query("SELECT COUNT(*) FROM sys_user WHERE del_flag='0'")[0][0])

print("=" * 78)
print("[A2] Token 篡改 / 伪造 / 会话失效")
print("=" * 78)
uuid = payload_of(token).get("login_user_key")
print(f"  真实会话 uuid = {uuid}")
show("有效 Token（基线）", api.get("/getInfo"))

bad_sig = token[:-1] + ("a" if token[-1] != "a" else "b")
show("篡改签名（改 1 个字符）", api.get("/getInfo", headers={"Authorization": f"Bearer {bad_sig}"}, auth=False))

parts = token.split(".")
forged_payload = b64e(json.dumps({"login_user_key": "00000000-0000-0000-0000-000000000000"},
                                 separators=(",", ":")).encode()).decode()
show("篡改 payload（保留原签名）",
     api.get("/getInfo", headers={"Authorization": f"Bearer {parts[0]}.{forged_payload}.{parts[2]}"}, auth=False))

show("畸形 Token（Bearer abc）",
     api.get("/getInfo", headers={"Authorization": "Bearer abc"}, auth=False))
show("空 Token（Bearer 空）",
     api.get("/getInfo", headers={"Authorization": "Bearer "}, auth=False))

# 若依源码里的公开演示默认 JWT 密钥，用于验证「即使拿到默认密钥也伪造不出有效 Token」；非真实凭据
for name, secret in [("RuoYi 默认 secret", "abcdefghijklmnopqrstuvwxyz")]:  # demo-default
    same = forge(uuid, secret)
    show(f"{name} 伪造【真实 uuid】的 Token", api.get("/getInfo", headers={"Authorization": f"Bearer {same}"}, auth=False))
    rnd = forge("00000000-0000-0000-0000-000000000000", secret)
    show(f"{name} 伪造【不存在 uuid】的 Token", api.get("/getInfo", headers={"Authorization": f"Bearer {rnd}"}, auth=False))

print("  --- 会话失效（删除 Redis 会话键）---")
fresh = login(ADMIN_USERNAME, ADMIN_PASSWORD)
fresh_uuid = payload_of(fresh).get("login_user_key")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
key = f"login_tokens:{fresh_uuid}"
print(f"  Redis 会话键 {key} 存在 = {r.exists(key)}")
show("失效前访问 /getInfo", api.get("/getInfo", headers={"Authorization": f"Bearer {fresh}"}, auth=False))
r.delete(key)
show("删除会话键后访问 /getInfo", api.get("/getInfo", headers={"Authorization": f"Bearer {fresh}"}, auth=False))

print("=" * 78)
print("[A8] 角色-菜单落库交叉校验可行性")
print("=" * 78)
rows = query("SELECT r.role_id, r.role_key, COUNT(rm.menu_id) FROM sys_role r "
             "LEFT JOIN sys_role_menu rm ON r.role_id = rm.role_id GROUP BY r.role_id, r.role_key")
for row in rows:
    print(f"  role_id={row[0]} role_key={row[1]} 绑定菜单数={row[2]}")
admin_role = query("SELECT role_id FROM sys_role WHERE role_key=%s", (ADMIN_ROLE_KEY,))[0][0]
resp = api.get(f"/system/menu/roleMenuTreeselect/{admin_role}")
checked = resp.get("checkedKeys")
print(f"  roleMenuTreeselect/{admin_role} code={resp.get('code')} checkedKeys 类型={type(checked).__name__} "
      f"长度={len(checked) if isinstance(checked, list) else 'N/A'}")
print(f"  checkedKeys 前 10 个: {checked[:10] if isinstance(checked, list) else checked}")

print("  --- 用 role_id=2（common，库中绑定 85 个菜单）做交叉校验 ---")
common_role = query("SELECT role_id FROM sys_role WHERE role_key='common'")[0][0]
db_ids = sorted(r[0] for r in query("SELECT menu_id FROM sys_role_menu WHERE role_id=%s", (common_role,)))
r2 = api.get(f"/system/menu/roleMenuTreeselect/{common_role}")
api_ids = sorted(r2.get("checkedKeys") or [])
print(f"  role_id={common_role} DB 菜单数={len(db_ids)}  API checkedKeys 数={len(api_ids)}")
print(f"  两集合是否完全一致: {db_ids == api_ids}")
if db_ids != api_ids:
    print(f"  仅 DB 有: {sorted(set(db_ids) - set(api_ids))[:10]}")
    print(f"  仅 API 有: {sorted(set(api_ids) - set(db_ids))[:10]}")
    print("  仅 DB 有 的菜单类型分布:",
          query("SELECT menu_type, COUNT(*) FROM sys_menu WHERE menu_id IN (%s) GROUP BY menu_type"
                % ",".join(str(i) for i in sorted(set(db_ids) - set(api_ids)))))
    print("  role=2 已绑定菜单的类型分布:",
          query("SELECT m.menu_type, COUNT(*) FROM sys_role_menu rm JOIN sys_menu m ON rm.menu_id=m.menu_id "
                "WHERE rm.role_id=%s GROUP BY m.menu_type", (common_role,)))
    mc_ids = sorted(r[0] for r in query(
        "SELECT rm.menu_id FROM sys_role_menu rm JOIN sys_menu m ON rm.menu_id=m.menu_id "
        "WHERE rm.role_id=%s AND m.menu_type IN ('M','C')", (common_role,)))
    print(f"  仅取 M/C 类：DB={len(mc_ids)}  API={len(api_ids)}  完全一致={mc_ids == api_ids}")