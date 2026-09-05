---
description: 对晶体结构进行处理（信息提取/对称性/单胞转换/超胞/XRD/格式转换）。
argument-hint: "[结构文件 | mp-xxxx] [操作，如: --symmetry / --supercell 2 2 1 / --convert poscar]"
skills: mp-database
---

对晶体结构执行处理操作。

用户输入：$ARGUMENTS

执行要求：
1. 确定输入源：本地结构文件路径，或 mp-xxxx（用 `--from-mp`）；两者都没有时先请用户确认目标结构
2. 将用户需求映射为 `mp_process.py` 操作：
   - "看看结构/信息" → `--info`
   - "空间群/对称性" → `--symmetry`
   - "原胞/惯用胞" → `--primitive` / `--conventional`
   - "扩胞/超胞 N×N×N" → `--supercell A B C`
   - "XRD/衍射" → `--xrd`（指定波长用 `--wavelength`）
   - "转成 CIF/POSCAR" → `--convert cif|poscar [-o 目标路径]`
3. 在**插件根目录**执行 `uv run scripts/mp_process.py <文件或--from-mp> <操作>`
4. 向用户呈现结果并解读（空间群编号、XRD 主峰、超胞原子数等）
5. 强调原始文件未被修改，派生文件路径已报告；slab/掺杂/吸附等高级生成转交 structure-prep 技能
