# mp_search.py 可查询字段速查

`--fields` 参数（逗号分隔）可从 Materials Project summary 端点选取以下常用字段。
未指定时默认输出：material_id, formula_pretty, symmetry（渲染为空间群符号）,
band_gap, energy_above_hull, is_stable, density, volume。

## 基础信息

| 字段 | 含义 | 单位/类型 |
|---|---|---|
| material_id | MP 材料编号 | mp-xxxx |
| formula_pretty | 约简化学式 | 字符串 |
| formula_anonymous | 匿名化学式（按元素比例，如 A2B） | 字符串 |
| elements | 元素列表 | 列表 |
| nelements | 元素数目 | 整数 |
| nsites | 单胞原子数 | 整数 |
| chemsys | 化学体系 | 如 Li-Fe-O |
| theoretical | 是否纯理论数据（无实验收录） | 布尔 |

## 结构与对称性

| 字段 | 含义 |
|---|---|
| density | 密度 (g/cm³) |
| volume | 单胞体积 (Å³) |
| symmetry | 对称性对象：`symbol`（HM 符号）、`number`（国际编号）、`crystal_system`（晶系）、`point_group`（点群） |

> 注意：API 顶层没有 `spacegroup_symbol` / `crystal_system` 字段，空间群与晶系信息都在
> `symmetry` 对象内。mp_search.py 的默认表格会自动把 `symmetry` 渲染为空间群符号；
> `--fields` 里写 `symmetry` 得到空间群符号，写 `crystal_system` 得到晶系（脚本会自动提取）。

## 电子性质

| 字段 | 含义 | 单位 |
|---|---|---|
| band_gap | GGA/PBE 带隙（系统性低估） | eV |
| efermi | 费米能级 | eV |
| is_metal | 是否金属 | 布尔 |
| is_gap_direct | 带隙是否直接 | 布尔 |
| ordering | 磁序（FM=铁磁 / AFM=反铁磁 / NM=非磁 / Unknown） | 字符串 |
| total_magnetization | 总磁矩 | μB |
| is_magnetic | 是否磁性材料 | 布尔 |

## 能量与热力学

| 字段 | 含义 | 单位 |
|---|---|---|
| formation_energy_per_atom | 形成能 | eV/atom |
| energy_above_hull | 凸包上方能量（E_hull，越小越稳定） | eV/atom |
| is_stable | 是否凸包稳定相 | 布尔 |
| uncorrected_energy_per_atom | 未校正总能量 | eV/atom |
| equilibrium_reaction_energy_per_atom | 平衡反应能量 | eV/atom |

## 常用过滤参数（命令行）与字段对应

| 命令行参数 | 对应字段/含义 |
|---|---|
| `--band-gap MIN MAX` | band_gap 范围 |
| `--stable` | is_stable = True |
| `--eabovehull MAX` | energy_above_hull ∈ (0, MAX] |
| `--crystal-system` | symmetry.crystal_system |
| `--spacegroup` | symmetry.symbol |
| `--num-elements MIN MAX` | nelements 范围 |

## 解读判据

- E_hull ≤ 0.025 eV/atom：通常视为可合成候选（实验可及性经验阈值）
- E_hull = 0：凸包稳定相（is_stable = True）
- band_gap = 0：金属；> 0：半导体/绝缘体（PBE 低估，实际值可能更大）
