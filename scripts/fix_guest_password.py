# -*- coding: utf-8 -*-
"""一次性初始化：把「访客」账号密码修正为 admin123（用参数化，避免 shell 转义问题）。"""
from utils.db_check import update

ADMIN_PWD_HASH = (
    "$2a$10$7JB720yubVSZvUI0rEqK/"
    ".VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2"
)

update("UPDATE sys_user SET password=%s WHERE user_name='guest'", (ADMIN_PWD_HASH,))
print("guest 密码已修正为 admin123")