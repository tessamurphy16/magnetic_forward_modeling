/* All Pyodide work stays off the UI thread. */
const started = performance.now();
const runtime = new URL("./vendor/pyodide/", self.location.href);
const sources = [
  "__init__.py", "geometry.py", "geomagnetic.py", "igrf.py", "observables.py",
  "solver.py", "simulation.py", "data/IGRF14.shc",
];
let py;

async function copySource(url, filename) {
  const response = await fetch(new URL(url, self.location.href));
  if (!response.ok) throw new Error("Could not load " + url + " (HTTP " + response.status + ")");
  py.FS.writeFile(filename, new Uint8Array(await response.arrayBuffer()));
}

function errorText(error) {
  return String(error).trim().split("\n").at(-1);
}

async function initialize() {
  try {
    importScripts(new URL("pyodide.js", runtime).href);
    py = await loadPyodide({ indexURL: runtime.href });
    await py.loadPackage([
      "numpy", "pandas", "scipy",
      new URL("./vendor/ppigrf-2.1.0-py3-none-any.whl", self.location.href).href,
    ]);
    py.FS.mkdirTree("/app/magnetic_model/data");
    await Promise.all([
      copySource("./browser_model.py", "/app/browser_model.py"),
      ...sources.map(path => copySource("./magnetic_model/" + path, "/app/magnetic_model/" + path)),
    ]);
    py.runPython([
      "import sys, json",
      "sys.path.insert(0, '/app')",
      "from browser_model import field_result, simulation_result",
    ].join("\n"));
    postMessage({ type: "ready", initializationMs: performance.now() - started });
  } catch (error) {
    postMessage({ type: "fatal", error: errorText(error) });
  }
}

self.onmessage = ({ data: { type, id, inputs } }) => {
  const start = performance.now();
  py.globals.set("request_json", JSON.stringify(inputs));
  try {
    if (type === "field") {
      const metadata = JSON.parse(py.runPython("json.dumps(field_result(json.loads(request_json)))"));
      postMessage({ type, id, metadata });
      return;
    }
    const metadata = JSON.parse(py.runPython([
      "metadata, web_arrays = simulation_result(json.loads(request_json))",
      "json.dumps(metadata)",
    ].join("\n")));
    const payload = py.globals.get("web_arrays");
    const arrays = {};
    try {
      for (const key of ["x", "z", "profile", "vertical", "total"]) {
        const array = payload.get(key);
        try {
          const buffer = array.getBuffer("f64");
          try {
            // Copy out of WASM memory before releasing the view and transferring it.
            arrays[key] = buffer.data.slice();
          } finally {
            buffer.release();
          }
        } finally {
          array.destroy();
        }
      }
    } finally {
      payload.destroy();
    }
    postMessage({ type, id, metadata, arrays, simulationMs: performance.now() - start },
      Object.values(arrays).map(array => array.buffer));
  } catch (error) {
    postMessage({ type: "error", requestType: type, id, error: errorText(error) });
  } finally {
    for (const name of ["request_json", "metadata", "web_arrays"]) {
      if (py.globals.has(name)) py.globals.delete(name);
    }
  }
};

initialize();
