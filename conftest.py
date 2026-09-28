# -*- coding: utf-8 -*-
"""pytest 的 fixture：会话级只登录一次，把 Token 共享给所有用例。
不用每个用例都去登录，全部用例自动带上同一个 Token。
"""
import pytest

from common.captcha import login
from config import ADMIN_USERNAME, ADMIN_PASSWORD


@pytest.fixture(scope="session")
def token():
    """整个测试会话登录一次，返回 Token"""
    return login(ADMIN_USERNAME, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def auth_headers(token):
    """把 Token 拼成标准的请求头 Authorization: Bearer xxx"""
    return {"Authorization": f"Bearer {token}"}