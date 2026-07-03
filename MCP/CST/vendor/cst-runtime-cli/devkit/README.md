# CST Runtime CLI — 开发包

面向开发者或 agent。独立文件夹，包含参考文档、开发工具和流程说明。

---

## 1. 仓库身份

cst-runtime-cli 是 opencode skill 源码仓库。两个 skill：

- `cst-runtime-cli/` — 基础设施（CLI 入口、100+ 工具、管道）
- `cst-runtime-optimization/` — 优化闭环（仅 SKILL.md，不含代码）

### 绝对禁止

- 禁止在仓库运行 `uv run python -m cst_runtime` 或任何 CST CLI 命令（会产生污染目录）
- 禁止修改 `archive/`、`refs/` 下文件
- 禁止写一次性 Python 脚本绕过 CLI
- 禁止收到修改指令后直接动手——必须先拆解问题、分析影响、给出方案

---

## 2. 快速开始

### 前提条件

- CST Studio Suite 2026 已安装
- 测试区已初始化（`bootstrap.py` → `health-check --auto-fix`）

### 新增 VBA 工具

```powershell
# 1. 查阅官方文档
start "<CST_INSTALL>\\Online Help\\mergedProjects\\VBA_3D\\index.htm"

# 2. 编写 TOML 定义（参考 tools/vba_defs/ 中的示例）
# 3. 生成 Python 工具
uv run python tools/generate_tools.py
# → 输出到 tools/generated/gen_<object>.py

# 4. 部署到测试区
Copy-Item -LiteralPath "tools\generated\gen_*.py" -Destination "<test_workspace>\\.cst_runtime\\cst_runtime\\tools\\" -Force

# 5. 在真实 CST 上逐个工具测试（每个工具独立 run）
#    测试体系详见 references/Test_kit_README.md
cd <test_workspace>
uv run python _test_gen_tools.py

# 6. 通过后注册到 CLI
# 在 cli.py 的 TOOLS dict 中添加: **_NEW_TOOLS
```

### 增强现有工具

```powershell
# 1. 修改函数签名（加带默认值的参数，VBA 模板中 "{param}" 替代硬编码）
# 2. 同步 JSON Schema（新参数声明类型 + 默认值，type 用 number 非 integer）
# 3. 跑合约测试
uv run pytest <repo>\\skills\\cst-runtime-cli\\tests -v
# 4. 默认值向下兼容——新参数默认值 = 旧硬编码值
```

---

## 3. 文件索引

### 参考文档

| 文档 | 内容 |
|------|------|
| `references/vba-official-reference.md` | VBA 官方对象参考——150+ 对象方法签名/参数类型/枚举值 |
| `references/cst-official-api-reference.md` | CST Python API 参考（cst.interface / cst.results / cst.units / C 扩展层） |
| `references/tool-development-guide.md` | 工具开发集成指南——从查文档到 CLI 上线的完整 6 步流程 |
| `references/Test_kit_README.md` | 测试体系全貌——单元测试 + 管道合约测试 + 生成工具验证 |

### 开发工具

| 工具 | 内容 |
|------|------|
| `tools/generate_tools.py` | VBA 代码生成器：读 TOML → 生成 Python 工具函数 |
| `tools/vba_defs/` | TOML 定义模板 — 10 个参考实现 |
| `tools/generated/` | 生成器输出（gen_*.py，不入 git，按需重新生成） |

---

## 4. 两条开发路径

| 场景 | 路径 | 步骤 |
|------|------|------|
| **新对象/新方法** | 代码生成器 | 写 TOML → `generate_tools.py` → `gen_*.py` → CST 实测 |
| **现有工具增强** | 手工修补 | 改 `core/*.py` 函数签名 → 同步 JSON Schema → 合约测试 |

### 管道与原子工具的分工

| 角色 | 说明 | 例子 |
|------|------|------|
| 管道执行 | 编排好的原子调用链 | `inspect-project`、`prepare-experiment`、`run-experiment` |
| 灵活编排 | 单个原子工具 | `set-farfield-monitor`、`change-material` |

原则：管道尽可组合，不是黑箱。

---

## 5. 关键规则

### 设计方法

涉及新功能或修改时，先回答四个问题：

1. **输入输出边界是什么？** 函数的输入从哪来、输出被谁消费
2. **根因在哪个层？** CST COM 行为 / 管道编排 / CLI 注册——不跨层补丁
3. **一次性还是需要灵活性？** 管道覆盖 80% 标准路径，原子工具留给 20% 非标
4. **网上有没有已实现的？** 不要重复造轮

### 实测驱动

遇到 CST 行为不确定时，写最小 Python 脚本直连 COM 查事实：

- `project.modeler.add_to_history("name","VBA")` 执行建模/仿真
- `get_result_item(treepath, run_id=N)` 读 N 号 run 的原始数据
- `get_parameter_combination(run_id)` 获取历史参数

### 常见 CST 陷阱

| 问题 | 原因 | 处理 |
|------|------|------|
| run_id 0 是别名 | 永远指向当前结果 | 导出时跳过 |
| 远场每轮覆盖 | 新仿真覆盖旧远场 | 每轮 export-run-results |
| 远场导出后不可 save | CST 进入错误状态 | close(save=False) |
| modeler/results session 分离 | 不同 session 不同状态 | 仿真后关 modeler，再开 results |
| S11 不是 dB | ydata 是复数 | `20*log10(hypot(real,imag))` |
| modeler 未被废弃 | `add_to_history` 仍是入口 | 用 `add_to_history` |
| model3d 不是建模接口 | 只是历史记录开关 | 建模仍用 modeler |

### VBA 拼装规则

| 参数类型 | Python 传入 | VBA 输出 | 引号 |
|---------|------------|---------|------|
| str | `"brick1"` | `"brick1"` | 加 |
| float | `10.0` | `10.0` | 不加 |
| int | `5` | `5` | 不加 |
| bool | `True` | `True` | 不加 |
| enum | `FieldType.EFIELD` | `"Efield"` | 加（`.value`） |

### 时序约定

- modeler session 与 results session 独立，禁止混用
- 仿真后先关 modeler，再 results 侧 reopen 刷新
- 远场导出放流程最后，导出后 `close(save=False)`
- `close_project()` 默认 `kill_processes=True`，自动清理孤悬 DE
- `change-parameter` 改参后必须 save → close → reopen → 仿真才能生效

---

## 6. TOML 编写规则

- **只加优化流程相关方法**——不照抄官方文档
- **布尔**：`type = "bool"`，默认值 `"true"` / `"false"`（TOML 小写，生成器转 Python True/False）
- **枚举**：`[enums.EnumName]` 下 `values = [...]`，值必须与 VBA_3D HTML 一致
- **硬编码参数**：标注 `hardcoded = "Literal"`，不暴露到函数签名
- **参数去重**：同名同类型自动合并，同名不同类型生成器报错
- **block_end**：标记 With 块的最后一个方法

### Schema 规则

- 参数类型 `number`（非 `integer`），布尔用 `"boolean"`
- `default` 字段必填（保证 agent 知道可选参数的存在）
- `description` 描述功能而非实现

---

## 7. 结构

```
devkit/
├── README.md
├── references/
│   ├── vba-official-reference.md
│   ├── cst-official-api-reference.md
│   ├── tool-development-guide.md
│   └── Test_kit_README.md
└── tools/
    ├── generate_tools.py
    ├── vba_defs/           ← 10 个 TOML 参考实现
    └── generated/           ← 生成器输出（不入 git）
```

---

## 8. 外部资源

| 资源 | URL |
|------|-----|
| CST 内建 VBA 文档 | `<CST_INSTALL>\Online Help\mergedProjects\VBA_3D\index.htm` |
| CST 官方社区 | `3dswym.3dexperience.3ds.com/` |
| EDAboard CST | `edaboard.com/forums/cst-microwave.242/` |
| CST VBA 在线镜像 | `mweda.com/cst/cst2013/` |
