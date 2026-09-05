# mp_process.py 结构处理操作详解

输入：本地结构文件（`.cif` / `.poscar` / `.vasp` / `.json`）或 `--from-mp mp-xxxx`。
所有操作**不修改原始文件**，派生结构写入新文件；`--from-mp` 产生的派生文件名携带 entry ID。

## 操作一览（可组合，按序执行）

| 操作 | 参数 | 说明 |
|---|---|---|
| 结构摘要 | `--info` | 成分、原子数、体积、密度、晶格参数 |
| 对称性分析 | `--symmetry` | 空间群（HM 符号+编号）、晶系、点群（symprec=0.01） |
| 转原胞 | `--primitive` | 原胞标准形（primitive standard） |
| 转惯用胞 | `--conventional` | 惯用单胞标准形；与 `--primitive` 互斥 |
| 超胞 | `--supercell A B C` | 沿晶格矢量 a/b/c 方向各扩 A/B/C 倍 |
| XRD 模拟 | `--xrd` | 粉末衍射 2θ–强度表（最强峰归一化 100），最多列 30 峰 |
| 格式转换 | `--convert FMT` | FMT = cif / poscar / json / xyz |

其他参数：`--wavelength`（XRD 波长，默认 CuKa=1.54184 Å，可传浮点 Å 值）、
`-o FILE`（导出路径）、`--json`（机器可读输出）。

## 输出文件命名

未用 `-o` 时自动命名：`<原名>-<操作标签>.<ext>`，操作标签按实际链取，如
`s.cif --supercell 2 2 1 --convert poscar` → `s-supercell-2x2x1.vasp`；
`--from-mp mp-149 --primitive --convert cif` → `mp-149-primitive.cif`。
poscar 格式默认扩展名 `.vasp`（pymatgen 识别），文件内容即 VASP POSCAR。

## 结果解读

- **对称性**：`--symmetry` 用 SpacegroupAnalyzer（symprec=0.01）。结构畸变较大时可先 `--primitive` 或用 MP 弛豫结构原文件；对称性结果与 MP 收录的 spacegroup 字段可能因标准化方式不同而略有差异
- **超胞**：仅平移复制，不改变内部坐标；用于后续缺陷/吸附建模前的扩胞
- **XRD**：基于结构因子计算的理想粉末图，无择优取向/仪器展宽；峰位（2θ）可靠，相对强度为定性参考
- **转换**：cif↔poscar 无损（保留晶格+坐标）；poscar→xyz 会丢失晶格（xyz 不含周期信息），仅用于分子/团簇用途

## 与其他技能的衔接

- 从 MP 导出的结构交 **structure-prep** 做 slab / 掺杂 / 吸附 / 空位等高级生成（必须携带 entry ID）
- 生成的 POSCAR 交 **vasp** 前注意物种顺序需与 POTCAR 一致
- 本脚本不含：slab 生成、原子替换掺杂、空位删除、吸附物放置——这些属于 structure-prep 职责
