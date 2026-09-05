---
description: 获取 Materials Project 材料详情与晶体结构（可导出 CIF/POSCAR）。
argument-hint: "[mp-xxxx] [--structure] [--save cif,poscar] [导出目录]"
skills: mp-database
---

获取指定 Materials Project 材料的信息与晶体结构。

用户输入：$ARGUMENTS

执行要求：
1. 从输入中提取 material_id（如 mp-149）；未给出时先用 /mp-search 搜索确认
2. 在**插件根目录**执行 `uv run scripts/mp_get.py <material_id> [选项]`：
   - 用户要结构详情 → 加 `--structure`
   - 用户要导出 → 加 `--save cif,poscar`（按需），可加 `--outdir <目录>`
   - 用户要惯用胞/原胞 → 加 `--conventional` / `--primitive`
3. 向用户呈现格式化摘要（化学式、空间群、带隙、形成能、E_hull、密度等），说明 GGA 带隙低估惯例
4. 导出文件后报告完整路径；文件名携带 entry ID，符合 structure-prep 技能的衔接要求
5. 若提示缺 API key，按 SKILL.md 检查清单第 3 步引导用户配置
