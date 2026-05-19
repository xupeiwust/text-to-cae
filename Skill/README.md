# Finite Element Simulation Skills

This directory collects public, third-party agent skills that are useful for finite element simulation workflows. The files were imported on 2026-05-19 from public GitHub repositories and kept as small, auditable skill folders rather than full upstream repositories.

## What is included

| Skill | Use case | Upstream |
| --- | --- | --- |
| `fea-structural` | General structural FEA guidance for ANSYS Mechanical, Abaqus, NASTRAN, meshing, boundary conditions, convergence, and post-processing. | [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter/tree/main/library/specializations/domains/science/mechanical-engineering/skills/fea-structural) |
| `fenics-fem` | FEniCS/dolfinx finite element PDE workflows: weak forms, gmsh meshes, Poisson/elasticity examples, and ParaView export. | [xjtulyc/awesome-rosetta-skills](https://github.com/xjtulyc/awesome-rosetta-skills/tree/main/skills/01-physics/fenics-fem) |
| `abaqus*` | Abaqus workflow skills covering geometry, materials, mesh, loads, BCs, steps, jobs, outputs, ODB post-processing, static/dynamic/modal/thermal/contact/coupled/fatigue analyses, and optimization. | [majiayu000/claude-skill-registry](https://github.com/majiayu000/claude-skill-registry/tree/main/skills/data) |

## Abaqus skill set

The Abaqus set currently includes:

`abaqus`, `abaqus-amplitude`, `abaqus-bc`, `abaqus-contact-analysis`, `abaqus-coupled-analysis`, `abaqus-docs`, `abaqus-dynamic-analysis`, `abaqus-export`, `abaqus-fatigue-analysis`, `abaqus-field`, `abaqus-geometry`, `abaqus-interaction`, `abaqus-job`, `abaqus-load`, `abaqus-material`, `abaqus-mesh`, `abaqus-modal-analysis`, `abaqus-odb`, `abaqus-optimization`, `abaqus-output`, `abaqus-shape-optimization`, `abaqus-static-analysis`, `abaqus-step`, `abaqus-thermal-analysis`, and `abaqus-topology-optimization`.

## How to use with MCP/agent clients

These are skill folders, not MCP servers. They do not open a socket or provide tools by themselves. Use them as agent instruction modules alongside an MCP server or local solver integration.

### Codex

Copy the skills you want into your Codex skills directory, then start a new Codex session:

```powershell
$src = "E:\Code\text-to-cae\Skill\fea-structural"
$dst = "$env:USERPROFILE\.codex\skills\fea-structural"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -Recurse -Force $src $dst
```

Use a prompt such as:

```text
Use the fea-structural skill. Help me set up and verify a finite element analysis workflow for this model. Prefer the local Abaqus/ANSYS MCP tools if available, and clearly separate solver-backed results from planning guidance.
```

### Claude Code

For a project-local install:

```powershell
New-Item -ItemType Directory -Force -Path .claude\skills | Out-Null
Copy-Item -Recurse -Force "E:\Code\text-to-cae\Skill\abaqus-static-analysis" ".claude\skills\abaqus-static-analysis"
```

For a user-level install:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force "E:\Code\text-to-cae\Skill\fenics-fem" "$env:USERPROFILE\.claude\skills\fenics-fem"
```

Suggested prompt:

```text
Use the abaqus-static-analysis, abaqus-mesh, abaqus-job, and abaqus-odb skills. Build a complete Abaqus static-analysis workflow, run it if the Abaqus MCP or local Abaqus CLI is available, and report the exact files and commands used.
```

### Claude Desktop

Claude Desktop mainly uses MCP server configuration. These skill folders are best used as reference context or copied into a skill-aware companion client. If using them with an Abaqus or ANSYS MCP server, attach or reference the relevant `SKILL.md` file and prompt:

```text
Follow the attached Abaqus finite element skill instructions. Use the configured MCP tools only for live solver operations, and state when an answer is only a modeling recommendation.
```

### Cursor and other clients

If the client supports Claude-style or project-local skills, copy selected folders into the client's documented skills directory. If it does not, add the relevant `SKILL.md` files as project context and explicitly ask the agent to follow them.

```text
Use the finite element skills in Skill/ as project instructions. For Abaqus work, route setup through geometry/material/mesh/load/BC/step/job/ODB skills as appropriate.
```

## Licensing and attribution

Each imported directory includes `UPSTREAM.md` with its source URL and import date. Where an upstream repository license file was available, it is included as `UPSTREAM_LICENSE` or `UPSTREAM_LICENSE.md`.

These are third-party public skills. Before redistributing modified versions or packaging them commercially, check the upstream repository and license terms.
