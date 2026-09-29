# -*- coding: utf-8 -*-
"""测试用例包

加这个 __init__.py 是为了让 pytest 走「包内导入」：pytest 会向上找到第一个非包目录
（即项目根目录）加进 sys.path，于是 `from config import ...`、`from utils.db_check import ...`
在 `python -m pytest` 与直接 `pytest` 两种调用方式下都能解析。
不加的话用例目录会被单独塞进 sys.path，只有从根目录执行才不报导入错误。
"""