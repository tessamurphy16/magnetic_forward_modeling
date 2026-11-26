"""Stage a self-contained static site. Only the maintainer needs Python."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import shutil
from urllib.request import urlopen


WEB = Path(__file__).resolve().parent
REPO = WEB.parent
PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full"
JSDELIVR = "https://cdn.jsdelivr.net/npm"
ASSETS = {
    "globe.gl.LICENSE.txt": (f"{JSDELIVR}/globe.gl@2.44.0/LICENSE",
                            "c633a0da18abe4208665d9faf574f38084bbe38ce5bf743e9ecc06e50b941b59"),
    "plotly.LICENSE.txt": (f"{JSDELIVR}/plotly.js-dist-min@2.35.2/LICENSE",
                          "67a26cf80f03ff388f26945dfc1f6caed1a0746ff43871190339b3aee49b94bb"),
    "plotly.min.js.LICENSE.txt": (f"{JSDELIVR}/plotly.js@2.35.2/dist/plotly.min.js.LICENSE.txt",
                                  "9144a55454d7944bd0695179ec85956de3d08a64c5227ffa2d45da186ec8445a"),
    "pyodide.LICENSE.txt": ("https://raw.githubusercontent.com/pyodide/pyodide/0.27.7/LICENSE",
                            "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5"),
    "globe.gl.js": (f"{JSDELIVR}/globe.gl@2.44.0/dist/globe.gl.min.js",
                    "3b5bfa647663072df455e4e993082f89fc8a06859d59de5bc13ebf534ac3b0b2"),
    "plotly.js": (f"{JSDELIVR}/plotly.js-dist-min@2.35.2/plotly.min.js",
                  "6d21266ce1bd7d9e5ab4e115989c70c20de0382fd973a8f26ab58619eba4d603"),
    "earth.jpg": (f"{JSDELIVR}/three-globe@2.44.0/example/img/earth-blue-marble.jpg",
                  "228deba2e4b600146bdcb6cfa359b8ead6aacc2b1c13550a29cd82824cfa1c01"),
    "ppigrf-2.1.0-py3-none-any.whl": (
        "https://files.pythonhosted.org/packages/c5/c8/7c561c46a39ac4a21c0cf2c104bf81f76ef2183fa69c0c2bb7c583d52f69/ppigrf-2.1.0-py3-none-any.whl",
        "50ff8968380a90c50cc6085122ac4673b0890939e37efa375f24d5bee7b1e1d6",
    ),
}
RUNTIME = {
    "pyodide.js": "b4cb23a53aba19c221659b9fb40a2f18281d685691dc06647fb0afd0681baf98",
    "pyodide.asm.js": "6b4c90de5b7172873f04f21884d0e9d2274e305fe32116558fe3e4fbe3618d51",
    "pyodide.asm.wasm": "a50dd1843f805a0b7c45b61037ee0d7b26dfe85efe0e18ef95a34ad24e401f5f",
    "python_stdlib.zip": "16611534726e5d8ac2bd8f926410b2dcb8d6f49aa24913463533b457a2115c16",
    "pyodide-lock.json": "9c45b916001a750f4102fc287494f3eab215909c7535c626a20db80fd6333e2c",
}


def download(destination, url, digest):
    if destination.is_file() and sha256(destination.read_bytes()).hexdigest() == digest:
        return
    with urlopen(url, timeout=90) as response:
        data = response.read()
    if sha256(data).hexdigest() != digest:
        raise ValueError(f"Checksum mismatch for {url}")
    destination.write_bytes(data)


def build(output):
    vendor = output / "vendor"
    runtime = vendor / "pyodide"
    runtime.mkdir(parents=True, exist_ok=True)
    jobs = [(vendor / name, url, digest) for name, (url, digest) in ASSETS.items()]
    jobs += [(runtime / name, f"{PYODIDE}/{name}", digest) for name, digest in RUNTIME.items()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for job in [pool.submit(download, *job) for job in jobs]:
            job.result()
        packages = json.loads((runtime / "pyodide-lock.json").read_text())["packages"]
        needed = set()
        pending = ["numpy", "scipy", "pandas"]
        while pending:
            name = pending.pop()
            if name not in needed:
                needed.add(name)
                pending.extend(packages[name]["depends"])
        jobs = []
        for name in sorted(needed):
            package = packages[name]
            file = package["file_name"]
            jobs.append(pool.submit(download, runtime / file, f"{PYODIDE}/{file}", package["sha256"]))
        for job in jobs:
            job.result()

    for name in ("index.html", "styles.css", "app.js", "plots.js", "solver-worker.js", "browser_model.py"):
        shutil.copy2(WEB / name, output / name)
    shutil.copytree(REPO / "magnetic_model", output / "magnetic_model",
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Dedicated output directory outside the source checkout")
    output = parser.parse_args().output.resolve()
    if output == REPO or REPO in output.parents or output in REPO.parents:
        parser.error("Choose a dedicated output directory separate from the checkout.")
    build(output)
    print(f"Static site ready at {output}")
