# -*- coding: utf-8 -*-
"""MySQL 数据一致性校验工具
用法：query(sql) 查询、update(sql, params) 更新。
后面阶段会用这里的 query 校验「用户-角色-菜单」关联是否正确落库。
"""
import pymysql

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


def get_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
    )


def query(sql, params=None):
    """执行查询，返回所有行（每行是 tuple）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def update(sql, params=None):
    """执行增删改并提交"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
    finally:
        conn.close()