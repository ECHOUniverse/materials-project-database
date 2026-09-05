# materials-project-database

为 [ZCode](https://z.ai) 创建的 **Materials Project (MP) 数据库插件**：连接 MP API 查询数据库、获取格式化晶体信息、并对晶体结构进行处理。

## 功能

- **搜索数据库**：按化学式 / 元素组合 / 化学体系 / material ID 搜索，支持带隙、稳定性、E_hull、晶系、空间群等性质过滤
- **获取晶体信息**：材料摘要（带隙、形成能、磁序、密度等）、晶格参数与原子坐标表，导出 CIF / POSCAR / JSON（文件名携带 entry ID）
- **晶体结构处理**：结构信息提取、空间群对称性分析、原胞/惯用胞转换、超胞构建、粉末 XRD 模拟、格式转换（可链式组合）
- **生态衔接**：slab / 掺杂 / 吸附等高级结构生成转交 `structure-prep` 技能；DFT 计算转交 `vasp` 技能

实现为 **Skill + CLI 脚本**（uv 管理依赖，`mp-api` + `pymatgen`），脚本输出对 agent 友好的 Markdown / JSON。

## 安装（本地 marketplace）

1. 打开 ZCode **Settings → Plugin Management → Discover → `+`**，选择本仓库根目录（含 `marketplace.json`）添加为 marketplace
2. 安装其中的 `materials-project` 插件并启用
3. 安装后即获得技能 `mp-database` 与三个斜杠命令：`/mp-search`、`/mp-get`、`/mp-process`

## 配置 API key（必需）

1. 到 [MP Dashboard](https://next-gen.materialsproject.org/dashboard) 免费注册获取 API key
2. 配置（二选一）：
   ```bash
   # 方式 a：环境变量（推荐）
   echo 'export MP_API_KEY="你的key"' >> ~/.zshrc && source ~/.zshrc
   # 方式 b：key 文件
   echo "你的key" > ~/.mp_api_key
   ```

插件读取顺序：`MP_API_KEY` 环境变量 → `~/.mp_api_key` 文件；缺失时脚本会打印中文配置指引并以退出码 2 退出。

## 环境准备

插件脚本依赖通过 uv 管理（Python ≥ 3.11，`mp-api` + `pymatgen`）。首次使用需在**插件根目录**（`plugins/materials-project/`，即 `pyproject.toml` 所在目录）执行：

```bash
uv sync
```

## 手动使用（不经过 agent）

```bash
cd plugins/materials-project

# 搜索：稳定相 TiO2，带隙 0.5–2 eV
uv run scripts/mp_search.py --formula TiO2 --stable --band-gap 0.5 2.0

# 获取 mp-149 详情、结构坐标表并导出 CIF/POSCAR
uv run scripts/mp_get.py mp-149 --structure --save cif,poscar --outdir structures

# 结构处理：对称性分析 + 超胞 + XRD
uv run scripts/mp_process.py structures/mp-149.cif --symmetry
uv run scripts/mp_process.py structures/mp-149.cif --supercell 2 2 1 --xrd --convert poscar -o super.vasp
```

各脚本 `--help` 查看完整参数。更多可查字段见 `plugins/materials-project/skills/mp-database/references/`。

## 目录结构

```
├── PLAN.md                  # 实施计划
├── marketplace.json         # 本地 marketplace 定义
└── plugins/materials-project/
    ├── .zcode-plugin/plugin.json   # 插件清单
    ├── pyproject.toml       # uv 依赖（mp-api, pymatgen）
    ├── skills/mp-database/  # 技能（SKILL.md + references）
    ├── commands/            # /mp-search /mp-get /mp-process
    └── scripts/             # mp_search / mp_get / mp_process + 公共库
```

## 已验证

- 无 API key 时输出中文配置指引、退出码 2
- 结构处理离线全链路（金红石 TiO2 测试结构）：info / symmetry（P4₂/mnm #136）/ supercell / XRD（主峰 27.46° 与文献一致）/ convert（cif·poscar·json）
- 在线查询（search / get）需配置 API key 后使用

## License

MIT
