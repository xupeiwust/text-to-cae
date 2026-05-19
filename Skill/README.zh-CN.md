# 有限元仿真 Skills

这个目录收集了公开 GitHub 仓库中对有限元仿真有用的第三方 agent skills。文件于 2026-05-19 导入，只保留具体 skill 目录，没有把完整上游仓库和历史一起带进来，便于审查和维护。

## 已包含内容

| Skill | 用途 | 上游来源 |
| --- | --- | --- |
| `fea-structural` | 通用结构有限元分析指导，覆盖 ANSYS Mechanical、Abaqus、NASTRAN、网格、边界条件、收敛和后处理。 | [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter/tree/main/library/specializations/domains/science/mechanical-engineering/skills/fea-structural) |
| `fenics-fem` | FEniCS/dolfinx 有限元 PDE 工作流，包含弱形式、gmsh 网格、Poisson/弹性示例和 ParaView 导出。 | [xjtulyc/awesome-rosetta-skills](https://github.com/xjtulyc/awesome-rosetta-skills/tree/main/skills/01-physics/fenics-fem) |
| `abaqus*` | Abaqus 工作流 skills，覆盖几何、材料、网格、载荷、边界、分析步、作业、输出、ODB 后处理、静力/动力/模态/热/接触/耦合/疲劳分析和优化。 | [majiayu000/claude-skill-registry](https://github.com/majiayu000/claude-skill-registry/tree/main/skills/data) |

## Abaqus skill 套件

当前 Abaqus 套件包含：

`abaqus`, `abaqus-amplitude`, `abaqus-bc`, `abaqus-contact-analysis`, `abaqus-coupled-analysis`, `abaqus-docs`, `abaqus-dynamic-analysis`, `abaqus-export`, `abaqus-fatigue-analysis`, `abaqus-field`, `abaqus-geometry`, `abaqus-interaction`, `abaqus-job`, `abaqus-load`, `abaqus-material`, `abaqus-mesh`, `abaqus-modal-analysis`, `abaqus-odb`, `abaqus-optimization`, `abaqus-output`, `abaqus-shape-optimization`, `abaqus-static-analysis`, `abaqus-step`, `abaqus-thermal-analysis`, `abaqus-topology-optimization`。

## 如何在 MCP/Agent 客户端中使用

这些是 skill 目录，不是 MCP server。它们本身不会启动 socket，也不会提供工具。实际使用时，应把它们作为 agent 指令模块，配合 Abaqus、ANSYS、FEniCS 或其他本地求解器/MCP 工具使用。

### Codex

把需要的 skill 复制到 Codex skills 目录，然后重新打开一个 Codex 会话：

```powershell
$src = "E:\Code\text-to-cae\Skill\fea-structural"
$dst = "$env:USERPROFILE\.codex\skills\fea-structural"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -Recurse -Force $src $dst
```

可使用这样的提示词：

```text
使用 fea-structural skill。帮我建立并检查这个模型的有限元分析流程；如果本机有 Abaqus/ANSYS MCP 工具，优先使用本机工具，并明确区分真实求解结果和建模建议。
```

### Claude Code

项目级安装：

```powershell
New-Item -ItemType Directory -Force -Path .claude\skills | Out-Null
Copy-Item -Recurse -Force "E:\Code\text-to-cae\Skill\abaqus-static-analysis" ".claude\skills\abaqus-static-analysis"
```

用户级安装：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force "E:\Code\text-to-cae\Skill\fenics-fem" "$env:USERPROFILE\.claude\skills\fenics-fem"
```

推荐提示词：

```text
使用 abaqus-static-analysis、abaqus-mesh、abaqus-job 和 abaqus-odb skills。帮我构建完整的 Abaqus 静力分析流程；如果 Abaqus MCP 或本地 Abaqus CLI 可用，就实际运行，并报告使用的文件和命令。
```

### Claude Desktop

Claude Desktop 主要通过 MCP server 配置工具能力。这些 skill 目录更适合作为参考上下文，或复制到支持 skills 的配套客户端中。如果要配合 Abaqus/ANSYS MCP 使用，可以附加或引用对应的 `SKILL.md`，并使用：

```text
按附加的 Abaqus 有限元 skill 指令执行。只有在需要真实求解操作时才调用已配置的 MCP 工具；如果只是建模建议，请明确说明不是求解结果。
```

### Cursor 和其他客户端

如果客户端支持 Claude-style 或项目级 skills，把需要的目录复制到该客户端文档指定的 skills 目录。如果不支持，就把相关 `SKILL.md` 作为项目上下文，并在提示词中明确要求遵循这些指令。

```text
使用 Skill/ 中的有限元 skills 作为项目指令。处理 Abaqus 时，根据任务分别使用 geometry/material/mesh/load/BC/step/job/ODB 等 skill。
```

## 许可证和来源

每个导入目录都包含 `UPSTREAM.md`，记录来源 URL 和导入日期。如果上游仓库提供了许可证文件，也已保存为 `UPSTREAM_LICENSE` 或 `UPSTREAM_LICENSE.md`。

这些是第三方公开 skills。二次分发、修改后发布或商业打包前，应再次检查上游仓库和许可证条款。
