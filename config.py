# -*- coding: utf-8 -*-
"""若依接口自动化 —— 全局配置

地址与账号集中在这一个文件；密码等敏感项优先从环境变量读取，
本地或 CI 可通过环境变量注入，避免把真实凭据写进代码库。
"""
import os

# 后端接口地址
BASE_URL = os.getenv("RY_BASE_URL", "http://localhost:8080")

# Redis：若依的图形验证码明文存在这里，用于「万能验证码」自动登录
REDIS_HOST = os.getenv("RY_REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("RY_REDIS_PORT", "6380"))
REDIS_DB = int(os.getenv("RY_REDIS_DB", "0"))

# MySQL：用于数据一致性校验
MYSQL_HOST = os.getenv("RY_MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("RY_MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("RY_MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("RY_MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("RY_MYSQL_DB", "ry-vue")

# 默认管理员账号（登录用它拿 Token）
ADMIN_USERNAME = os.getenv("RY_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("RY_ADMIN_PASSWORD", "admin123")