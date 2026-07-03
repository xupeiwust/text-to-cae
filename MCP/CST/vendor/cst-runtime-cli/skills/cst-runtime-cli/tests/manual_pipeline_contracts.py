"""Pipeline contract RED/GREEN tests — ref_0 缓存优先，缺失自动仿真。

仓库区（本文件所在仓库）→ 测试逻辑 + 裸工程模板 ref_0.cst
工作区（CST_TEST_WORKSPACE env / CWD）→ .cst_runtime 部署 + 结果缓存

Usage:
  cd <workspace> && uv run pytest <repo>\\skills\\cst-runtime-cli\\tests\\test_pipeline_contracts.py -v
"""

import json
import math
import os
import shutil
import subprocess
from pathlib import Path

# --- 路径：仓库 vs 工作区分离 ---
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # cst-runtime-cli/
REFS_DIR = REPO_ROOT / "skills" / "cst-runtime-cli" / "tests" / "refs"
CST_WORKSPACE = Path(os.environ.get("CST_TEST_WORKSPACE", Path.cwd()))


def _cli(tool: str, args: dict, timeout: int = 300) -> dict:
    """在工作区运行 cst_runtime CLI 工具。"""
    af = CST_WORKSPACE / ".cst_runtime" / "tmp" / f"ctr_{tool}.json"
    af.parent.mkdir(parents=True, exist_ok=True)
    af.write_text(json.dumps(args, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(
        ["uv", "run", "python", "-m", "cst_runtime", tool, "--args-file", str(af)],
        capture_output=True, text=True, cwd=str(CST_WORKSPACE), timeout=timeout,
    )
    return json.loads(r.stdout) if r.stdout.strip() else {}


def _copy_ref0(dst_dir: Path) -> Path:
    """从仓库复制 ref_0.cst，从工作区复制结果缓存（如有）。
    
    结果缓存采用就近原则：仓库 REFS_DIR 下存在 cache 则优先，否则从工作区查找。
    """
    src = REFS_DIR / "ref_0" / "ref_0.cst"
    dst = dst_dir / "working.cst"
    shutil.copy2(str(src), str(dst))

    for cache_candidate in (REFS_DIR / "ref_0" / "ref_0", CST_WORKSPACE / "refs" / "ref_0" / "ref_0"):
        if cache_candidate.is_dir():
            shutil.copytree(
                str(cache_candidate), str(dst_dir / "working"),
                ignore=lambda d, f: [x for x in f if x.endswith(".lok")],
                dirs_exist_ok=True,
            )
            break
    return dst


def _ensure_simulated(pp: str, timeout: int = 900) -> dict:
    r = _cli("run-experiment", {"project_path": pp, "timeout_seconds": 600}, timeout=timeout)
    assert r["status"] == "success", f"simulation fallback failed: {r.get('message', r)}"
    return r


# ===========================================================================
# Phase 0 — pre-flight (0 sim)
# ===========================================================================

def test_health_check():
    r = _cli("health-check", {"auto_fix": False})
    assert r["status"] == "success"
    assert r.get("overall") == "pass"


# ===========================================================================
# T8 — Abs(E) as gain (0 sim, guard only)
# ===========================================================================

def test_t8_abs_e_rejected_realized_gain_allowed(tmp_path):
    pp = str(_copy_ref0(tmp_path))

    # RED
    r = _cli("export-farfield-grid", {
        "project_path": pp, "farfield_name": "farfield (f=10) [1]",
        "export_dir": str(tmp_path / "exports"), "quantity": "Abs(E)", "run_id": 1,
    })
    assert r["status"] == "error"
    assert r["error_type"] == "not_gain_evidence"
    assert "cst_raw" in r
    assert "next_action" in r

    # GREEN
    r = _cli("export-farfield-grid", {
        "project_path": pp, "farfield_name": "farfield (f=10) [1]",
        "export_dir": str(tmp_path / "exports"), "quantity": "Realized Gain", "run_id": 1,
    })
    if r["status"] == "error":
        assert r["error_type"] != "not_gain_evidence"


# ===========================================================================
# T13 — parameter readback lie (0 sim)
# ===========================================================================

def test_t13_change_parameter_warns(tmp_path):
    pp = str(_copy_ref0(tmp_path))

    r = _cli("cst-session-open", {"project_path": pp})
    assert r["status"] == "success"

    r = _cli("list-parameters", {"project_path": pp})
    p_name = list(r["parameters"].keys())[0]
    p_val = float(r["parameters"][p_name]["value"])

    r = _cli("change-parameter", {
        "project_path": pp, "name": p_name, "value": round(p_val * 1.05, 4),
    })
    assert r["status"] == "success"
    assert "warning" in r
    assert "next_action" in r
    assert "cst_raw" in r

    _cli("cst-session-close", {"project_path": pp, "save": False})


# ===========================================================================
# T2 — dirty project rejects simulation (0 sim for RED, GREEN is pipeline)
# ===========================================================================

def test_t2_change_blocks_simulation(tmp_path):
    """RED: 改参后 start-simulation-async 被 gateway 拒绝，含 cst_raw + next_action"""
    pp = str(_copy_ref0(tmp_path))
    r = _cli("inspect-project", {"project_path": pp})
    p_name = list(r["parameters"].keys())[0]
    p_val = float(r["parameters"][p_name]["value"])

    r = _cli("cst-session-open", {"project_path": pp})
    assert r["status"] == "success"
    r = _cli("change-parameter", {
        "project_path": pp, "name": p_name, "value": round(p_val * 1.05, 4),
    })
    assert r["status"] == "success"

    r = _cli("start-simulation-async", {"project_path": pp})
    assert r["status"] == "error"
    assert r["error_type"] == "params_not_rebuilt"
    assert "cst_raw" in r
    assert "next_action" in r
    _cli("cst-session-close", {"project_path": pp, "save": False})


# ===========================================================================
# Pipelines (0 sim for inspect/prepare)
# ===========================================================================

def test_pipeline_inspect_project(tmp_path):
    pp = str(_copy_ref0(tmp_path))
    r = _cli("inspect-project", {"project_path": pp})
    assert r["status"] == "success"
    assert r["parameters_count"] > 0
    assert r["entities_count"] > 0
    assert isinstance(r.get("farfield_monitors", []), list)


def test_pipeline_prepare_experiment(tmp_path):
    pp = str(_copy_ref0(tmp_path))
    r = _cli("inspect-project", {"project_path": pp})
    p0 = list(r["parameters"].keys())[0]
    v0 = float(r["parameters"][p0]["value"])

    r = _cli("prepare-experiment", {
        "project_path": pp, "param_name": p0, "param_value": round(v0 * 1.1, 4),
    })
    assert r["status"] == "success"


# ===========================================================================
# S11 产物验证 (0 sim, read cached results)
# ===========================================================================

def test_s11_export_structure(tmp_path):
    pp = str(_copy_ref0(tmp_path))
    r = _cli("get-1d-result", {
        "project_path": pp, "treepath": "1D Results\\S-Parameters\\S1,1",
        "run_id": 1, "export_path": str(tmp_path / "s11_read.json"),
    })
    if r.get("status") == "error":
        _ensure_simulated(pp)
        r = _cli("get-1d-result", {
            "project_path": pp, "treepath": "1D Results\\S-Parameters\\S1,1",
            "run_id": 1, "export_path": str(tmp_path / "s11_read.json"),
        })
    assert r["status"] == "success", f"s11 export failed: {r.get('message', r)}"
    assert r["point_count"] > 0

    data = json.loads((tmp_path / "s11_read.json").read_text(encoding="utf-8"))
    assert len(data["xdata"]) > 0
    assert isinstance(data["ydata"][0], dict)
    assert "real" in data["ydata"][0] and "imag" in data["ydata"][0]

    db = [20 * math.log10(max(math.hypot(d["real"], d["imag"]), 1e-30))
          for d in data["ydata"]]
    assert all(isinstance(v, float) for v in db)


def test_list_run_ids(tmp_path):
    pp = str(_copy_ref0(tmp_path))
    r = _cli("list-run-ids", {"project_path": pp})
    if r.get("status") == "success" and r.get("count", 0) <= 1 and 1 not in r.get("run_ids", []):
        _ensure_simulated(pp)
        r = _cli("list-run-ids", {"project_path": pp})
    assert r["status"] == "success"
    assert r["count"] > 0
    assert 1 in r.get("run_ids", [])


def test_get_parameter_combination(tmp_path):
    pp = str(_copy_ref0(tmp_path))
    r = _cli("get-parameter-combination", {"project_path": pp, "run_id": 1})
    if r.get("status") == "error":
        _ensure_simulated(pp)
        r = _cli("get-parameter-combination", {"project_path": pp, "run_id": 1})
    assert r["status"] == "success", f"get-parameter-combination failed: {r.get('message', r)}"
    assert isinstance(r.get("parameters"), dict)


# ===========================================================================
# 工作流验证 (1 sim)
# ===========================================================================

def test_workflow_prepare_sim_param_roundtrip(tmp_path):
    """prepare(CapA=192.5) → run-experiment → 验证参数已持久化"""
    pp = str(_copy_ref0(tmp_path))
    r = _cli("inspect-project", {"project_path": pp})
    cap_a = r["parameters"].get("CapA", {}).get("value")
    assert cap_a is not None, "CapA not found"

    new_a = round(cap_a * 1.1, 4)

    r = _cli("prepare-experiment", {
        "project_path": pp, "param_name": "CapA", "param_value": new_a,
    })
    assert r["status"] == "success", f"prepare: {r}"

    # run-experiment open → sim → export → close
    r = _cli("run-experiment", {"project_path": pp, "timeout_seconds": 600}, timeout=900)
    assert r["status"] == "success"
    assert r["exported_count"] > 0

    # verify CapA was saved to disk (not necessarily used by simulator if cached)
    r = _cli("inspect-project", {"project_path": pp})
    saved = r["parameters"].get("CapA", {}).get("value")
    assert abs(saved - new_a) < 0.01, (
        f"CapA={cap_a}→{new_a}, but after pipeline read back={saved}. "
        "prepare-experiment did not persist the change."
    )
