# 若依接口自动化测试框架

针对若依（RuoYi）后台权限管理系统搭建的接口自动化测试工程，用 Python + pytest + requests 实现。
覆盖系统管理模块 41 个接口，包含功能、边界、异常、安全、数据一致性五类用例，
配套「万能验证码」自动登录、会话级 Token 复用、数据驱动、越权专项与 MySQL 落库校验。

## 一、环境

- Python 3.10+
- 若依后端已启动，默认地址：http://localhost:8080
- Redis（存放图形验证码）：localhost:6380
- MySQL（数据一致性校验）：localhost:3306，库 `ry-vue`

> 地址、端口、账号都可通过环境变量覆盖（`RY_BASE_URL`、`RY_REDIS_PORT`、
> `RY_MYSQL_HOST`、`RY_MYSQL_PASSWORD`、`RY_ADMIN_PASSWORD` 等），
> 数据库密码等敏感项不写死在代码里，完整清单见 `config.py`。

## 二、安装依赖

```bash
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 三、运行测试

在项目根目录下执行（用 `python -m pytest`，不要直接敲 `pytest`）：

```bash
python -m pytest testcases -v

# 只跑冒烟集（版本提测准入门禁，已打 smoke 标记）
python -m pytest -m smoke -v
```

> `pytest.ini` 已注册 `smoke` 标记，冒烟集覆盖登录鉴权 → 基础数据查询 → 认证/鉴权防线共 13 个用例函数
> （26 个参数化实例），约 2 秒跑完。

## 四、生成报告

```bash
# 1) 生成自包含的 HTML 报告（双击即可打开）
python -m pytest testcases -v --html=report/report.html --self-contained-html

# 2) 生成 Allure 报告（先出结果数据，再渲染成静态站点）
python -m pytest testcases --alluredir=allure-results --clean-alluredir
allure generate allure-results -o allure-report --clean
allure open allure-report        # 本地预览
```

> 用例已用 `@allure.title("编号 用例名")` 标注，报告里直接以「SEC-001 / SEC-002 / DB-001」这类编号呈现，
> 便于按编号定位到具体的接口与断言。

## 五、目录结构

```
├── config.py                  # 全局配置（地址、账号、Redis、MySQL，敏感项走环境变量）
├── conftest.py                # pytest fixture：会话级登录一次，Token 共享给所有用例
├── pytest.ini                 # pytest 配置：注册 smoke 标记、指定用例目录
├── common/
│   └── captcha.py             # 万能验证码：从 Redis 取验证码明文，完成自动登录
├── testcases/                 # 测试用例
│   ├── test_login.py          # 登录鉴权
│   ├── test_user.py           # 用户管理（含数据驱动分页）
│   ├── test_role.py           # 角色管理
│   ├── test_menu.py           # 菜单/部门/岗位
│   ├── test_authz.py          # 越权专项（无 Token→401，低权限→403）
│   ├── test_bugs.py           # 缺陷复现与登记
│   └── test_data_consistency.py  # MySQL 数据一致性校验
├── utils/
│   └── db_check.py            # MySQL 连接与校验工具
├── scripts/
│   └── fix_guest_password.py  # 一次性：初始化「访客」账号密码
└── requirements.txt
```

## 六、几个核心概念

1. **万能验证码绕过**：若依登录页要输图形验证码，自动化无法识别图片。但验证码的正确答案存在 Redis 里（key 是 `captcha_codes:{uuid}`），所以脚本先去 Redis 把答案取出来，再调用 `/login` 完成登录，不需要人眼看图。
2. **fixture 传 Token**：`conftest.py` 里用 pytest 的 fixture，整个测试会话只登录一次拿到 Token，所有用例自动带上，不用每个用例都重新登录。
3. **数据驱动**：用 `@pytest.mark.parametrize` 把多组分页参数喂给同一个用例。
4. **越权 401 / 403**：不带 Token 访问受限接口返回 401；用一个「零权限访客」账号访问返回 403。
5. **MySQL 数据一致性**：直接查 `sys_user`、`sys_user_role`、`sys_role`、`sys_role_menu` 这几张表，验证权限关系是否正确落库。

## 七、访客账号（用于 403 越权测试）

- 用户名：`guest`，密码：`admin123`，角色：访客（零权限）

（账号由 `scripts/fix_guest_password.py` + SQL 初始化，详见该文件。）