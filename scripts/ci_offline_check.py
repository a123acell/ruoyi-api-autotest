# -*- coding: utf-8 -*-
"""CI 离线校验：不连后端、不发请求，只检查仓库层面的硬性约束。

三项检查：
  1. `.env` 不得入库 —— 那是本地真实凭据文件，仓库里只允许 `.env.example` 模板，
     且 `.gitignore` 必须忽略 `.env`；
  2. 不得硬编码凭据 —— 大写常量名含 PASSWORD/SECRET/TOKEN 且直接赋字符串字面量的，
     必须改走环境变量（config.py 的 _env）；
  3. `.env.example` 必须覆盖 config.py 读取的全部 RY_ 变量 —— 防止新增配置项后
     忘记同步模板，导致别人照模板配完还是缺项。

只依赖标准库，不依赖若依后端 / Redis / MySQL，秒级跑完，退出码非 0 即 CI 失败。
本地也可以直接 `python scripts/ci_offline_check.py` 当提交前门禁。
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "allure-results",
             "allure-report", "report", ".venv", "venv"}

# 大写常量名带凭据语义、且直接赋字符串字面量（正确写法是 _env("RY_...", 默认值)）
CRED_RE = re.compile(r"^[A-Z][A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN)[A-Z0-9_]*\s*=\s*[\"']")
ENV_USED_RE = re.compile(r"_env\(\s*[\"'](RY_[A-Z0-9_]+)[\"']")
ENV_DECLARED_RE = re.compile(r"^\s*(RY_[A-Z0-9_]+)\s*=", re.M)

problems = []


def check_env_not_committed():
    if (ROOT / ".env").exists():
        problems.append("仓库里存在 .env（本地真实凭据文件），应删除，改用环境变量 / CI secret 注入")
    if not (ROOT / ".env.example").exists():
        problems.append("缺少 .env.example 模板，别人无法知道要配哪些变量")
        return
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists() or ".env" not in gitignore.read_text(encoding="utf-8"):
        problems.append(".gitignore 未忽略 .env，真实凭据有被提交的风险")


def check_no_hardcoded_credentials():
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if CRED_RE.match(line):
                problems.append(
                    f"{path.relative_to(ROOT)}:{lineno} 疑似硬编码凭据，请改走 _env()：{line.strip()}"
                )


def check_env_template_covers_config():
    used = set(ENV_USED_RE.findall((ROOT / "config.py").read_text(encoding="utf-8")))
    declared = set(ENV_DECLARED_RE.findall((ROOT / ".env.example").read_text(encoding="utf-8")))
    missing = sorted(used - declared)
    if missing:
        problems.append(f".env.example 缺少 config.py 已读取的变量：{', '.join(missing)}")
    return f"config.py 读取 {len(used)} 个变量，模板声明 {len(declared)} 个"


def main():
    check_env_not_committed()
    check_no_hardcoded_credentials()
    summary = check_env_template_covers_config()

    if problems:
        print("离线校验未通过：")
        for item in problems:
            print("  -", item)
        return 1
    print(f"离线校验通过：.env 未入库、无硬编码凭据、环境变量模板与 config.py 一致（{summary}）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())