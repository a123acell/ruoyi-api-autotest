# -*- coding: utf-8 -*-
"""若依接口自动化 —— 全局配置

地址与账号集中在这一个文件，全部支持环境变量覆盖（RY_ 前缀），本地与 CI 都可注入。
仓库内保留的是若依本地演示环境的默认口令，不是生产凭据；接入真实环境时用环境变量覆盖即可。
带 demo-default 标记的行即此类公开演示口令，交付自检脚本据此跳过告警。

配置来源优先级：真实环境变量 > 项目根目录 .env 文件 > 本文件内置默认值。
.env 已被 .gitignore 排除，敏感项（数据库密码等）放这里，模板见 .env.example。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 只在「进程环境变量未设置」时用 .env 补齐，不覆盖已有环境变量，保证 CI 注入优先
load_dotenv(Path(__file__).resolve().with_name(".env"))


def _env(name, default):
    """读取环境变量，把「空串」当作「未设置」处理。

    CI 里未配置的 secret 会被注入成空串而不是不注入，此时 int("") 会抛 ValueError，
    整个用例集在导入阶段就崩掉。这里统一兜底成默认值，让「没配」等价于「走默认」。
    """
    value = os.getenv(name)
    return default if value is None or not value.strip() else value


# 后端接口地址
BASE_URL = _env("RY_BASE_URL", "http://localhost:8080")

# 请求层默认超时（秒），统一由 common/api_client.py 使用
DEFAULT_TIMEOUT = int(_env("RY_TIMEOUT", "10"))

# 单接口响应时间上限（毫秒），供 A6 响应时间阈值断言使用
MAX_RESPONSE_MS = int(_env("RY_MAX_RESPONSE_MS", "1000"))

# Redis：若依的图形验证码明文存在这里，用于「万能验证码」自动登录
REDIS_HOST = _env("RY_REDIS_HOST", "localhost")
REDIS_PORT = int(_env("RY_REDIS_PORT", "6380"))
REDIS_DB = int(_env("RY_REDIS_DB", "0"))

# MySQL：用于数据一致性校验
MYSQL_HOST = _env("RY_MYSQL_HOST", "localhost")
MYSQL_PORT = int(_env("RY_MYSQL_PORT", "3306"))
MYSQL_USER = _env("RY_MYSQL_USER", "root")
MYSQL_PASSWORD = _env("RY_MYSQL_PASSWORD", "")
MYSQL_DB = _env("RY_MYSQL_DB", "ry-vue")

# 默认管理员账号（登录用它拿 Token）
ADMIN_USERNAME = _env("RY_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _env("RY_ADMIN_PASSWORD", "admin123")  # demo-default

# 零权限「访客」账号，用于 403 越权测试
GUEST_USERNAME = _env("RY_GUEST_USERNAME", "guest")
GUEST_PASSWORD = _env("RY_GUEST_PASSWORD", "admin123")  # demo-default

# 访客角色的 role_key：越权用例按 key 反查 role_id，避免把自增主键写死在用例里
GUEST_ROLE_KEY = _env("RY_GUEST_ROLE_KEY", "guest")

# 超级管理员角色的 role_key：角色详情用例按 key 反查 role_id，同样不写死自增主键
ADMIN_ROLE_KEY = _env("RY_ADMIN_ROLE_KEY", "admin")

# 有实际菜单授权的普通角色 role_key：供 DB-003「角色-菜单落库交叉校验」使用
# （admin 是超管、guest 零权限，都不适合做授权比对，故单独取 common）
COMMON_ROLE_KEY = _env("RY_COMMON_ROLE_KEY", "common")

# 写接口正向链路用例的探针数据（仅测试数据，非真实凭据；名称固定便于清理与重复执行）
PROBE_USERNAME = _env("RY_PROBE_USERNAME", "probe_crud_user")
PROBE_NICKNAME = _env("RY_PROBE_NICKNAME", "正向链路探针")
PROBE_PASSWORD = _env("RY_PROBE_PASSWORD", "Probe@12345")
PROBE_WEAK_PASSWORD = _env("RY_PROBE_WEAK_PASSWORD", "1234")
PROBE_ROLE_KEY = _env("RY_PROBE_ROLE_KEY", "probe_crud_role")
PROBE_ROLE_NAME = _env("RY_PROBE_ROLE_NAME", "正向链路探针角色")
PROBE_POST_CODE = _env("RY_PROBE_POST_CODE", "probe_crud_post")
PROBE_POST_NAME = _env("RY_PROBE_POST_NAME", "正向链路探针岗位")
PROBE_DEPT_NAME = _env("RY_PROBE_DEPT_NAME", "正向链路探针部门")
PROBE_DEPT_PARENT_NAME = _env("RY_PROBE_DEPT_PARENT_NAME", "正向链路探针父部门")