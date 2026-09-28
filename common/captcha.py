# -*- coding: utf-8 -*-
"""万能验证码：不靠人眼识别图形验证码，而是直接从 Redis 取出验证码明文。
整条链路的原理：
  登录页会先请求 /captchaImage 拿到一个 uuid（验证码的唯一编号），
  同时后端把验证码的正确答案写进 Redis，key 是 captcha_codes:{uuid}。
  所以我们只要拿到 uuid，再去 Redis 里查这个 key，就能得到答案，
  然后用它调 /login 完成登录，全程不需要人工看图。
"""
import json

import requests
import redis

from config import BASE_URL, REDIS_HOST, REDIS_PORT, REDIS_DB


def get_captcha_code():
    """获取验证码答案和 uuid，返回 (答案, uuid)"""
    resp = requests.get(f"{BASE_URL}/captchaImage", timeout=10).json()
    uuid = resp["uuid"]

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    raw = r.get(f"captcha_codes:{uuid}")
    r.close()

    # 若依用 JSON 序列化存验证码，Redis 里是 '"42"'（带引号），需还原成 '42'
    code = json.loads(raw) if raw else None

    return code, uuid


def login(username, password):
    """用万能验证码完成登录，成功返回 Token 字符串"""
    code, uuid = get_captcha_code()
    resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": username, "password": password, "code": code, "uuid": uuid},
        timeout=10,
    ).json()

    if resp.get("code") == 200:
        return resp["token"]

    raise RuntimeError(f"登录失败，返回内容：{resp}")