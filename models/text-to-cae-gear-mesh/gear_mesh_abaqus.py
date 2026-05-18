"""Abaqus/CAE source script for the Text-to-CAE gear meshing example.

Run with:
    abaqus cae noGUI=models/text-to-cae-gear-mesh/gear_mesh_abaqus.py
"""

from __future__ import print_function

import json
import math
import os
import sys

from abaqus import mdb
from abaqusConstants import *
import mesh
import regionToolset


def script_root():
    env_root = os.environ.get("TEXT_TO_CAE_ROOT", "")
    if env_root and os.path.exists(os.path.join(env_root, "cae_project.json")):
        return os.path.abspath(env_root)
    script_path = globals().get("__file__", "")
    if script_path:
        return os.path.dirname(os.path.abspath(script_path))
    argv_path = sys.argv[0] if sys.argv else ""
    if argv_path and argv_path.endswith(".py"):
        return os.path.dirname(os.path.abspath(argv_path))
    return os.getcwd()


ROOT = script_root()
MODEL_NAME = "TextToCAE_GearMeshDynamics_Model"
JOB_NAME = "TextToCAE_GearMeshDynamics"
MANIFEST_PATH = os.path.join(ROOT, "cae_project.json")
PARAMETERS_PATH = os.path.join(ROOT, "cae_parameters.json")
STEEL_DENSITY_TONNE_PER_MM3 = 7.85e-9
DEFAULT_PARAMETERS = {
    "module_mm": 2.5,
    "driver_teeth": 18,
    "driven_teeth": 30,
    "face_width_mm": 12.0,
    "driver_speed_rpm": 900.0,
    "transmitted_torque_nmm": 1800.0,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.08,
    "step_time_s": 0.04,
    "output_frames": 120,
    "seed_size_mm": 1.2,
    "youngs_modulus_mpa": 210000.0,
    "poissons_ratio": 0.3,
}


def bounded_float(parameters, name, lower, upper):
    try:
        value = float(parameters.get(name, DEFAULT_PARAMETERS[name]))
    except Exception:
        value = float(DEFAULT_PARAMETERS[name])
    return min(max(value, lower), upper)


def bounded_int(parameters, name, lower, upper):
    return int(round(bounded_float(parameters, name, lower, upper)))


def load_parameters():
    parameters = dict(DEFAULT_PARAMETERS)
    if os.path.exists(PARAMETERS_PATH):
        with open(PARAMETERS_PATH, "r") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            parameters.update(loaded)
    return {
        "module_mm": bounded_float(parameters, "module_mm", 0.8, 6.0),
        "driver_teeth": bounded_int(parameters, "driver_teeth", 10, 40),
        "driven_teeth": bounded_int(parameters, "driven_teeth", 10, 60),
        "face_width_mm": bounded_float(parameters, "face_width_mm", 4.0, 35.0),
        "driver_speed_rpm": bounded_float(parameters, "driver_speed_rpm", 30.0, 3600.0),
        "transmitted_torque_nmm": bounded_float(parameters, "transmitted_torque_nmm", 50.0, 20000.0),
        "pressure_angle_deg": bounded_float(parameters, "pressure_angle_deg", 14.5, 25.0),
        "backlash_mm": bounded_float(parameters, "backlash_mm", 0.0, 0.5),
        "step_time_s": bounded_float(parameters, "step_time_s", 0.005, 0.12),
        "output_frames": bounded_int(parameters, "output_frames", 40, 240),
        "seed_size_mm": bounded_float(parameters, "seed_size_mm", 0.4, 5.0),
        "youngs_modulus_mpa": bounded_float(parameters, "youngs_modulus_mpa", 1000.0, 500000.0),
        "poissons_ratio": bounded_float(parameters, "poissons_ratio", 0.01, 0.49),
    }


PARAMETERS = load_parameters()


def write_manifest(status, message):
    if not os.path.exists(MANIFEST_PATH):
        return
    with open(MANIFEST_PATH, "r") as handle:
        manifest = json.load(handle)
    module_value = PARAMETERS["module_mm"]
    driver_teeth = PARAMETERS["driver_teeth"]
    driven_teeth = PARAMETERS["driven_teeth"]
    center_distance = module_value * (driver_teeth + driven_teeth) * 0.5
    gear_ratio = float(driven_teeth) / float(driver_teeth)
    manifest["connection"] = {"status": "connected", "message": message}
    manifest["outputs"]["status"] = status
    manifest["inputs"]["geometry"] = {
        "module_mm": module_value,
        "driver_teeth": driver_teeth,
        "driven_teeth": driven_teeth,
        "face_width_mm": PARAMETERS["face_width_mm"],
        "center_distance_mm": center_distance,
    }
    manifest["inputs"]["material"] = {
        "name": "Steel",
        "youngs_modulus_mpa": PARAMETERS["youngs_modulus_mpa"],
        "poissons_ratio": PARAMETERS["poissons_ratio"],
        "density_tonne_per_mm3": STEEL_DENSITY_TONNE_PER_MM3,
    }
    manifest["inputs"]["loads"] = {
        "description": "Driver gear prescribed at {} rpm with {} N mm transmitted torque".format(
            PARAMETERS["driver_speed_rpm"],
            PARAMETERS["transmitted_torque_nmm"],
        ),
        "driver_speed_rpm": PARAMETERS["driver_speed_rpm"],
        "transmitted_torque_nmm": PARAMETERS["transmitted_torque_nmm"],
        "contact": "hard normal contact with backlash {} mm".format(PARAMETERS["backlash_mm"]),
        "load_direction": "rotation about global Z",
    }
    manifest["inputs"]["mesh"] = {
        "element_family": "S4R shell gear teeth",
        "seed_size_mm": PARAMETERS["seed_size_mm"],
    }
    manifest["outputs"]["metrics"] = [
        {"label": "Gear ratio", "value": round(gear_ratio, 4), "unit": "", "state": status},
        {"label": "Driver speed", "value": PARAMETERS["driver_speed_rpm"], "unit": "rpm", "state": status},
        {"label": "Simulation time", "value": PARAMETERS["step_time_s"] * 1000.0, "unit": "ms", "state": status},
    ]
    for item in manifest.get("workflow", []):
        if item.get("step") in ("Build Abaqus model", "Solve"):
            item["status"] = "complete" if status == "complete" else status
    with open(MANIFEST_PATH, "w") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def gear_points(tooth_count, module_value, backlash):
    pitch_radius = module_value * tooth_count * 0.5
    root_radius = max(pitch_radius - 1.25 * module_value, module_value * 2.0)
    outer_radius = pitch_radius + module_value
    points = []
    steps_per_tooth = 6
    half_backlash_angle = backlash / max(pitch_radius, 1.0) * 0.5
    for index in range(tooth_count * steps_per_tooth):
        tooth_phase = float(index % steps_per_tooth) / float(steps_per_tooth)
        angle = 2.0 * math.pi * float(index) / float(tooth_count * steps_per_tooth)
        if 0.18 <= tooth_phase <= 0.48:
            radius = outer_radius
            angle += half_backlash_angle
        elif 0.12 <= tooth_phase <= 0.58:
            radius = pitch_radius + module_value * 0.35
        else:
            radius = root_radius
        points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return points


def make_gear_part(model, name, tooth_count):
    module_value = PARAMETERS["module_mm"]
    face_width = PARAMETERS["face_width_mm"]
    points = gear_points(tooth_count, module_value, PARAMETERS["backlash_mm"])
    sketch = model.ConstrainedSketch(name=name + "_profile", sheetSize=module_value * tooth_count * 4.0)
    for index, point in enumerate(points):
        sketch.Line(point1=point, point2=points[(index + 1) % len(points)])
    part = model.Part(name=name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sketch, depth=face_width)
    del model.sketches[name + "_profile"]
    material_region = regionToolset.Region(cells=part.cells)
    part.SectionAssignment(region=material_region, sectionName="SteelSolid")
    part.seedPart(size=PARAMETERS["seed_size_mm"], deviationFactor=0.1, minSizeFactor=0.1)
    part.setElementType(regions=(part.cells,), elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=EXPLICIT),))
    part.generateMesh()
    return part


def build_model():
    if MODEL_NAME in mdb.models:
        del mdb.models[MODEL_NAME]
    if JOB_NAME in mdb.jobs:
        del mdb.jobs[JOB_NAME]

    model = mdb.Model(name=MODEL_NAME)
    material = model.Material(name="Steel")
    material.Density(table=((STEEL_DENSITY_TONNE_PER_MM3,),))
    material.Elastic(table=((PARAMETERS["youngs_modulus_mpa"], PARAMETERS["poissons_ratio"]),))
    model.HomogeneousSolidSection(name="SteelSolid", material="Steel", thickness=None)

    driver_part = make_gear_part(model, "DriverGear", PARAMETERS["driver_teeth"])
    driven_part = make_gear_part(model, "DrivenGear", PARAMETERS["driven_teeth"])
    module_value = PARAMETERS["module_mm"]
    driver_pitch = module_value * PARAMETERS["driver_teeth"] * 0.5
    driven_pitch = module_value * PARAMETERS["driven_teeth"] * 0.5
    center_distance = driver_pitch + driven_pitch

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    driver = assembly.Instance(name="DriverGear-1", part=driver_part, dependent=ON)
    driven = assembly.Instance(name="DrivenGear-1", part=driven_part, dependent=ON)
    assembly.translate(instanceList=("DrivenGear-1",), vector=(center_distance, 0.0, 0.0))
    assembly.Set(name="DRIVER", cells=driver.cells[:])
    assembly.Set(name="DRIVEN", cells=driven.cells[:])

    driver_rp = assembly.ReferencePoint(point=(0.0, 0.0, PARAMETERS["face_width_mm"] * 0.5))
    driven_rp = assembly.ReferencePoint(point=(center_distance, 0.0, PARAMETERS["face_width_mm"] * 0.5))
    assembly.Set(name="DRIVER_RP", referencePoints=(assembly.referencePoints[driver_rp.id],))
    assembly.Set(name="DRIVEN_RP", referencePoints=(assembly.referencePoints[driven_rp.id],))
    model.RigidBody(name="DriverRigidBody", refPointRegion=assembly.sets["DRIVER_RP"], bodyRegion=assembly.sets["DRIVER"])
    model.RigidBody(name="DrivenRigidBody", refPointRegion=assembly.sets["DRIVEN_RP"], bodyRegion=assembly.sets["DRIVEN"])

    model.ExplicitDynamicsStep(name="MeshRotation", previous="Initial", timePeriod=PARAMETERS["step_time_s"], improvedDtMethod=ON)
    model.FieldOutputRequest(name="GearFieldOutput", createStepName="MeshRotation", variables=("S", "U", "V"), numIntervals=PARAMETERS["output_frames"])
    model.ContactProperty("ToothContact")
    model.interactionProperties["ToothContact"].NormalBehavior(pressureOverclosure=HARD, allowSeparation=ON)
    model.interactionProperties["ToothContact"].TangentialBehavior(formulation=PENALTY, directionality=ISOTROPIC, table=((0.08,),))
    model.ContactExp(name="GeneralContact", createStepName="MeshRotation")
    model.interactions["GeneralContact"].includedPairs.setValuesInStep(stepName="MeshRotation", useAllstar=ON)
    model.interactions["GeneralContact"].contactPropertyAssignments.appendInStep(stepName="MeshRotation", assignments=((GLOBAL_SELF, "ToothContact"),))

    angular_speed = PARAMETERS["driver_speed_rpm"] * 2.0 * math.pi / 60.0
    model.EncastreBC(name="DriverAxis", createStepName="Initial", region=assembly.sets["DRIVER_RP"])
    model.EncastreBC(name="DrivenAxis", createStepName="Initial", region=assembly.sets["DRIVEN_RP"])
    model.boundaryConditions["DriverAxis"].setValuesInStep(stepName="MeshRotation", ur3=UNSET)
    model.boundaryConditions["DrivenAxis"].setValuesInStep(stepName="MeshRotation", ur3=UNSET)
    model.VelocityBC(name="DriverSpin", createStepName="MeshRotation", region=assembly.sets["DRIVER_RP"], vr3=angular_speed)
    model.Moment(name="DrivenTorque", createStepName="MeshRotation", region=assembly.sets["DRIVEN_RP"], cm3=-PARAMETERS["transmitted_torque_nmm"])

    mdb.Job(
        name=JOB_NAME,
        model=MODEL_NAME,
        description="Text-to-CAE explicit dynamic spur gear meshing",
        type=ANALYSIS,
        memory=90,
        memoryUnits=PERCENTAGE,
        explicitPrecision=SINGLE,
        nodalOutputPrecision=SINGLE,
        echoPrint=OFF,
        modelPrint=OFF,
        contactPrint=OFF,
        historyPrint=OFF,
        resultsFormat=ODB,
    )


def main():
    os.chdir(ROOT)
    write_manifest("building", "Abaqus is building the gear mesh model.")
    build_model()
    write_manifest("running", "Abaqus explicit gear mesh job submitted.")
    job = mdb.jobs[JOB_NAME]
    job.submit(consistencyChecking=OFF)
    job.waitForCompletion()
    write_manifest("complete", "Abaqus completed the gear mesh model. Use refresh_gear_result.mjs to regenerate the browser preview.")
    print("Text-to-CAE gear mesh complete: {}".format(MANIFEST_PATH))


if __name__ == "__main__":
    main()
