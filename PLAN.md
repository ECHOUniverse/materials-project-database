# Materials Project 数据库 ZCode 插件 — 实施计划

> 目标：为 ZCode 创建 Materials Project（MP）数据库插件，实现：
> 1. 链接 MP API 获取数据库内容
> 2. 查找（搜索）数据库
> 3. 获取格式化晶体信息输出
> 4. 对晶体信息进行处理
>
> 参考 API：https://next-gen.materialsproject.org/api

## 0. 背景调研结论

### ZCode 插件体系（来自本机官方插件逆向探索）
- 插件最小必需结构：一个目录 + `.zcode-plugin/plugin.json`（仅 `name` 必填，须匹配 `^[a-z0-9][a-z0-9._-]{0,127}$`）
- 组件字段（值为目录名字符串、数组或内联定义）：`skills`、`commands`、`agents`、`hooks`、`mcpServers`
- 本地安装路径：把插件放进带 `marketplace.json` 的目录（`plugins[].source` 用相对路径字符串指向插件子目录），然后在 ZCode
  Settings → Plugin Management → Discover → `+` 添加该目录为 marketplace 并安装
- 运行时环境变量：`ZCODE_PLUGIN_ROOT`、`ZCODE_PLUGIN_DATA`、`ZCODE_PLUGIN_ID`
- `userConfig` 字段可声明用户配置项并通过 `${user_config.<key>}` 注入 MCP env（本项目用 skill+CLI，暂不需要）

### Materials Project API（mp-api 官方文档）
- 官方 Python 客户端：`mp-api`，要求 **Python 3.11+**，核心依赖 `pymatgen`（自动安装）
- 认证：`MPRester(api_key=...)` 或环境变量 `MP_API_KEY`；key 在 next-gen.materialsproject.org 免费注册获取
- 搜索：`mpr.materials.summary.search(formula=..., elements=..., chemsys=..., band_gap=(min,max), is_stable=..., energy_above_hull=..., crystal_system=..., spacegroup_symbol=..., num_elements=..., fields=[...])`
- 结构获取：`mpr.get_structure_by_material_id("mp-149", conventional_unit_cell=True/False, final=True/False)`
- 导出：`structure.to(filename="x.cif", fmt="cif")`；`Poscar(structure).write_file("POSCAR")`
- 默认 endpoint：`https://api.materialsproject.org`

### 本机环境现状
- 当前仓库：全新空 git 仓库（main 分支，零提交）
- `mp_api` / `pymatgen` / `ase` 均未安装；conda 不可用；**uv 可用**（CPython 3.12.13）
- 用户现有 skills 生态（structure-prep / vasp）统一使用 `uv run scripts/xxx.py` 惯例
- 生态衔接约定：从数据库获取的结构必须携带 entry ID；原始结构文件保留不动，派生结构写入新路径；
  slab/吸附/掺杂等高级结构生成属于 structure-prep 技能职责；DFT 计算属于 vasp 技能职责

## 1. 总体方案（已决策）

- **实现形式**：Skill + Python CLI 脚本（非 MCP 服务器）。与现有 structure-prep/vasp 生态一致，
  输出 Markdown/JSON 对 agent 友好，开发维护简单
- **处理范围**：基础处理（原胞/惯用胞、超胞、对称性、XRD、格式转换、信息提取）内置本插件；
  高级结构生成（slab、吸附、掺杂）在 SKILL.md 中写明转交 structure-prep 技能，避免功能重复
- **依赖管理**：插件目录内独立 uv 项目（pyproject.toml），脚本一律 `uv run scripts/xxx.py` 调用，
  兼容插件被安装（拷贝到 cache 目录）后的场景

## 2. 目录结构

```
materials-project-database/
├── PLAN.md                               # 本文件
├── marketplace.json                      # 本地 marketplace（source 指向 ./plugins/materials-project）
├── README.md                             # 中文安装与使用说明
├── .gitignore                            # .venv / __pycache__ / uv.lock 可选忽略策略
└── plugins/
    └── materials-project/                # 插件本体
        ├── .zcode-plugin/
        │   └── plugin.json               # 清单：name/version/skills/commands
        ├── pyproject.toml                # uv 项目：mp-api + pymatgen（requires-python >=3.11）
        ├── README.md                     # 插件级说明（可选，简短）
        ├── skills/
        │   └── mp-database/
        │       ├── SKILL.md              # 主技能文档
        │       └── references/
        │           ├── search-fields.md  # summary 端点可查询字段/性质速查表
        │           └── structure-processing.md  # 结构处理操作详解与参数说明
        ├── commands/
        │   ├── mp-search.md              # /mp-search — 按化学式/元素/性质搜索
        │   ├── mp-get.md                 # /mp-get  — 获取材料详情+晶体结构导出
        │   └── mp-process.md             # /mp-process — 本地/MP 结构处理
        └── scripts/
            ├── _mp_common.py             # 公共库：key 解析、MPRester 工厂、格式化输出
            ├── mp_search.py              # 数据库搜索 CLI
            ├── mp_get.py                 # 材料 详情/结构/多格式导出 CLI
            └── mp_process.py             # 结构处理 CLI
```

## 3. 组件设计

### 3.1 plugin.json
```json
{
  "name": "materials-project",
  "version": "0.1.0",
  "description": "Materials Project 数据库查询、晶体结构获取与处理工具集",
  "description_i18n": { "en": "Materials Project database search, crystal structure retrieval and processing", "zh-CN": "Materials Project 数据库查询、晶体结构获取与处理工具集" },
  "author": { "name": "hanxu" },
  "license": "MIT",
  "skills": "skills",
  "commands": "commands"
}
```

### 3.2 marketplace.json（仓库根，本地 marketplace）
```json
{
  "name": "materials-project-local",
  "owner": { "name": "hanxu" },
  "plugins": [
    {
      "name": "materials-project",
      "source": "./plugins/materials-project",
      "description": "Materials Project 数据库查询与晶体结构处理",
      "category": "scientific-computing"
    }
  ]
}
```

## 4. 脚本功能规格

### 4.1 _mp_common.py（公共库，非 CLI）
- `get_api_key()`：解析顺序 `MP_API_KEY` 环境变量 → `~/.mp_api_key` 文件（首行）；均缺失时打印中文指引
  （到 https://next-gen.materialsproject.org/dashboard 注册免费获取，写出两种配置方法）并以退出码 2 退出
- `make_rester()`：返回配置好的 MPRester（mute_progress_bars=True，use_document_model=False 按 dict 处理更稳）
- 结构格式化：晶格参数表、原子坐标表、材料摘要 Markdown 渲染
- 统一输出风格：中文标签 + Markdown 表格；`--json` 时输出机器可读 JSON
- 统一错误处理：401（key 无效）、网络/代理失败、material_id 不存在

### 4.2 mp_search.py — 查找数据库
- 必选其一的查询条件：`--formula TiO2` / `--elements Li Fe O`（多元素） / `--chemsys Li-Fe-O` / `--ids mp-13 mp-14`
- 可选过滤：`--band-gap MIN MAX`、`--stable`、`--eabovehull MAX`、`--crystal-system cubic`、
  `--spacegroup Fm-3m`、`--num-elements MIN MAX`、`--fields f1,f2`、`--limit N`（默认 20）、`--json`
- 默认输出 Markdown 表：material_id、化学式、空间群、晶系、带隙 (eV)、E_above_hull (eV/atom)、稳定、密度、体积
- 结果按 energy_above_hull 升序（最稳定在前）

### 4.3 mp_get.py — 获取格式化晶体信息
- 位置参数：material_id（如 mp-149）
- 默认：材料摘要（化学式、带隙、形成能、磁序、体积、密度、空间群、同分异构体等，Markdown 分节）
- `--structure`：晶格 a/b/c/α/β/γ、晶格矩阵、原子分数/笛卡尔坐标表
- `--conventional` / `--primitive`：取惯用胞 / 原胞（默认 MP final 弛豫结构）
- `--save cif,poscar,json`：导出 `mp-149.cif` / `POSCAR-mp-149` / `mp-149.json`；`--outdir DIR`（默认当前目录）
- `--json`：全文机器可读输出
- 遵循惯例：导出文件名携带 entry ID

### 4.4 mp_process.py — 晶体信息处理
- 输入：本地结构文件（cif/poscar/vasp/json/xsd 等按扩展名自动识别）或 `--from-mp mp-149`
- 操作（可组合，按序执行，链式处理）：
  - `--info`：结构摘要（成分、晶格、体积、密度、原子数）
  - `--symmetry`：空间群分析（SpacegroupAnalyzer：国际编号、HM 符号、晶系、点群）
  - `--primitive` / `--conventional`：标准化转换
  - `--supercell A B C`：超胞（默认 1 1 1 = 不变）
  - `--xrd`：粉末 XRD（默认 Cu Kα，`--wavelength` 可选；输出 2θ–强度表，最强峰归一化 100）
  - `--convert FMT` + `-o FILE`：导出为 cif/poscar/json/xyz 等格式
- 惯例：原始文件只读不修改；派生结构输出到新文件（默认名 `<原名>-<op>.<ext>`，或 `-o` 指定），
  携带来源 entry ID（`--from-mp` 时）
- 不内置：slab 生成、掺杂、吸附、空位 → SKILL.md 指引转交 structure-prep 技能

### 4.5 skills/mp-database/SKILL.md
- frontmatter：`name: mp-database`、description（触发信号：查 MP、Materials Project、按性质筛选材料、
  下载 CIF/POSCAR、晶体结构处理等）
- 正文分节：
  1. 首次使用检查清单（`cd 插件目录 && uv sync`；key 检测与两种配置方法）
  2. 三个脚本的用法速查与典型示例
  3. 输出解读（字段含义、稳定性判据 E_hull<25 meV/atom 惯例等）
  4. 工作流衔接：获取结构 → structure-prep（slab/掺杂）→ vasp（DFT）
  5. 错误排查：401 / 无网络或需代理 / Python 版本
- references/ 两份参考文档按需加载（渐进式披露）

### 4.6 commands/*.md（斜杠命令）
- `mp-search.md`：argument-hint `[化学式/元素/条件]`，正文引导调用 mp_search.py
- `mp-get.md`：argument-hint `[material_id] [导出格式]`
- `mp-process.md`：argument-hint `[结构文件或mp-id] [操作]`

## 5. 验证步骤
1. 插件目录 `uv sync` 成功创建 .venv 并安装 mp-api/pymatgen
2. 无 key 时运行 `mp_search.py --formula TiO2` → 输出清晰中文指引、退出码 2（不崩溃、不堆栈）
3. 离线链路（不依赖 API key）：用 pymatgen 构造测试结构文件，验证 `mp_process.py` 的
   info/symmetry/supercell/xrd/convert 全部操作
4. 在线链路（key 就绪后）：`--formula TiO2` 搜索、`mp-149` 摘要与结构、`--save cif,poscar` 导出
5. `uv run python -c "import mp_api"` 等冒烟检查
6. README 安装路径复核：ZCode Settings → Plugin Management → Discover → `+` 添加仓库根目录

## 6. 交付物清单
- [ ] PLAN.md（本文件）
- [ ] marketplace.json + README.md + .gitignore
- [ ] plugins/materials-project/.zcode-plugin/plugin.json
- [ ] pyproject.toml（uv，Python>=3.11，mp-api）
- [ ] scripts/_mp_common.py、mp_search.py、mp_get.py、mp_process.py
- [ ] skills/mp-database/SKILL.md + references/search-fields.md + references/structure-processing.md
- [ ] commands/mp-search.md、mp-get.md、mp-process.md
- [ ] 验证通过（第 5 节 1–3、5 项；第 4 项需用户 key）
- [ ] git 初始提交

## 7. 风险与备注
- MP API key 由用户自行申请配置，插件只负责读取与指引，不代管不存储
- 插件安装到 cache 后路径会变化，脚本内部不做任何绝对路径依赖；SKILL.md 中 `uv sync` 需在插件根执行
- mp-api 要求 Python>=3.11，本机 uv 默认 CPython 3.12.13 满足
- GitHub 直连受限时按用户全局规则使用 jsdelivr CDN（本项目依赖来自 PyPI，一般不受影响）
