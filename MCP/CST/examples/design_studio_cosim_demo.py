from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cst_automation import CSTSessionManager
from cst_schematic import CSTSchematicVBA, SchematicEndpoint


def build_demo_vba() -> str:
    snippets = [
        CSTSchematicVBA.external_port("1", x=42000, y=50000, label="Input"),
        CSTSchematicVBA.external_port("2", x=61000, y=50000, label="Output", rotation=180),
        CSTSchematicVBA.inductor("L_match_0p35nH", 0.35, unit="nH", x=46000, y=50000),
        CSTSchematicVBA.capacitor("C_gap_0p07pF", 0.07, unit="pF", x=50000, y=50000),
        CSTSchematicVBA.diode("D_nonlinear", x=53500, y=50000),
        CSTSchematicVBA.inductor("L_bias_39nH", 39, unit="nH", x=57000, y=50000),
        CSTSchematicVBA.resistor("R_load_100ohm", 100, unit="Ohm", x=61000, y=53500),
        CSTSchematicVBA.ground("GND_load", x=61000, y=56500),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("Externalport", "1", 0), SchematicEndpoint("BLOCK", "L_match_0p35nH", 0)],
            net_name="net_in",
        ),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("BLOCK", "L_match_0p35nH", 1), SchematicEndpoint("BLOCK", "C_gap_0p07pF", 0)],
            net_name="net_lc",
        ),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("BLOCK", "C_gap_0p07pF", 1), SchematicEndpoint("BLOCK", "D_nonlinear", 0)],
            net_name="net_cd",
        ),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("BLOCK", "D_nonlinear", 1), SchematicEndpoint("BLOCK", "L_bias_39nH", 0)],
            net_name="net_dl",
        ),
        CSTSchematicVBA.connect(
            [
                SchematicEndpoint("BLOCK", "L_bias_39nH", 1),
                SchematicEndpoint("Externalport", "2", 0),
                SchematicEndpoint("BLOCK", "R_load_100ohm", 0),
            ],
            net_name="net_out",
        ),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("BLOCK", "R_load_100ohm", 1), SchematicEndpoint("BLOCK", "GND_load", 0)],
            net_name="net_gnd",
        ),
        CSTSchematicVBA.frequency_sweep(task_name="SPara1", fmin=1, fmax=10, samples=91, unit="GHz"),
    ]
    return "\n\n".join(snippets)


def export_se_il(manager: CSTSessionManager, project_path: Path, output_csv: Path) -> dict[str, object]:
    s21 = manager.read_1d_result(
        "Tasks\\SPara1\\S-Parameters\\S2,1",
        cst_file=str(project_path),
        module="schematic",
        max_points=2000,
    )
    rows = []
    for index, row in enumerate(s21["data"]):
        value = row[1]
        if isinstance(value, list):
            magnitude = math.hypot(float(value[0]), float(value[1]))
        else:
            magnitude = abs(complex(value))
        rows.append(
            {
                "index": index,
                "frequency": row[0],
                "s21_magnitude": magnitude,
                "se_il_db": -20.0 * math.log10(max(magnitude, 1e-300)),
            }
        )
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["index", "frequency", "s21_magnitude", "se_il_db"])
        writer.writeheader()
        writer.writerows(rows)
    return {
        "source_tree_path": "Tasks\\SPara1\\S-Parameters\\S2,1",
        "points": len(rows),
        "output_csv": str(output_csv),
        "first_rows": rows[:3],
    }


def build_touchstone_nport_demo(manager: CSTSessionManager, run_dir: Path, source_s2p: Path) -> dict[str, object]:
    project_path = run_dir / f"touchstone_nport_block_demo_{int(time.time())}.cst"
    manager.new_schematic_project(path=str(project_path))
    snippets = [
        CSTSchematicVBA.external_port("1", x=42000, y=50000, label="Input"),
        CSTSchematicVBA.external_port("2", x=61000, y=50000, label="Output", rotation=180),
        CSTSchematicVBA.block("NPORT_touchstone", "touchstone", file_path=str(source_s2p), x=51500, y=50000, cache_files=True),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("Externalport", "1", 0), SchematicEndpoint("BLOCK", "NPORT_touchstone", 0)],
            net_name="nport_in",
        ),
        CSTSchematicVBA.connect(
            [SchematicEndpoint("Externalport", "2", 0), SchematicEndpoint("BLOCK", "NPORT_touchstone", 1)],
            net_name="nport_out",
        ),
        CSTSchematicVBA.frequency_sweep(task_name="SPara1", fmin=1, fmax=10, samples=91, unit="GHz"),
    ]
    manager.schematic_execute_vba("\n\n".join(snippets))
    manager.save_project(str(project_path))
    run_result = manager.schematic_run_simulation(task_name="SPara1")
    manager.save_project(str(project_path))
    result_items = manager.list_results(cst_file=str(project_path), module="schematic")
    export_base = run_dir / f"{project_path.stem}_sparameters"
    touchstone_export = manager.schematic_export_touchstone("Tasks\\SPara1\\S-Parameters", str(export_base), 50)
    return {
        "project_path": str(project_path),
        "source_s2p": str(source_s2p),
        "run_result": run_result,
        "result_items": result_items,
        "touchstone_export": touchstone_export,
        "touchstone_files": [str(path) for path in run_dir.glob(f"{project_path.stem}_sparameters.s*p")],
    }


def main() -> None:
    run_dir = ROOT / "examples" / "design_studio_cosim_demo_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    project_path = run_dir / f"fss_rlc_diode_schematic_demo_{int(time.time())}.cst"
    log: dict[str, object] = {"project_path": str(project_path), "steps": []}

    manager = CSTSessionManager()
    manager.connect(launch_if_needed=False)
    manager.new_schematic_project(path=str(project_path))
    log["steps"].append({"create_project": str(project_path)})

    manager.schematic_execute_vba(build_demo_vba())
    manager.save_project(str(project_path))
    log["steps"].append({"build_schematic": True})

    log["run_result"] = manager.schematic_run_simulation(task_name="SPara1")
    manager.save_project(str(project_path))
    log["steps"].append({"run_circuit": True})

    log["result_items"] = manager.list_results(cst_file=str(project_path), module="schematic")

    export_base = run_dir / f"{project_path.stem}_schematic_sparameters"
    log["touchstone_export"] = manager.schematic_export_touchstone("Tasks\\SPara1\\S-Parameters", str(export_base), 50)
    log["touchstone_files"] = [str(path) for path in run_dir.glob(f"{project_path.stem}_schematic_sparameters.s*p")]

    csv_path = run_dir / f"{project_path.stem}_se_il.csv"
    log["se_il_export"] = export_se_il(manager, project_path, csv_path)
    if log["touchstone_files"]:
        log["nport_block_demo"] = build_touchstone_nport_demo(manager, run_dir, Path(log["touchstone_files"][0]))
    log["messages_tail"] = manager.get_project_info().get("messages_tail", [])

    log_path = run_dir / f"{project_path.stem}_demo_log.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "project_path": str(project_path), "log_path": str(log_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
