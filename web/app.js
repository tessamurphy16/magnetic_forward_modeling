import { plotHeatmap, plotProfile } from "./plots.js";

const $ = id => document.getElementById(id);
const sites = {
  Golden: [39.7, -105],
  Skagway: [59.45, -135.31],
  Singapore: [1.35, 103.82],
  Perth: [-31.95, 115.86],
};
const spacings = [5, 6.25, 8, 10, 12.5, 16, 20, 25];
const defaults = { azimuth: 0, susceptibility: .1, width: 80, thickness: 40,
  depth: 40, height: 10, spacing: 5 };
const parameters = [
  ["susceptibility", "Susceptibility (SI)", 0, 1, .01],
  ["width", "Ore-body width (m)", 15, 600, 5],
  ["thickness", "Ore-body thickness (m)", 15, 400, 5],
  ["depth", "Depth to top (m)", 0, 600, 5],
  ["height", "Observation height (m)", 0, 300, 5],
  ["spacing", "Grid spacing (m)", 5, 25, 1],
];
const fieldKeys = {
  "total-field": "total_nt", north: "north_nt", east: "east_nt", down: "down_nt",
  horizontal: "horizontal_nt", inclination: "inclination_deg", declination: "declination_deg",
};
let globe, worker, ready = false, busy = false, fieldTimer, fieldId = 0;
let startupTimer, initializationMs, activeRun, lastResult, lastField, revision = 0, runId = 0;

function status(message, tone = "") {
  $("status").textContent = message;
  $("status").className = "status " + tone;
}

function format(value, digits = 1) {
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function modelInputs() {
  return Object.fromEntries(["latitude", "longitude", ...Object.keys(defaults)]
    .map(id => [id, $(id).valueAsNumber]));
}

function setupControls() {
  for (const name of Object.keys(sites)) $("preset").add(new Option(name, name));
  for (const [id, label, min, max, step] of parameters) {
    const row = document.createElement("div");
    row.className = "parameter";
    row.innerHTML = '<label for="' + id + '">' + label + '</label>' +
      '<input type="range" id="' + id + '-slider" aria-label="' + label + ' slider">' +
      '<input type="number" id="' + id + '" min="' + min + '" max="' + max + '" step="any" required>';
    $("parameters").append(row);
    Object.assign($(id + "-slider"), id === "spacing" ?
      { min: 0, max: spacings.length - 1, step: 1 } : { min, max, step });
  }
  for (const id of Object.keys(defaults)) {
    const number = $(id);
    const slider = $(id + "-slider");
    slider.addEventListener("input", () => {
      const value = slider.valueAsNumber;
      number.value = id === "spacing" ? spacings[value] : value;
      edited(id === "azimuth");
    });
    number.addEventListener("input", () => {
      syncSlider(id);
      edited(id === "azimuth");
    });
  }
}

function syncSlider(id) {
  const number = $(id).valueAsNumber;
  if (!Number.isFinite(number)) return;
  $(id + "-slider").value = id === "spacing" ?
    spacings.reduce((nearest, value, index) =>
      Math.abs(value - number) < Math.abs(spacings[nearest] - number) ? index : nearest, 0) : number;
}

function validLocation() {
  return $("latitude").validity.valid && $("longitude").validity.valid;
}

function setLocation(lat, lng, name = "", center = false) {
  $("latitude").value = lat;
  $("longitude").value = lng;
  $("preset").value = name;
  updateMarker(center);
  edited(true);
}

function updateMarker(center) {
  if (!globe || !validLocation()) return;
  const lat = $("latitude").valueAsNumber;
  const lng = $("longitude").valueAsNumber;
  globe.pointsData([{ lat, lng }]);
  if (center) {
    globe.pointOfView({ lat, lng, altitude: 1.85 },
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 430);
  }
}

function initializeGlobe() {
  try {
    globe = new Globe($("globe"), { animateIn: false })
      .globeImageUrl(new URL("./vendor/earth.jpg", import.meta.url).href)
      .backgroundColor("#071d24")
      .atmosphereColor("#73cdd5").atmosphereAltitude(.12)
      .pointColor(() => "#ffbf55").pointRadius(.95).pointAltitude(.025)
      .pointsTransitionDuration(0)
      .onGlobeClick(({ lat, lng }) => setLocation(
        Number(lat.toFixed(5)), Number(lng.toFixed(5))));
    globe.controls().autoRotate = false;
    const resize = new ResizeObserver(() => {
      globe.width($("globe").clientWidth).height($("globe").clientHeight);
    });
    resize.observe($("globe"));
    const lat = $("latitude").valueAsNumber;
    const lng = $("longitude").valueAsNumber;
    globe.pointOfView({ lat, lng, altitude: 1.85 }, 0);
    updateMarker(false);
  } catch (error) {
    $("globe-note").textContent = "3D globe unavailable. Use the preset or coordinate inputs.";
    console.warn(error);
  }
}

function geometryMessage(inputs) {
  if (!Number.isFinite(inputs.spacing) || inputs.spacing < 5 || inputs.spacing > 25 ||
      Math.abs(Math.round(800 / inputs.spacing) * inputs.spacing - 800) > 1e-8) {
    return "Grid spacing must divide 800 m and be between 5 and 25 m.";
  }
  if (Math.min(inputs.width, inputs.thickness) < 3 * inputs.spacing) {
    return "Width and thickness must each span at least three grid cells.";
  }
  if (inputs.depth + inputs.thickness > 800 - inputs.spacing) {
    return "Leave at least one grid cell between the body and the bottom boundary.";
  }
  return "";
}

function refreshGridNote() {
  const inputs = modelInputs();
  const issue = geometryMessage(inputs);
  const count = 2 * Math.round(800 / inputs.spacing);
  $("grid-info").textContent = issue || (
    count + " × " + count + " cells. " + (inputs.spacing === 5 ?
      "5 m is the verified default for the reference body." :
      "Coarse grid. A 10 m preview missed the reference error targets.")
  );
}

function showField(metadata) {
  for (const [id, key] of Object.entries(fieldKeys)) {
    const value = metadata?.field[key];
    $(id).textContent = Number.isFinite(value) ?
      format(value, key.endsWith("_deg") ? 2 : 1) + (key.endsWith("_deg") ? "°" : " nT") :
      value === null ? "Undefined" : "—";
  }
  ["survey-x", "strike-s", "down-z"].forEach((id, index) => {
    $(id).textContent = metadata ? format(metadata.background[index]) + " nT" : "—";
  });
  drawCompass();
}

function drawCompass() {
  const canvas = $("compass");
  const ctx = canvas.getContext("2d");
  const [x, y, r] = [canvas.width / 2, canvas.height / 2, 78];
  const bearing = degrees => degrees * Math.PI / 180 - Math.PI / 2;
  const azimuth = $("azimuth").valueAsNumber;
  const declination = lastField?.field.declination_deg;
  const relative = Number.isFinite(declination) && Number.isFinite(azimuth) ?
    ((azimuth - declination + 540) % 360) - 180 : null;
  $("relative-heading").textContent = relative === null ? "—" :
    format(Math.abs(relative), 1) + "°" + (relative > 0 ? " CW" : relative < 0 ? " CCW" : "");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = "#f3f8f5";
  ctx.fill();
  ctx.strokeStyle = "#c7dbd1";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.font = "bold 18px system-ui";
  ctx.textAlign = "center";
  ctx.fillStyle = "#4f665e";
  for (const [letter, angle] of [["N", 0], ["E", 90], ["S", 180], ["W", 270]]) {
    ctx.fillText(letter, x + (r + 14) * Math.cos(bearing(angle)),
      y + (r + 14) * Math.sin(bearing(angle)) + 6);
  }
  if (relative !== null && relative !== 0) {
    ctx.beginPath();
    ctx.arc(x, y, 24, bearing(declination), bearing(declination + relative), relative < 0);
    ctx.strokeStyle = "#527067";
    ctx.lineWidth = 3;
    ctx.stroke();
  }
  function needle(angle, distance, color) {
    if (!Number.isFinite(angle)) return;
    const a = bearing(angle);
    const tipX = x + distance * Math.cos(a), tipY = y + distance * Math.sin(a);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(tipX, tipY);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(tipX, tipY);
    for (const offset of [-.48, .48]) {
      ctx.lineTo(tipX - 13 * Math.cos(a + offset), tipY - 13 * Math.sin(a + offset));
    }
    ctx.closePath();
    ctx.fill();
  }
  needle(0, 73, "#8a9d97");
  needle(declination, 61, "#b94e26");
  needle(azimuth, 48, "#11664f");
  canvas.setAttribute("aria-label", "Survey compass. Relative heading from magnetic north: " +
    $("relative-heading").textContent);
}

function queueField() {
  clearTimeout(fieldTimer);
  const id = ++fieldId;
  if (!ready || busy || !validLocation() || !$("azimuth").validity.valid) return;
  fieldTimer = setTimeout(() => worker.postMessage({ type: "field", id, inputs: modelInputs() }), 100);
}

function edited(fieldChanged = false) {
  revision++;
  refreshGridNote();
  if (fieldChanged) {
    lastField = null;
    showField(null);
    queueField();
  }
  if (!busy && ready) {
    if (!validLocation() || !$("azimuth").validity.valid) {
      status("Enter valid coordinates and azimuth.", "error");
    } else if (lastResult) {
      status("Inputs changed. Run again to update the plots.");
    } else {
      status("Ready. Run the simulation when the inputs are set.");
    }
  }
}

function diagnostics(result) {
  const { diagnostics: d, igrf_ms: igrfMs, shape } = result.metadata;
  const data = {
    "Grid": shape.join(" × ") + " cells",
    "Runtime initialization": format(initializationMs, 1) + " ms",
    "IGRF calculation": format(igrfMs, 1) + " ms",
    "PDE solution": format(d.pde_seconds * 1000, 1) + " ms",
    "Total simulation": format(result.simulationMs, 1) + " ms",
    "Relative L² residual": d.relative_residual_l2.toExponential(2),
    "Max flux divergence": d.max_flux_divergence_nt_per_m.toExponential(2) + " nT/m",
  };
  $("diagnostics").replaceChildren(...Object.entries(data).map(([title, value]) => {
    const pair = document.createElement("div");
    const term = document.createElement("dt");
    const definition = document.createElement("dd");
    term.textContent = title;
    definition.textContent = value;
    pair.append(term, definition);
    return pair;
  }));
}

async function finishRun(message) {
  const completed = activeRun;
  if (message.id !== completed?.id) return;
  try {
    if (message.type === "error") throw new Error(message.error);
    lastResult = { ...message, inputs: completed.inputs };
    const { latitude, longitude, azimuth, spacing } = completed.inputs;
    $("result-summary").textContent = "Last run · " + format(latitude, 3) + "°, " +
      format(longitude, 3) + "° · Azimuth " + azimuth + "° · " + spacing + " m grid";
    $("empty-result").hidden = true;
    $("plots").hidden = false;
    diagnostics(lastResult);
    await Promise.all([plotHeatmap(lastResult, $("heatmap-type").value), plotProfile(lastResult)]);
    if (completed.revision === revision) {
      lastField = message.metadata;
      showField(lastField);
    }
    status(completed.revision === revision ?
      "Simulation complete." : "Previous inputs finished. Run again to apply current inputs.");
  } catch (error) {
    status("Simulation failed. " + error.message, "error");
  } finally {
    activeRun = null;
    busy = false;
    $("run").disabled = !ready;
    $("results-title").closest("section").setAttribute("aria-busy", "false");
    if (completed.revision !== revision) queueField();
  }
}

function workerFailed(message) {
  clearTimeout(startupTimer);
  worker?.terminate();
  ready = busy = false;
  activeRun = null;
  $("run").disabled = true;
  $("retry").hidden = false;
  $("results-title").closest("section").setAttribute("aria-busy", "false");
  status("Python runtime unavailable. " + message, "error");
}

function startWorker() {
  worker?.terminate();
  $("retry").hidden = true;
  status("Loading Python runtime…", "busy");
  try {
    worker = new Worker(new URL("./solver-worker.js", import.meta.url));
  } catch (error) {
    workerFailed(error.message);
    return;
  }
  startupTimer = setTimeout(() => workerFailed("Initialization timed out."), 60000);
  worker.onerror = event => workerFailed(event.message || "Worker failed to load.");
  worker.onmessage = ({ data }) => {
    switch (data.type) {
      case "ready":
        clearTimeout(startupTimer);
        ready = true;
        initializationMs = data.initializationMs;
        $("run").disabled = false;
        status("Ready. Run the simulation when the inputs are set.");
        queueField();
        break;
      case "fatal": workerFailed(data.error); break;
      case "field":
        if (data.id === fieldId) {
          lastField = data.metadata;
          showField(lastField);
        }
        break;
      case "error":
        if (data.requestType !== "field") void finishRun(data);
        else if (data.id === fieldId) status("Field calculation failed. " + data.error, "error");
        break;
      case "run": void finishRun(data); break;
    }
  };
}

function run(event) {
  event.preventDefault();
  if (!ready || busy) return;
  const invalid = ["latitude", "longitude", ...Object.keys(defaults)].find(id => !$(id).validity.valid);
  if (invalid) {
    $(invalid).reportValidity();
    status("Correct the highlighted input.", "error");
    return;
  }
  const inputs = modelInputs();
  const issue = geometryMessage(inputs);
  if (issue) {
    status(issue, "error");
    return;
  }
  clearTimeout(fieldTimer);
  ++fieldId;
  activeRun = { id: ++runId, inputs, revision };
  busy = true;
  $("run").disabled = true;
  $("results-title").closest("section").setAttribute("aria-busy", "true");
  status("Solving magnetic potential…", "busy");
  worker.postMessage({ type: "run", id: activeRun.id, inputs });
}

function reset() {
  for (const [id, value] of Object.entries(defaults)) {
    $(id).value = value;
    syncSlider(id);
  }
  $("heatmap-type").value = "vertical";
  if (lastResult) void plotHeatmap(lastResult, "vertical");
  setLocation(...sites.Golden, "Golden", true);
  if (!ready && !busy && !$("retry").hidden) startWorker();
}

setupControls();
$("model-form").addEventListener("submit", run);
$("reset").addEventListener("click", reset);
$("retry").addEventListener("click", startWorker);
$("heatmap-type").addEventListener("change", () => {
  if (lastResult) void plotHeatmap(lastResult, $("heatmap-type").value);
});
$("preset").addEventListener("change", () => {
  const name = $("preset").value;
  if (name) setLocation(...sites[name], name, true);
});
for (const id of ["latitude", "longitude"]) {
  $(id).addEventListener("input", () => {
    $("preset").value = "";
    updateMarker(false);
    edited(true);
  });
  $(id).addEventListener("change", () => updateMarker(true));
}
reset();
initializeGlobe();
startWorker();
