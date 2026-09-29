# 若依接口自动化测试框架

针对若依（RuoYi）后台权限管理系统搭建的接口自动化测试工程，用 Python + pytest + requests 实现。
覆盖系统管理模块及登录鉴权共 22 个接口，实现 33 条自动化用例（70 个参数化实例），
包含功能、边界、异常、安全、数据一致性五类用例；配套「万能验证码」自动登录、统一请求层、
数据驱动、越权专项、写接口正向链路（新增/修改/删除）、MySQL 落库校验与响应时间阈值断言。

> 口径说明：测试设计阶段梳理了 77 条设计用例、41 个系统管理接口（见作品集目录下的用例文档）；
> 本工程按优先级实现其中的 33 条（70 个参数化实例）。接口数按代码实际调用的路径去重统计，不虚报。
>
> 最近一次全量回归：70 个参数化实例全部通过，用例执行约 12 秒（报告见作品集目录）。

## 一、环境

- Python 3.10+
- 若依后端已启动，默认地址：http://localhost:8080
- Redis（存放图形验证码）：localhost:6380
- MySQL（数据一致性校验）：localhost:3306，库 `ry-vue`

> 地址、端口、账号都可通过环境变量覆盖（`RY_BASE_URL`、`RY_REDIS_PORT`、
> `RY_MYSQL_HOST`、`RY_MYSQL_PASSWORD`、`RY_ADMIN_PASSWORD` 等），
> 数据库密码等敏感项不写死在代码里，完整清单见 `config.py`。
>
> 想批量改配置，复制 `.env.example` 为 `.env` 填值即可（`.env` 已被 `.gitignore` 排除，
> 不会提交）。配置优先级：真实环境变量 > `.env` 文件 > 代码内置默认值，CI 注入的环境变量始终优先。

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

> `pytest.ini` 已注册 `smoke` 标记，冒烟集覆盖登录鉴权 → 基础数据查询 → 认证/鉴权防线共 12 个用例函数
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
├── conftest.py                # pytest fixture：会话级登录一次，向用例注入带 Token 的请求客户端
├── pytest.ini                 # pytest 配置：注册 smoke 标记、指定用例目录
├── common/
│   ├── api_client.py          # 统一请求层：base_url/超时/鉴权头/响应解析 + 401 自动重登
│   └── captcha.py             # 万能验证码：从 Redis 取验证码明文，完成自动登录
├── testcases/                 # 测试用例
│   ├── test_login.py          # 登录鉴权
│   ├── test_user.py           # 用户管理（含数据驱动分页）
│   ├── test_role.py           # 角色管理
│   ├── test_menu.py           # 菜单/部门/岗位
│   ├── test_crud_flow.py      # 写接口正向链路（新增/修改/删除，含落库校验与数据清理）
│   ├── test_abnormal.py       # 异常输入容错与查询注入防护
│   ├── test_performance.py    # 响应时间阈值断言
│   ├── test_authz.py          # 越权专项（无 Token→401，低权限→403）
│   ├── test_bugs.py           # 缺陷复现与登记
│   └── test_data_consistency.py  # MySQL 数据一致性校验
├── utils/
│   └── db_check.py            # MySQL 连接与校验工具
├── scripts/
│   ├── fix_guest_password.py  # 一次性：初始化「访客」账号密码
│   └── ci_offline_check.py    # CI 离线校验：凭据扫描 + 环境变量模板一致性
├── .github/workflows/ci.yml   # GitHub Actions：push/PR 离线校验 + 手动全量运行
├── .env.example               # 环境变量模板（复制为 .env 使用，.env 不入库）
└── requirements.txt
```

## 六、几个核心概念

1. **万能验证码绕过**：若依登录页要输图形验证码，自动化无法识别图片。但验证码的正确答案存在 Redis 里（key 是 `captcha_codes:{uuid}`），所以脚本先去 Redis 把答案取出来，再调用 `/login` 完成登录，不需要人眼看图。
2. **统一请求层**：所有用例只跟 `common/api_client.py` 的 `ApiClient` 打交道，不直接调 `requests`。base_url 拼接、默认超时、鉴权头注入、响应解析都收敛在一处；带 Token 的请求遇到 401 会自动重登一次并重试，Token 有效期短也不会导致用例连锁失败。匿名请求（`auth=False`）不触发重登，否则会把「未认证应返回 401」的用例刷成 200。
3. **fixture 注入客户端**：`conftest.py` 里用 pytest 的 fixture，整个测试会话只登录一次拿到 Token，绑到 `ApiClient` 上注入用例；用例函数签名声明 `api` / `guest_api` 即可，不用关心登录与请求头。
4. **数据驱动**：用 `@pytest.mark.parametrize` 把多组分页参数、多接口越权矩阵喂给同一个用例。
5. **越权 401 / 403**：不带 Token 访问受限接口返回 401；用一个「零权限访客」账号访问返回 403。
6. **MySQL 数据一致性**：直接查 `sys_user`、`sys_user_role`、`sys_role`、`sys_role_menu` 这几张表，验证权限关系是否正确落库。
7. **写接口正向链路**：新增/修改/删除不只断言返回码，而是走完整链路——正向操作 → 断言成功 → 落库校验 → 反向校验（重复新增 / 层级保护）→ 数据清理。清理放在 `finally` 且走数据库硬删除，断言失败也不残留测试数据，用例可重复执行。
8. **异常输入与注入防护**：分页参数越界/非法值、超长关键字、LIKE 通配符、排序字段与查询条件注入，预期值全部来自实测探针而非臆测；断言优先看业务码与数据条数，不依赖后端提示文案。
9. **响应时间阈值**：请求层把每次请求耗时记在 `ApiClient.last_elapsed_ms`，性能用例先预热一次再计时，阈值由 `RY_MAX_RESPONSE_MS` 配置（默认 1000ms），避免把某一台机器的标准写死。

## 七、CI（GitHub Actions）

`.github/workflows/ci.yml` 分两个 job：

- **离线校验**（push / PR 自动触发）：装依赖 → `pytest --collect-only` 校验全部用例可收集 → `scripts/ci_offline_check.py` 扫描「`.env` 是否入库 / 是否硬编码凭据 / `.env.example` 是否覆盖 config.py 全部变量」。不连后端、不发请求，秒级完成，永远能跑绿。
- **全量运行**（`workflow_dispatch` 手动触发）：本仓库只有测试代码，若依后端是独立的 Java 工程不在仓库内，云端跑不了真正的全量接口用例。该 job 把 `RY_BASE_URL`、MySQL、Redis、账号等全部走 GitHub Secrets 注入，需要一个 CI 能访问到的后端（本地后端经隧道暴露，或用自建 runner）。

```bash
# 本地先跑一遍离线校验（提交前门禁）
python scripts/ci_offline_check.py
```

## 八、访客账号（用于 403 越权测试）

- 用户名：`guest`，密码：`admin123`，角色：访客（零权限）

（账号由 `scripts/fix_guest_password.py` + SQL 初始化，详见该文件。）