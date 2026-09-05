---
description: 搜索 Materials Project 数据库（按化学式/元素/性质筛选材料）。
argument-hint: "[化学式 | 元素列表 | 条件描述，如: TiO2 或 Li Fe O 稳定相 带隙0.5-2eV]"
skills: mp-database
---

按用户给出的条件搜索 Materials Project 数据库。

用户输入：$ARGUMENTS

执行要求：
1. 将用户条件解析为 `mp_search.py` 参数（化学式 → `--formula`；多元素 → `--elements`；
   带隙范围 → `--band-gap MIN MAX`；"稳定" → `--stable`；"可合成" → `--eabovehull 0.025`）
2. 在**插件根目录**（pyproject.toml 所在目录）执行 `uv run scripts/mp_search.py <参数>`
3. 以 Markdown 表格向用户呈现结果，解读 E_hull 与带隙含义（GGA 低估）
4. 若无匹配，放宽条件重试一次；若提示缺 API key，按 SKILL.md 检查清单第 3 步引导用户配置
5. 主动提示可继续用 /mp-get 获取某条材料的详情与结构
