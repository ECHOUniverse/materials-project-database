#!/usr/bin/env python3
"""Materials Project 插件公共库：API key 解析、MPRester 工厂、格式化输出。

供 mp_search.py / mp_get.py / mp_process.py 复用，不作为 CLI 直接运行。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

KEY_HELP = """\
缺少 Materials Project API key。请按以下步骤获取并配置：

1. 到 https://next-gen.materialsproject.org/dashboard 免费注册并获取 API key

2. 配置（二选一）：
   a) 环境变量（推荐）：在 ~/.zshrc 中添加
      export MP_API_KEY="你的key"
      然后 source ~/.zshrc
   b) key 文件：将 key 写入 ~/.mp_api_key 文件首行
      echo "你的key" > ~/.mp_api_key

配置完成后重新运行本命令。"""

NO_KEY_EXIT = 2


def get_api_key() -> str:
    """解析 API key：环境变量 MP_API_KEY → ~/.mp_api_key 文件首行。

    均缺失时打印中文指引并以退出码 2 退出。
    """
    key = os.environ.get("MP_API_KEY", "").strip()
    if key:
        return key
    key_file = Path.home() / ".mp_api_key"
    if key_file.is_file():
        first = key_file.read_text(encoding="utf-8").strip().splitlines()
        if first and first[0].strip():
            return first[0].strip()
    print(KEY_HELP, file=sys.stderr)
    sys.exit(NO_KEY_EXIT)


def make_rester():
    """返回配置好的 MPRester。注意：须以 with 上下文使用或手动 close。"""
    from mp_api.client import MPRester

    return MPRester(api_key=get_api_key(), mute_progress_bars=True)


def fmt_num(value, digits=4):
    """数值格式化：None → —，浮点保留 digits 位，去掉多余尾零。"""
    if value is None:
        return "—"
    try:
        s = f"{float(value):.{digits}f}".rstrip("0").rstrip(".")
        return s if s else "0"
    except (TypeError, ValueError):
        return str(value)


def structure_info_md(structure, title="晶体结构信息") -> str:
    """pymatgen Structure → Markdown 格式化晶体信息（晶格+坐标表）。"""
    lat = structure.lattice
    lines = [f"## {title}", ""]
    lines.append(f"- 化学式（约简）：**{structure.composition.reduced_formula}**")
    lines.append(f"- 原子数：{len(structure)}")
    lines.append(f"- 体积：{structure.volume:.4f} Å³")
    lines.append(f"- 密度：{structure.density:.4f} g/cm³")
    lines.append("")
    lines.append("### 晶格参数")
    lines.append("")
    lines.append("| 参数 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| a / b / c | {lat.a:.4f} / {lat.b:.4f} / {lat.c:.4f} Å |")
    lines.append(f"| α / β / γ | {lat.alpha:.2f}° / {lat.beta:.2f}° / {lat.gamma:.2f}° |")
    lines.append("")
    lines.append("### 晶格矩阵（行向量，Å）")
    lines.append("")
    for row in lat.matrix:
        lines.append(f"- [{row[0]:>10.5f}, {row[1]:>10.5f}, {row[2]:>10.5f}]")
    lines.append("")
    lines.append("### 原子坐标")
    lines.append("")
    lines.append("| # | 元素 | 分数坐标 (a,b,c) | 笛卡尔坐标 (Å) |")
    lines.append("|---|---|---|---|")
    for i, site in enumerate(structure, 1):
        frac = " ".join(f"{v:.5f}" for v in site.frac_coords)
        cart = " ".join(f"{v:.5f}" for v in site.coords)
        lines.append(f"| {i} | {site.specie} | ({frac}) | ({cart}) |")
    return "\n".join(lines)


def handle_api_error(exc: Exception) -> None:
    """常见 MP API 错误的中文诊断输出。"""
    msg = str(exc)
    print(f"查询失败：{msg}", file=sys.stderr)
    low = msg.lower()
    if "401" in msg or "unauthorized" in low or "invalid" in low and "key" in low:
        print("提示：API key 无效或未授权。请检查 MP_API_KEY 环境变量或 ~/.mp_api_key 文件，"
              "必要时到 https://next-gen.materialsproject.org/dashboard 重新生成。", file=sys.stderr)
    elif "proxy" in low or "connection" in low or "timed out" in low or "unreachable" in low:
        print("提示：网络连接失败。MP API 服务器为 api.materialsproject.org，"
              "如需代理请设置 HTTPS_PROXY / ZCODE_HTTP_PROXY 环境变量后重试。", file=sys.stderr)
    sys.exit(1)
