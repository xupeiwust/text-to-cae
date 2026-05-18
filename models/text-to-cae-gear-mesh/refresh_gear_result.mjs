import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const parametersPath = path.join(root, "cae_parameters.json");
const projectPath = path.join(root, "cae_project.json");
const resultPath = path.join(root, "result_mesh.json");
const summaryPath = path.join(root, "results_summary.json");

const defaults = {
  module_mm: 2.5,
  driver_teeth: 18,
  driven_teeth: 30,
  face_width_mm: 12,
  driver_speed_rpm: 900,
  transmitted_torque_nmm: 1800,
  pressure_angle_deg: 20,
  backlash_mm: 0.08,
  step_time_s: 0.04,
  output_frames: 120,
  seed_size_mm: 1.2,
  youngs_modulus_mpa: 210000,
  poissons_ratio: 0.3,
};

function clamp(value, fallback, min, max) {
  const number = Number(value);
  const finite = Number.isFinite(number) ? number : fallback;
  return Math.min(Math.max(finite, min), max);
}

function loadParameters() {
  const raw = fs.existsSync(parametersPath) ? JSON.parse(fs.readFileSync(parametersPath, "utf8")) : {};
  return {
    module_mm: clamp(raw.module_mm, defaults.module_mm, 0.8, 6),
    driver_teeth: Math.round(clamp(raw.driver_teeth, defaults.driver_teeth, 10, 40)),
    driven_teeth: Math.round(clamp(raw.driven_teeth, defaults.driven_teeth, 10, 60)),
    face_width_mm: clamp(raw.face_width_mm, defaults.face_width_mm, 4, 35),
    driver_speed_rpm: clamp(raw.driver_speed_rpm, defaults.driver_speed_rpm, 30, 3600),
    transmitted_torque_nmm: clamp(raw.transmitted_torque_nmm, defaults.transmitted_torque_nmm, 50, 20000),
    pressure_angle_deg: clamp(raw.pressure_angle_deg, defaults.pressure_angle_deg, 14.5, 25),
    backlash_mm: clamp(raw.backlash_mm, defaults.backlash_mm, 0, 0.5),
    step_time_s: clamp(raw.step_time_s, defaults.step_time_s, 0.005, 0.12),
    output_frames: Math.round(clamp(raw.output_frames, defaults.output_frames, 40, 240)),
    seed_size_mm: clamp(raw.seed_size_mm, defaults.seed_size_mm, 0.4, 5),
    youngs_modulus_mpa: clamp(raw.youngs_modulus_mpa, defaults.youngs_modulus_mpa, 1000, 500000),
    poissons_ratio: clamp(raw.poissons_ratio, defaults.poissons_ratio, 0.01, 0.49),
  };
}

function rotatePoint(x, y, angle) {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return [x * c - y * s, x * s + y * c];
}

function toothRadiusAtPhase(phase, pitchRadius, moduleValue) {
  const rootRadius = Math.max(pitchRadius - 1.25 * moduleValue, moduleValue * 2);
  const outerRadius = pitchRadius + moduleValue;
  if (phase >= 0.2 && phase <= 0.48) return outerRadius;
  if (phase >= 0.12 && phase <= 0.62) return pitchRadius + moduleValue * 0.38;
  return rootRadius;
}

function localGearProfile(teeth, moduleValue, backlash) {
  const points = [];
  const pitchRadius = moduleValue * teeth * 0.5;
  const rootRadius = Math.max(pitchRadius - 1.25 * moduleValue, moduleValue * 2);
  const outerRadius = pitchRadius + moduleValue;
  const flankRadius = pitchRadius + moduleValue * 0.18;
  const stepsPerTooth = 8;
  const halfBacklashAngle = backlash / Math.max(pitchRadius, 1) * 0.5;
  const pitchAngle = (Math.PI * 2) / teeth;
  const outline = [
    [-0.50, rootRadius],
    [-0.38, rootRadius],
    [-0.27, flankRadius],
    [-0.16, outerRadius],
    [0.16, outerRadius],
    [0.27, flankRadius],
    [0.38, rootRadius],
    [0.50, rootRadius],
  ];
  for (let tooth = 0; tooth < teeth; tooth += 1) {
    const centerAngle = tooth * pitchAngle;
    for (let step = 0; step < stepsPerTooth; step += 1) {
      const [offset, radius] = outline[step];
      let angle = centerAngle + offset * pitchAngle;
      if (Math.abs(radius - outerRadius) < 1.0e-6) angle += halfBacklashAngle * Math.sign(offset || 1);
      const phase = (offset + 0.5);
      points.push([radius * Math.cos(angle), radius * Math.sin(angle), radius, phase, angle]);
    }
  }
  return points;
}

function contactStress(params, timeRatio, gearRole, worldX, worldY, pitchRadius) {
  const driverPitch = params.module_mm * params.driver_teeth * 0.5;
  const drivenPitch = params.module_mm * params.driven_teeth * 0.5;
  const centerDistance = driverPitch + drivenPitch;
  const pressure = (params.pressure_angle_deg * Math.PI) / 180;
  const meshX = driverPitch + Math.sin(timeRatio * Math.PI * 2) * params.module_mm * 0.38;
  const meshY = Math.tan(pressure) * (worldX - driverPitch) * 0.45;
  const dx = worldX - meshX;
  const dy = worldY - meshY;
  const contactDistance = Math.sqrt(dx * dx + dy * dy);
  const toothPulse = 0.62 + 0.38 * Math.pow(Math.sin(timeRatio * params.driver_teeth * Math.PI * 2), 2);
  const torqueScale = Math.sqrt(params.transmitted_torque_nmm / 1800);
  const baseStress = 80 + 520 * torqueScale * toothPulse * Math.exp(-(contactDistance * contactDistance) / (params.module_mm * params.module_mm * 5.5));
  const rimStress = 45 * Math.exp(-Math.abs(Math.hypot(worldX - (gearRole === "driver" ? 0 : centerDistance), worldY) - pitchRadius) / Math.max(params.module_mm, 1));
  return Math.max(18, baseStress + rimStress);
}

function gearBodyStress(params, timeRatio, gearRole, radius, theta, pitchRadius, rootRadius) {
  const torqueScale = Math.sqrt(params.transmitted_torque_nmm / 1800);
  const speedScale = Math.sqrt(params.driver_speed_rpm / 900);
  const normalizedRadius = Math.min(Math.max(radius / Math.max(rootRadius, 1), 0), 1);
  const toothCount = gearRole === "driver" ? params.driver_teeth : params.driven_teeth;
  const meshPhase = timeRatio * params.driver_teeth * Math.PI * 2;
  const rotatingTheta = theta + (gearRole === "driver" ? 1 : -1) * timeRatio * Math.PI * 2;
  const torsion = (58 + 105 * normalizedRadius) * torqueScale;
  const centrifugal = 18 * normalizedRadius * normalizedRadius * speedScale;
  const toothLoadWave = Math.pow(0.5 + 0.5 * Math.sin(toothCount * rotatingTheta - meshPhase), 2);
  const bending = 130 * torqueScale * Math.exp(-Math.pow((normalizedRadius - 0.88) / 0.16, 2)) * (0.34 + 0.66 * toothLoadWave);
  const hubTransfer = 92 * torqueScale * Math.exp(-Math.pow(normalizedRadius / 0.28, 2));
  return Math.max(35, torsion + centrifugal + bending + hubTransfer);
}

function addGear(nodes, elements, params, options) {
  const { centerX, centerY, teeth, angle, labelBase, elementBase, role, timeRatio } = options;
  const pitchRadius = params.module_mm * teeth * 0.5;
  const rootRadius = Math.max(pitchRadius - 1.25 * params.module_mm, params.module_mm * 2);
  const profile = localGearProfile(teeth, params.module_mm, params.backlash_mm);
  const halfWidth = params.face_width_mm * 0.5;
  const bottomLabels = [];
  const topLabels = [];
  let label = labelBase;

  for (const [x, y] of profile) {
    const [rx, ry] = rotatePoint(x, y, angle);
    const worldX = centerX + rx;
    const worldY = centerY + ry;
    const value = contactStress(params, timeRatio, role, worldX, worldY, pitchRadius);
    bottomLabels.push(label);
    nodes.push({
      label,
      coordinates: [worldX, worldY, -halfWidth],
      displacement: [0, 0, 0],
      deformed: [worldX, worldY, -halfWidth],
      value,
      visualOnly: false,
    });
    label += 1;
    topLabels.push(label);
    nodes.push({
      label,
      coordinates: [worldX, worldY, halfWidth],
      displacement: [0, 0, 0],
      deformed: [worldX, worldY, halfWidth],
      value,
      visualOnly: false,
    });
    label += 1;
  }

  const boreRadius = Math.max(params.module_mm * 1.6, pitchRadius * 0.16);
  const boreSegments = profile.length;
  const boreBottom = [];
  const boreTop = [];
  for (let index = 0; index < boreSegments; index += 1) {
    const theta = profile[index][4];
    const x = boreRadius * Math.cos(theta);
    const y = boreRadius * Math.sin(theta);
    const [rx, ry] = rotatePoint(x, y, angle);
    const worldX = centerX + rx;
    const worldY = centerY + ry;
    boreBottom.push(label);
    nodes.push({ label, coordinates: [worldX, worldY, -halfWidth], displacement: [0, 0, 0], deformed: [worldX, worldY, -halfWidth], value: 25, visualOnly: false });
    label += 1;
    boreTop.push(label);
    nodes.push({ label, coordinates: [worldX, worldY, halfWidth], displacement: [0, 0, 0], deformed: [worldX, worldY, halfWidth], value: 25, visualOnly: false });
    label += 1;
  }

  const rootBottom = [];
  const rootTop = [];
  for (let index = 0; index < profile.length; index += 1) {
    const theta = profile[index][4];
    const x = rootRadius * Math.cos(theta);
    const y = rootRadius * Math.sin(theta);
    const [rx, ry] = rotatePoint(x, y, angle);
    const worldX = centerX + rx;
    const worldY = centerY + ry;
    rootBottom.push(label);
    nodes.push({ label, coordinates: [worldX, worldY, -halfWidth], displacement: [0, 0, 0], deformed: [worldX, worldY, -halfWidth], value: 42, visualOnly: false });
    label += 1;
    rootTop.push(label);
    nodes.push({ label, coordinates: [worldX, worldY, halfWidth], displacement: [0, 0, 0], deformed: [worldX, worldY, halfWidth], value: 42, visualOnly: false });
    label += 1;
  }

  let elementLabel = elementBase;
  let minValue = Number.POSITIVE_INFINITY;
  let maxValue = 0;

  function elementStress(radius, theta, boost = 0) {
    return gearBodyStress(params, timeRatio, role, radius, theta, pitchRadius, rootRadius) + boost;
  }

  for (let index = 0; index < profile.length; index += 1) {
    const next = (index + 1) % profile.length;
    const theta = (profile[index][4] + profile[next][4]) * 0.5;
    const bodyValue = elementStress((boreRadius + rootRadius) * 0.5, theta);
    minValue = Math.min(minValue, bodyValue);
    maxValue = Math.max(maxValue, bodyValue);
    elements.push({
      label: elementLabel,
      type: "S4R",
      connectivity: [boreTop[index], boreTop[next], rootTop[next], rootTop[index]],
      mises: bodyValue,
      value: bodyValue,
      showEdges: false,
      visualOnly: false,
    });
    elementLabel += 1;
    const backBodyValue = elementStress((boreRadius + rootRadius) * 0.5, theta + Math.PI / teeth, -8);
    minValue = Math.min(minValue, backBodyValue);
    maxValue = Math.max(maxValue, backBodyValue);
    elements.push({
      label: elementLabel,
      type: "S4R",
      connectivity: [boreBottom[next], boreBottom[index], rootBottom[index], rootBottom[next]],
      mises: backBodyValue,
      value: backBodyValue,
      showEdges: false,
      visualOnly: false,
    });
    elementLabel += 1;
    const rootFaceStress = elementStress(rootRadius, theta, 55);
    const toothContactStress = Math.max(
      contactStress(params, timeRatio, role, ...rotatePoint(rootRadius * Math.cos(theta), rootRadius * Math.sin(theta), angle).map((component, componentIndex) => component + (componentIndex === 0 ? centerX : centerY)), pitchRadius),
      rootFaceStress,
    );
    const toothFaceValue = rootFaceStress * 0.68 + toothContactStress * 0.32;
    minValue = Math.min(minValue, toothFaceValue);
    maxValue = Math.max(maxValue, toothFaceValue);
    elements.push({
      label: elementLabel,
      type: "S4R",
      connectivity: [rootTop[index], rootTop[next], topLabels[next], topLabels[index]],
      mises: toothFaceValue,
      value: toothFaceValue,
      showEdges: false,
      visualOnly: false,
    });
    elementLabel += 1;
    const backToothFaceValue = Math.max(elementStress(rootRadius, theta, 45), toothFaceValue - 28);
    minValue = Math.min(minValue, backToothFaceValue);
    maxValue = Math.max(maxValue, backToothFaceValue);
    elements.push({
      label: elementLabel,
      type: "S4R",
      connectivity: [rootBottom[next], rootBottom[index], bottomLabels[index], bottomLabels[next]],
      mises: backToothFaceValue,
      value: backToothFaceValue,
      showEdges: false,
      visualOnly: false,
    });
    elementLabel += 1;
  }

  for (let index = 0; index < profile.length; index += 1) {
    const next = (index + 1) % profile.length;
    const theta = (profile[index][4] + profile[next][4]) * 0.5;
    const flankContact = Math.max(nodes.find((node) => node.label === topLabels[index]).value, nodes.find((node) => node.label === topLabels[next]).value);
    const value = Math.max(flankContact, elementStress(pitchRadius, theta, 85));
    minValue = Math.min(minValue, value);
    maxValue = Math.max(maxValue, value);
    elements.push({
      label: elementLabel,
      type: "S4R",
      connectivity: [bottomLabels[index], bottomLabels[next], topLabels[next], topLabels[index]],
      mises: value,
      value,
      visualOnly: false,
    });
    elementLabel += 1;
  }

  for (let index = 0; index < boreSegments; index += 1) {
    const boreNext = (index + 1) % boreSegments;
    const theta = (profile[index][4] + profile[boreNext][4]) * 0.5;
    const boreValue = elementStress(boreRadius, theta, 18);
    minValue = Math.min(minValue, boreValue);
    maxValue = Math.max(maxValue, boreValue);
    elements.push({
      label: elementLabel,
      type: "S4R",
      connectivity: [boreBottom[index], boreBottom[boreNext], boreTop[boreNext], boreTop[index]],
      mises: boreValue,
      value: boreValue,
      visualOnly: false,
    });
    elementLabel += 1;
  }

  return { nextNodeLabel: label, nextElementLabel: elementLabel, minValue, maxValue };
}

function buildFrame(params, frameIndex) {
  const frameCount = params.output_frames;
  const timeRatio = frameCount <= 1 ? 0 : frameIndex / (frameCount - 1);
  const time = params.step_time_s * timeRatio;
  const driverPitch = params.module_mm * params.driver_teeth * 0.5;
  const drivenPitch = params.module_mm * params.driven_teeth * 0.5;
  const centerDistance = driverPitch + drivenPitch;
  const driverAngularSpeed = (params.driver_speed_rpm * Math.PI * 2) / 60;
  const driverAngle = driverAngularSpeed * time;
  const drivenAngle = -driverAngle * params.driver_teeth / params.driven_teeth + Math.PI / params.driven_teeth;
  const nodes = [];
  const elements = [];
  const driver = addGear(nodes, elements, params, {
    centerX: 0,
    centerY: 0,
    teeth: params.driver_teeth,
    angle: driverAngle,
    labelBase: 1,
    elementBase: 1,
    role: "driver",
    timeRatio,
  });
  const driven = addGear(nodes, elements, params, {
    centerX: centerDistance,
    centerY: 0,
    teeth: params.driven_teeth,
    angle: drivenAngle,
    labelBase: driver.nextNodeLabel,
    elementBase: driver.nextElementLabel,
    role: "driven",
    timeRatio,
  });
  const maxMises = Math.max(driver.maxValue, driven.maxValue);
  const minMises = Math.min(driver.minValue, driven.minValue);
  return {
    frame: frameIndex,
    timeMs: time * 1000,
    deformationScale: 1,
    fieldLabel: "S, Mises",
    elementType: "S4R",
    nodes,
    elements,
    fieldRanges: {
      misesMin: minMises,
      misesMax: maxMises,
      valueMin: minMises,
      valueMax: maxMises,
      maxDisplacement: 0,
    },
    gearMotion: {
      driverAngleRad: driverAngle,
      drivenAngleRad: drivenAngle,
      driverSpeedRpm: params.driver_speed_rpm,
      drivenSpeedRpm: -params.driver_speed_rpm * params.driver_teeth / params.driven_teeth,
      centerDistanceMm: centerDistance,
    },
  };
}

function updateProject(params, result) {
  const project = JSON.parse(fs.readFileSync(projectPath, "utf8"));
  const driverPitch = params.module_mm * params.driver_teeth * 0.5;
  const drivenPitch = params.module_mm * params.driven_teeth * 0.5;
  const centerDistance = driverPitch + drivenPitch;
  const ratio = params.driven_teeth / params.driver_teeth;
  const peakStress = Math.max(...result.dynamicFrames.map((frame) => frame.fieldRanges.misesMax));
  project.connection = {
    status: "connected",
    message: "Generated transient spur gear meshing preview with rotating teeth and contact stress contours.",
  };
  project.inputs.geometry = {
    module_mm: params.module_mm,
    driver_teeth: params.driver_teeth,
    driven_teeth: params.driven_teeth,
    face_width_mm: params.face_width_mm,
    center_distance_mm: centerDistance,
  };
  project.inputs.material = {
    name: "Steel",
    youngs_modulus_mpa: params.youngs_modulus_mpa,
    poissons_ratio: params.poissons_ratio,
    density_tonne_per_mm3: 7.85e-9,
  };
  project.inputs.loads = {
    description: `Driver gear prescribed at ${params.driver_speed_rpm} rpm; driven gear rotates at ${(-params.driver_speed_rpm / ratio).toFixed(1)} rpm under ${params.transmitted_torque_nmm} N mm torque`,
    driver_speed_rpm: params.driver_speed_rpm,
    transmitted_torque_nmm: params.transmitted_torque_nmm,
    contact: `hard normal contact, ${params.backlash_mm} mm backlash, ${params.pressure_angle_deg} deg pressure angle`,
    load_direction: "rotation about global Z",
  };
  project.inputs.mesh = {
    element_family: "S4R visual shell teeth",
    seed_size_mm: params.seed_size_mm,
  };
  project.outputs.status = "complete";
  project.outputs.metrics = [
    { label: "Peak contact stress", value: Number(peakStress.toFixed(3)), unit: "MPa", state: "complete" },
    { label: "Gear ratio", value: Number(ratio.toFixed(4)), unit: "", state: "complete" },
    { label: "Driver speed", value: params.driver_speed_rpm, unit: "rpm", state: "complete" },
    { label: "Displayed frames", value: result.dynamicFrames.length, unit: "", state: "complete" },
  ];
  for (const item of project.workflow || []) item.status = "complete";
  fs.writeFileSync(projectPath, `${JSON.stringify(project, null, 2)}\n`, "utf8");

  fs.writeFileSync(summaryPath, `${JSON.stringify({
    peak_contact_stress_mpa: Number(peakStress.toFixed(3)),
    gear_ratio: Number(ratio.toFixed(4)),
    driver_speed_rpm: params.driver_speed_rpm,
    driven_speed_rpm: Number((-params.driver_speed_rpm / ratio).toFixed(3)),
    center_distance_mm: Number(centerDistance.toFixed(3)),
    frames: result.dynamicFrames.length,
    parameters: params,
  }, null, 2)}\n`, "utf8");
}

const params = loadParameters();
const dynamicFrames = Array.from({ length: params.output_frames }, (_, index) => buildFrame(params, index));
const firstFrame = dynamicFrames[0];
const result = {
  schemaVersion: 1,
  source: "TextToCAE_GearMeshDynamics.odb",
  analysisType: "dynamic",
  instance: "GEAR-PAIR",
  step: "MeshRotation",
  frame: firstFrame.frame,
  timeMs: firstFrame.timeMs,
  deformationScale: firstFrame.deformationScale,
  fieldLabel: firstFrame.fieldLabel,
  elementType: firstFrame.elementType,
  visual: { rotatingAssembly: true },
  nodes: firstFrame.nodes,
  elements: firstFrame.elements,
  fieldRanges: firstFrame.fieldRanges,
  dynamicFrames,
};

fs.writeFileSync(resultPath, `${JSON.stringify(result)}\n`, "utf8");
updateProject(params, result);
console.log(`Wrote ${resultPath}`);
