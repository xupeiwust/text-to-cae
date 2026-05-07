# Text to CAE 使用教程

**语言：** [English](README.md) | 中文

Text to CAE 是一个本地运行的 Abaqus 仿真工作区，带有浏览器结果查看器。它适合用 Codex、Cursor、Claude Desktop 等 AI 客户端编写和修改 Abaqus Python 脚本，然后通过 Abaqus/CAE 求解，并把结果导出到浏览器中交互查看。

项目连接三层能力：

- **Abaqus/CAE**：负责真实建模、网格划分、提交作业和生成 ODB 结果数据库。
- **Abaqus MCP**：让 AI 客户端可以检查和控制当前 Abaqus/CAE 会话。
- **Text to CAE Viewer**：在浏览器中加载 `result_mesh.json`、项目元数据、参数、时间帧、云图和模型树。

项目仓库：

```text
https://github.com/Cai-aa/text-to-cae
```

配套 Abaqus MCP 仓库：

```text
https://github.com/Cai-aa/abaqus-mcp
```

## 推荐工作流

```text
Codex 或其他支持 MCP 的 AI 客户端
  -> 通过 Abaqus MCP 连接 Abaqus/CAE
  -> 创建或修改 Abaqus Python 脚本
  -> 让 Abaqus 建模、划分网格、求解、读取 ODB
  -> 导出 result_mesh.json
  -> 打开 Text to CAE 浏览器 viewer 查看结果
```

这个分工比较清晰：

- AI 客户端负责自然语言理解、代码修改、脚本调试和自动化。
- Abaqus/CAE 负责真实求解。
- 浏览器 viewer 负责快速交互式检查 CAE 结果。

## 环境要求

- Windows
- Node.js 和 npm
- Abaqus/CAE，用于真实求解
- Abaqus 脚本可用的 Python 环境
- 可选：支持 MCP 的 AI 客户端，以及 [Abaqus MCP](https://github.com/Cai-aa/abaqus-mcp)

如果某个案例已经包含 `result_mesh.json`，viewer 可以直接显示。只有需要重新求解或从浏览器触发 Abaqus 时，才必须安装 Abaqus。

## 安装并启动 Viewer

克隆项目：

```powershell
git clone https://github.com/Cai-aa/text-to-cae.git
Set-Location .\text-to-cae
```

安装 viewer 依赖：

```powershell
Set-Location .\viewer
npm.cmd install
```

启动本地 viewer：

```powershell
npm.cmd run dev
```

打开：

```text
http://127.0.0.1:4178/
```

如果 `4178` 端口被占用，可以指定其他端口：

```powershell
$env:VIEWER_PORT = "4181"
npm.cmd run dev
```

然后打开：

```text
http://127.0.0.1:4181/
```

## 打开示例案例

通过 `case` 参数打开指定案例：

```text
http://127.0.0.1:4178/?case=cantilever
http://127.0.0.1:4178/?case=hole-plate
http://127.0.0.1:4178/?case=hole-plate-modal
http://127.0.0.1:4178/?case=sphere-impact
http://127.0.0.1:4178/?case=milling-3d
http://127.0.0.1:4178/?case=gear-mesh
http://127.0.0.1:4178/?case=bullet-plate
```

Abaqus 风格结果界面：

```text
http://127.0.0.1:4178/?case=sphere-impact&mode=cae
```

## 通过浏览器运行 Abaqus

Vite dev server 内置了本地 CAE API：

```text
/__cae/project
/__cae/result-mesh
/__cae/result-summary
/__cae/parameters
/__cae/run
```

对于可运行案例，浏览器可以修改参数并触发 Abaqus noGUI：

```text
viewer
  -> /__cae/run
  -> Abaqus noGUI
  -> *_abaqus.py
  -> export_*.py
  -> result_mesh.json
  -> viewer 刷新结果
```

默认 Abaqus 路径：

```text
G:\SIMULIA\Commands\abaqus.bat
```

如果 Abaqus 安装在其他位置，启动 viewer 前设置：

```powershell
$env:ABAQUS_COMMAND = "C:\SIMULIA\Commands\abaqus.bat"
npm.cmd run dev
```

## 案例文件结构

每个案例通常包含：

```text
models/<case>/
  cae_parameters.json
  cae_project.json
  *_abaqus.py
  export_*.py
  result_mesh.json
```

文件职责：

- `*_abaqus.py`：创建 Abaqus 模型、材料、网格、分析步、载荷、边界条件并提交 job。
- `export_*.py`：从 ODB 导出 viewer 可读取的网格、云图、位移、模态或动态帧。
- `result_mesh.json`：viewer 加载的主要结果数据。
- `cae_project.json`：项目元数据、流程状态、模型树、输出路径和结果指标。
- `cae_parameters.json`：浏览器运行面板中的可编辑参数。

## 内置示例

| 案例 | 目录 | 说明 |
| --- | --- | --- |
| 悬臂梁 | `models/text-to-cae` | 静力学入门案例，展示位移和应力云图。 |
| 带孔板拉伸 | `models/text-to-cae-hole-plate` | 展示圆孔板拉伸载荷下的应力集中。 |
| 带孔板模态 | `models/text-to-cae-hole-plate-modal` | 频率提取案例，可查看不同模态帧。 |
| 球冲击板材 | `models/text-to-cae-sphere-impact` | 显式动力学案例，展示球板接触、冲击、压痕和回弹。 |
| 三维铣削 | `models/text-to-cae-milling-3d` | 端铣动力学可视化，包含可编辑加工参数。 |
| 齿轮啮合 | `models/text-to-cae-gear-mesh` | 直齿轮啮合动力学，包含主动轮和从动轮参数。 |
| 弹体侵彻板材 | `models/text-to-cae-bullet-plate` | 高速弹体侵彻板材案例。 |

部分大型结果文件不会提交到仓库，需要在本地通过 Abaqus 或刷新脚本重新生成。

## 刷新可视化结果数据

部分案例包含确定性的刷新脚本，可以不等待完整求解就重建浏览器预览数据：

```powershell
node models\text-to-cae-sphere-impact\refresh_contact_result.mjs
node models\text-to-cae-milling-3d\refresh_visual_result.mjs
node models\text-to-cae-gear-mesh\refresh_gear_result.mjs
```

## 直接运行 Abaqus 脚本

也可以不通过浏览器按钮，直接在命令行运行案例。

球冲击板材：

```powershell
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-sphere-impact\sphere_impact_abaqus.py
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-sphere-impact\export_dynamic_mesh.py
```

三维铣削：

```powershell
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-milling-3d\milling_abaqus.py
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-milling-3d\export_milling_mesh.py
```

齿轮啮合：

```powershell
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-gear-mesh\gear_mesh_abaqus.py
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-gear-mesh\export_gear_mesh.py
```

## 用 MCP 连接 Codex 和 Abaqus

安装 Abaqus MCP：

```powershell
git clone https://github.com/Cai-aa/abaqus-mcp.git $env:USERPROFILE\.abaqus-mcp
pip install mcp
```

让 Abaqus/CAE 加载 MCP 启动环境：

```powershell
Copy-Item -Force "$env:USERPROFILE\.abaqus-mcp\abaqus_v6.env.example" "$env:USERPROFILE\abaqus_v6.env"
```

可选 GUI 菜单插件：

```powershell
Copy-Item -Recurse -Force "$env:USERPROFILE\.abaqus-mcp\abaqus_plugins\mcp_control" "$env:USERPROFILE\abaqus_plugins\mcp_control"
```

重启 Abaqus/CAE 后，从菜单启动：

```text
Plug-ins -> MCP -> Start MCP
```

也可以在 Abaqus Python 控制台启动：

```python
mcp_start()
```

如果 Abaqus 版本的后台线程不稳定，可以使用 cooperative 或 blocking loop：

```python
mcp_coop_loop()
```

或：

```python
mcp_loop()
```

MCP 客户端配置通常类似：

```json
{
  "mcpServers": {
    "abaqus-mcp": {
      "command": "python",
      "args": ["C:/Users/<your-user>/.abaqus-mcp/mcp_server.py"]
    }
  }
}
```

把 `<your-user>` 替换成 Windows 用户名。如果 `python` 不在 `PATH`，可以使用 Python 解释器绝对路径。

## Viewer 操作

界面主要分为：

- 左侧模型树：项目、零件、材料、装配、分析步、载荷、边界条件、网格、作业和结果。
- 中间三维视窗：云图、网格边线、动态帧、模态、刀具、球、齿轮、弹体等对象。
- 右侧面板：状态、指标、可编辑参数和运行控制。

常用操作：

- 左键拖动：旋转模型。
- 中键拖动：平移模型。
- 鼠标滚轮：缩放。
- 播放控制：播放动态或模态帧。
- 主题控制：切换 Abaqus、深色、浅色显示风格。

## 项目结构

```text
text-to-cae/
  README.md
  README.zh-CN.md
  LICENSE
  models/
    text-to-cae/
    text-to-cae-hole-plate/
    text-to-cae-hole-plate-modal/
    text-to-cae-sphere-impact/
    text-to-cae-milling-3d/
    text-to-cae-gear-mesh/
    text-to-cae-bullet-plate/
  viewer/
    package.json
    vite.config.mjs
    main.jsx
    components/
      CaeResultViewer.js
      TextToCaeWorkspace.js
```

## Git 和大文件

仓库会排除生成文件和大型本地文件，例如：

- `viewer/node_modules/`
- `viewer/dist/`
- `viewer/dist-verify/`
- Abaqus `.odb`
- Abaqus `.inp`
- Abaqus 中间文件，例如 `.sim`、`.dat`、`.msg`、`.sta`、`.prt`、`.lck`
- Python `__pycache__`
- 超大型生成结果 `result_mesh.json`

这些文件可以通过安装依赖、重新构建 viewer、重新运行 Abaqus 脚本或刷新脚本生成。

## 构建

构建前端：

```powershell
Set-Location .\viewer
npm.cmd run build
```

构建产物写入 `viewer/dist/`。

## 常见问题

### 页面打不开

确认 dev server 已启动：

```powershell
Set-Location .\viewer
npm.cmd run dev
```

打开 Vite 输出的地址，通常是：

```text
http://127.0.0.1:4178/
```

### 结果没有更新

点击 viewer 中的刷新按钮，或直接刷新浏览器页面。`result_mesh.json` 是运行时加载的，页面可能仍显示上一份结果数据。

### 浏览器里点击运行后 Abaqus 没有启动

检查 `ABAQUS_COMMAND`：

```powershell
$env:ABAQUS_COMMAND
```

如果为空或路径错误，启动 viewer 前重新设置：

```powershell
$env:ABAQUS_COMMAND = "G:\SIMULIA\Commands\abaqus.bat"
npm.cmd run dev
```

### clone 后缺少某些结果文件

大型 ODB、INP 和生成结果文件不会提交到仓库。请运行对应 Abaqus 脚本或刷新脚本重新生成。
