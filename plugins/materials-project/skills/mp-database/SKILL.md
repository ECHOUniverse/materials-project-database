---
name: mp-database
description: 查询 Materials Project (MP) 材料数据库、按化学式/元素/性质搜索材料、获取晶体结构并导出 CIF/POSCAR、对晶体结构进行处理（对称性分析/超胞/XRD/格式转换）。当用户提到 Materials Project、MP 数据库、mp-xxxx 材料编号、查带隙/形成能、下载晶体结构文件时使用。
---

# Materials Project 数据库技能

通过 `mp-api`（官方 Python 客户端）连接 Materials Project 数据库，提供搜索、结构获取和结构处理三类能力。

## 脚本位置与运行方式

所有脚本位于本技能插件根目录 `scripts/` 下，**必须用 `uv run` 在插件根目录执行**：

```bash
cd <插件根目录>   # 即 pyproject.toml 所在目录
uv run scripts/mp_search.py --help
uv run scripts/mp_get.py --help
uv run scripts/mp_process.py --help
```

脚本输出 Markdown（人读）或 JSON（`--json`，机器读）。所有面向用户的提示均为中文。

## 首次使用检查清单

1. **环境同步**（仅需一次；插件更新后重做）：
   ```bash
   cd <插件根目录> && uv sync
   ```
   要求 Python ≥ 3.11（uv 会自动管理）。
2. **API key 检测**：
   ```bash
   [ -n "$MP_API_KEY" ] && echo "环境变量已配置" || ([ -s ~/.mp_api_key ] && echo "key 文件已配置" || echo "未配置")
   ```
3. **key 配置**（缺失时按以下顺序引导用户，二选一）：
   - 环境变量：`~/.zshrc` 中 `export MP_API_KEY="..."` 后 `source ~/.zshrc`
   - key 文件：`echo "..." > ~/.mp_api_key`
   - key 在 https://next-gen.materialsproject.org/dashboard 免费注册获取
   - 两个脚本级兜底：直接运行任一脚本，无 key 时会打印详细中文指引并以退出码 2 退出

**不要**向用户索要 key 明文或代写 key 到文件——引导用户自行配置即可。

## 能力一：搜索数据库（mp_search.py）

查询条件四选一（互斥）：`--formula`、`--elements`、`--chemsys`、`--ids`。

```bash
# 按化学式搜索（支持通配符 *）
uv run scripts/mp_search.py --formula TiO2

# 按元素组合 + 性质过滤：稳定相、带隙 0.5–2 eV
uv run scripts/mp_search.py --elements Li Fe O --stable --band-gap 0.5 2.0

# E_above_hull ≤ 0.025 eV/atom，最多 50 条
uv run scripts/mp_search.py --chemsys Li-Fe-O --eabovehull 0.025 --limit 50

# 按晶系/空间群过滤
uv run scripts/mp_search.py --formula Fe2O3 --crystal-system hexagonal --spacegroup R-3c
```

可选过滤：`--band-gap MIN MAX`、`--stable`、`--eabovehull MAX`、`--crystal-system`（triclinic/monoclinic/orthorhombic/tetragonal/trigonal/hexagonal/cubic）、`--spacegroup`、`--num-elements MIN MAX`、`--fields 字段1,字段2`（更多可查字段见 `references/search-fields.md`）、`--limit`、`--json`。

默认输出 Markdown 表：material_id、化学式、空间群、晶系、带隙、E_hull、稳定、密度、体积，按 E_hull 升序。

## 能力二：获取材料详情与晶体结构（mp_get.py）

```bash
uv run scripts/mp_get.py mp-149                     # 材料摘要（带隙/形成能/磁性/…）
uv run scripts/mp_get.py mp-149 --structure         # 摘要 + 晶格参数、原子坐标表
uv run scripts/mp_get.py mp-4163 --conventional --save cif,poscar --outdir structures
uv run scripts/mp_get.py mp-149 --primitive --json
```

- `--conventional` 惯用单胞 / `--primitive` 原胞（默认 MP 收录的弛豫结构）；`--initial` 取弛豫前初始结构
- `--save cif,poscar,json` 导出文件，命名携带 entry ID（如 `mp-4163.cif`、`POSCAR-mp-4163`）

## 能力三：晶体结构处理（mp_process.py）

输入为本地结构文件（cif/poscar/vasp/json）或 `--from-mp mp-xxxx`。**原始文件只读**，派生结构写新文件。

```bash
uv run scripts/mp_process.py POSCAR --info                    # 结构摘要
uv run scripts/mp_process.py mp-149.cif --symmetry            # 空间群/点群分析
uv run scripts/mp_process.py s.cif --supercell 2 2 1 --convert poscar -o super.vasp
uv run scripts/mp_process.py --from-mp mp-149 --xrd           # XRD 模拟（默认 Cu Kα，--wavelength 可改）
uv run scripts/mp_process.py s.cif --primitive --convert cif -o s-prim.cif
```

操作可链式组合，按 info → symmetry → primitive/conventional → supercell → xrd → convert 顺序执行。

## 结果解读惯例

- **稳定性**：`energy_above_hull`（E_hull）≤ 0.025 eV/atom 通常视为可合成候选；`is_stable` = E_hull 为 0 的凸包稳定相
- **带隙**：MP 默认值为 GGA/PBE 计算，系统性低估实际带隙；作定性判断（金属/半导体/绝缘体）而非定量
- **形成能**：`formation_energy_per_atom`，单位 eV/atom
- 字段含义详见 `references/search-fields.md`，处理操作详见 `references/structure-processing.md`

## 工作流衔接

1. **查材料 → 取结构**：`mp_search.py` 找到目标 material_id → `mp_get.py --save cif,poscar` 导出
2. **结构处理**：本技能做对称性/超胞/转换/XRD；**slab 生成、掺杂、吸附、空位等高级结构生成转交 structure-prep 技能**（从 MP 拿到的结构必须携带 entry ID 交给它）
3. **计算**：处理好的结构转交 vasp 技能（POSCAR 需与其 POTCAR 物种顺序规则核对）

## 错误排查

| 现象 | 处置 |
|---|---|
| 退出码 2，提示缺少 API key | 按"首次使用检查清单"第 3 步引导配置 |
| 401 / unauthorized | key 无效或过期，到 MP dashboard 重新生成 |
| 网络连接失败 / 超时 | MP API 为 api.materialsproject.org；需代理时设 `HTTPS_PROXY`（ZCode 环境用 `ZCODE_HTTP_PROXY`）后重试 |
| 未找到 material_id | 用 `mp_search.py` 确认 ID；MP ID 形如 mp-xxxx / mvc-xxxx |
| Python 版本错误 | `uv sync` 会自动选 ≥3.11 解释器，确认 uv 可用 |
| 输出为空 | 放宽过滤条件（去掉 --stable / --band-gap），或用通配符化学式 |
