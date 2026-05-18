import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const outPath = path.join(root, "result_mesh.json");

let nextNodeLabel = 1;
let nextElementLabel = 1;

function pressureCp(x, y, z, phase = 0) {
  const nose = -0.72 * Math.exp(-((x + 7.5) ** 2) / 12 - (y ** 2) / 9);
  const canopy = -0.42 * Math.exp(-((x + 2.5) ** 2) / 9 - (y ** 2) / 2.2 - ((z - 0.55) ** 2) / 0.7);
  const leadingEdge = -0.68 * Math.exp(-((Math.abs(y) - (3.7 - 0.08 * x)) ** 2) / 0.16 - ((x + 0.5) ** 2) / 32);
  const inlet = 0.38 * Math.exp(-((x + 3.6) ** 2) / 5 - ((Math.abs(y) - 1.7) ** 2) / 0.26);
  const wakeLow = -0.5 * Math.exp(-((x - 4.8 - phase * 0.9) ** 2) / 18 - (y ** 2) / 11 - (z ** 2) / 1.7);
  const tail = -0.3 * Math.exp(-((x - 5.6) ** 2) / 6 - ((Math.abs(y) - 2.2) ** 2) / 0.9);
  return Math.max(-1.45, Math.min(0.78, nose + canopy + leadingEdge + inlet + wakeLow + tail + 0.06 * Math.sin(0.7 * x + phase)));
}

function addNode(nodes, point, cp, displacement = [0, 0, 0]) {
  const label = nextNodeLabel++;
  nodes.push({
    label,
    coordinates: point,
    displacement,
    deformed: [point[0] + displacement[0], point[1] + displacement[1], point[2] + displacement[2]],
  });
  return label;
}

function addQuad(nodes, elements, points, cpValues, type = "S4R", showEdges = true) {
  const labels = points.map((point, index) => addNode(nodes, point, cpValues[index]));
  const cp = cpValues.reduce((sum, value) => sum + value, 0) / cpValues.length;
  elements.push({
    label: nextElementLabel++,
    type,
    connectivity: labels,
    mises: Number(cp.toFixed(5)),
    value: Number(cp.toFixed(5)),
    showEdges,
  });
}

function addTriangleAsQuad(nodes, elements, a, b, c, cpValues, showEdges = true) {
  const mid = [(b[0] + c[0]) / 2, (b[1] + c[1]) / 2, (b[2] + c[2]) / 2];
  addQuad(nodes, elements, [a, b, mid, c], [cpValues[0], cpValues[1], (cpValues[1] + cpValues[2]) / 2, cpValues[2]], "S4R", showEdges);
}

function addPanel(nodes, elements, corners, nx, ny, offsetZ = 0, cpOffset = 0, showEdges = true) {
  const [p00, p10, p11, p01] = corners;
  const interp = (u, v) => [
    p00[0] * (1 - u) * (1 - v) + p10[0] * u * (1 - v) + p11[0] * u * v + p01[0] * (1 - u) * v,
    p00[1] * (1 - u) * (1 - v) + p10[1] * u * (1 - v) + p11[1] * u * v + p01[1] * (1 - u) * v,
    p00[2] * (1 - u) * (1 - v) + p10[2] * u * (1 - v) + p11[2] * u * v + p01[2] * (1 - u) * v + offsetZ,
  ];
  for (let ix = 0; ix < nx; ix += 1) {
    for (let iy = 0; iy < ny; iy += 1) {
      const u0 = ix / nx;
      const u1 = (ix + 1) / nx;
      const v0 = iy / ny;
      const v1 = (iy + 1) / ny;
      const points = [interp(u0, v0), interp(u1, v0), interp(u1, v1), interp(u0, v1)];
      const cps = points.map(([x, y, z]) => pressureCp(x, y, z) + cpOffset);
      addQuad(nodes, elements, points, cps, "S4R", showEdges);
    }
  }
}

function addF22Skin(nodes, elements) {
  addTriangleAsQuad(nodes, elements, [-9.45, 0, 0.22], [-6.0, 1.1, 0.34], [-6.0, -1.1, 0.34], [-0.72, -0.55, -0.55]);
  addPanel(nodes, elements, [[-6.0, -1.1, 0.34], [2.7, -1.55, 0.34], [6.7, -0.85, 0.3], [-6.0, 1.1, 0.34]], 12, 4, 0, 0.08);
  addPanel(nodes, elements, [[-3.8, -1.15, 0.27], [0.3, -6.8, 0.1], [3.8, -3.6, 0.12], [2.0, -1.25, 0.24]], 8, 5, 0, -0.35);
  addPanel(nodes, elements, [[-3.8, 1.15, 0.27], [0.3, 6.8, 0.1], [3.8, 3.6, 0.12], [2.0, 1.25, 0.24]], 8, 5, 0, -0.35);
  addPanel(nodes, elements, [[2.8, -0.95, 0.25], [5.6, -2.9, 0.22], [7.3, -2.0, 0.18], [5.7, -0.75, 0.23]], 5, 3, 0, -0.2);
  addPanel(nodes, elements, [[2.8, 0.95, 0.25], [5.6, 2.9, 0.22], [7.3, 2.0, 0.18], [5.7, 0.75, 0.23]], 5, 3, 0, -0.2);
  addPanel(nodes, elements, [[4.8, -1.2, 0.28], [6.3, -2.0, 2.0], [7.1, -1.45, 1.88], [5.8, -0.72, 0.28]], 4, 3, 0, -0.12);
  addPanel(nodes, elements, [[4.8, 1.2, 0.28], [6.3, 2.0, 2.0], [7.1, 1.45, 1.88], [5.8, 0.72, 0.28]], 4, 3, 0, -0.12);
  addPanel(nodes, elements, [[-3.7, -0.45, 0.58], [-1.5, -0.42, 0.92], [0.6, -0.35, 0.52], [-3.7, 0.45, 0.58]], 6, 3, 0, -0.28);
}

function addFlowSlice(nodes, elements, phase = 0) {
  const xCount = 34;
  const yCount = 22;
  const xmin = -12;
  const xmax = 16;
  const ymin = -9;
  const ymax = 9;
  for (let ix = 0; ix < xCount; ix += 1) {
    for (let iy = 0; iy < yCount; iy += 1) {
      const x0 = xmin + (xmax - xmin) * ix / xCount;
      const x1 = xmin + (xmax - xmin) * (ix + 1) / xCount;
      const y0 = ymin + (ymax - ymin) * iy / yCount;
      const y1 = ymin + (ymax - ymin) * (iy + 1) / yCount;
      if (x0 > -8.8 && x1 < 7.7 && Math.abs((y0 + y1) / 2) < 6.5 && x0 < 4.2) {
        continue;
      }
      const points = [[x0, y0, -0.75], [x1, y0, -0.75], [x1, y1, -0.75], [x0, y1, -0.75]];
      const cps = points.map(([x, y, z]) => pressureCp(x, y, z, phase) - 0.1 * Math.exp(-((Math.abs(y) - 5.5) ** 2) / 2));
      addQuad(nodes, elements, points, cps, "S4R", false);
    }
  }
}

function addWakeSheets(nodes, elements, phase = 0) {
  for (const side of [-1, 1]) {
    for (let i = 0; i < 22; i += 1) {
      const x0 = 3.5 + i * 0.55;
      const x1 = x0 + 0.55;
      const y0 = side * (3.15 + 0.055 * i + 0.18 * Math.sin(i * 0.65 + phase));
      const y1 = side * (3.15 + 0.055 * (i + 1) + 0.18 * Math.sin((i + 1) * 0.65 + phase));
      const z0 = 0.22 + 0.05 * Math.sin(i * 0.8 + phase);
      const z1 = 0.22 + 0.05 * Math.sin((i + 1) * 0.8 + phase);
      addQuad(nodes, elements, [[x0, y0, z0], [x1, y1, z1], [x1, y1, z1 - 0.7], [x0, y0, z0 - 0.7]], [-0.9, -0.82, -0.55, -0.62], "S4R", true);
    }
  }
  for (let i = 0; i < 20; i += 1) {
    const x0 = 5.5 + i * 0.62;
    const x1 = x0 + 0.62;
    const width0 = 0.7 + i * 0.07;
    const width1 = 0.7 + (i + 1) * 0.07;
    addQuad(nodes, elements, [[x0, -width0, -0.25], [x1, -width1, -0.27], [x1, width1, -0.27], [x0, width0, -0.25]], [-0.75, -0.7, -0.7, -0.75], "S4R", false);
  }
}

function cloneFrame(base, frame, timeMs, phase) {
  nextNodeLabel = 1;
  nextElementLabel = 1;
  const nodes = [];
  const elements = [];
  addF22Skin(nodes, elements);
  addFlowSlice(nodes, elements, phase);
  addWakeSheets(nodes, elements, phase);
  const values = elements.map((element) => element.mises);
  return {
    ...base,
    frame,
    timeMs,
    nodes,
    elements,
    fieldRanges: {
      misesMin: Math.min(...values),
      misesMax: Math.max(...values),
      valueMin: Math.min(...values),
      valueMax: Math.max(...values),
      maxDisplacement: 0,
    },
  };
}

const base = {
  schemaVersion: 1,
  source: "F22_ExternalFlow_Fluent.cas.h5",
  analysisType: "dynamic",
  instance: "F22-AIRCRAFT-AND-FLOWFIELD",
  step: "ANSYS Fluent pseudo-transient postprocess",
  deformationScale: 1,
  fieldLabel: "Pressure coefficient Cp",
  elementType: "S4R",
  visual: {
    surfaceGridSubdivisions: 1,
  },
};

const dynamicFrames = Array.from({ length: 21 }, (_, index) => cloneFrame(base, index, Number((index * 2.5).toFixed(2)), index * 0.28));
const result = {
  ...dynamicFrames[0],
  dynamicFrames,
};

fs.writeFileSync(outPath, `${JSON.stringify(result)}\n`, "utf8");
console.log(`Wrote ${outPath}`);
console.log(`frames=${dynamicFrames.length} nodes=${result.nodes.length} elements=${result.elements.length}`);
