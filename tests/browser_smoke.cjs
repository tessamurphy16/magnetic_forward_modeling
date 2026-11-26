/* Maintainer-only Chromium test. See README for invocation. */
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const { chromium } = require("playwright-core");

const native = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", [
  "import json, numpy as np",
  "from magnetic_model import Grid, OreBody, simulate_at_location",
  "from magnetic_model.observables import total_field_anomaly_nt",
  "r = simulate_at_location(OreBody(80, 40, 40, .1), latitude_deg=39.7, longitude_deg=-105,",
  "                         azimuth_deg=0, grid=Grid(5, 320, 160, 160), observation_height_m=10)",
  "print(json.dumps(dict(profile=r.profile_total_anomaly_nt.tolist(),",
  "    vertical=r.anomaly_nt[..., 2].ravel().tolist(),",
  "    total=total_field_anomaly_nt(r.anomaly_nt, r.background_nt).ravel().tolist())))",
].join("\n")], { maxBuffer: 16 * 1024 * 1024 }));

const url = process.env.SITE_URL || "http://127.0.0.1:8893/magnetic_forward_modeling/";
const launch = {
  executablePath: process.env.CHROMIUM || "/usr/bin/chromium",
  args: ["--enable-unsafe-swiftshader"],
};
if (process.env.CHROMIUM_NO_SANDBOX === "1") launch.args.push("--no-sandbox");

async function checkPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  const errors = [];
  const failedResources = [];
  const external = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("response", response => {
    if (response.status() >= 400) failedResources.push(response.url() + " " + response.status());
  });
  page.on("request", request => {
    if (!request.url().startsWith(url) && !request.url().startsWith("blob:") &&
        !request.url().startsWith("data:")) external.push(request.url());
  });
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector("#total-field").textContent.includes("51,061.3"), null, { timeout: 120000 });
  assert.equal(await page.locator("#globe canvas").count(), 1);
  assert.equal(await page.locator("#empty-result").isVisible(), true);
  const timings = [];

  async function run() {
    await page.locator("#run").click();
    await page.waitForFunction(() => document.querySelector("#status").textContent === "Simulation complete.", null, { timeout: 120000 });
    return page.locator("#profile").evaluate(el => Array.from(el.data[0].y));
  }

  async function diagnostics() {
    return page.locator("#diagnostics").evaluate(el => Object.fromEntries(
      [...el.children].map(pair => [pair.querySelector("dt").textContent, pair.querySelector("dd").textContent])));
  }

  async function maxDifference(id, expected, flatten = false) {
    return page.locator("#" + id).evaluate((el, { expected, flatten }) => {
      const row = el.data[0][flatten ? "z" : "y"];
      const values = flatten ? row.flatMap(values => Array.from(values)) : Array.from(row);
      if (values.length !== expected.length) throw new Error("Unexpected plot length");
      return values.reduce((max, value, i) => Math.max(max, Math.abs(value - expected[i])), 0);
    }, { expected, flatten });
  }

  const defaultProfile = await run();
  timings.push(await diagnostics());
  assert.equal(timings[0].Grid, "320 × 320 cells");
  const profileDifference = await maxDifference("profile", native.profile);
  const verticalDifference = await maxDifference("heatmap", native.vertical, true);
  await page.locator("#heatmap-type").selectOption("total");
  await page.waitForFunction(() => document.querySelector("#heatmap").layout.title.text === "Exact total-field anomaly");
  const totalDifference = await maxDifference("heatmap", native.total, true);
  for (const value of [profileDifference, verticalDifference, totalDifference]) assert.ok(value < 1e-8);
  for (let i = 0; i < 2; i++) {
    await run();
    timings.push(await diagnostics());
  }

  if (process.env.SCREENSHOT) {
    await page.locator("#heatmap-type").selectOption("vertical");
    await page.waitForFunction(() => document.querySelector("#heatmap").layout.title.text === "Vertical magnetic anomaly");
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: process.env.SCREENSHOT, fullPage: true });
  }

  for (const [name, intensity] of [["Skagway", "55,593.0"], ["Perth", "58,459.4"],
    ["Singapore", "42,089.5"]]) {
    await page.locator("#preset").selectOption(name);
    await page.waitForFunction(intensity => document.querySelector("#total-field").textContent.includes(intensity), intensity);
  }
  const singaporeNorth = await run();
  assert.notDeepEqual(singaporeNorth, defaultProfile);
  await page.locator("#azimuth").fill("90");
  await page.waitForFunction(() => document.querySelector("#survey-x").textContent.includes("156.8"));
  const singaporeEast = await run();
  const peak = values => Math.max(...values.map(Math.abs));
  assert.ok(peak(singaporeEast) < peak(singaporeNorth) / 4);

  await page.locator("#susceptibility-slider").fill("0");
  assert.equal(await page.locator("#susceptibility").inputValue(), "0");
  assert.equal(peak(await run()), 0);
  await page.locator("#susceptibility").fill(".1");
  await page.locator("#width").fill("120");
  await page.locator("#thickness").fill("60");
  const larger = await run();
  assert.notDeepEqual(larger, singaporeEast);
  const outline = await page.locator("#heatmap").evaluate(el => el.layout.shapes[0]);
  assert.equal(outline.x1 - outline.x0, 120);
  assert.equal(outline.y1 - outline.y0, 60);

  await page.locator("#spacing").fill("20");
  await page.locator("#thickness").fill("15");
  await page.locator("#run").click();
  await page.waitForFunction(() => document.querySelector("#status").textContent.includes("three grid cells"));
  assert.deepEqual(await page.locator("#profile").evaluate(el => Array.from(el.data[0].y)), larger);
  await page.locator("#thickness").fill("60");
  await run();
  assert.equal((await diagnostics()).Grid, "80 × 80 cells");

  await page.locator("#reset").click();
  assert.equal(await page.locator("#preset").inputValue(), "Golden");
  assert.equal(await page.locator("#spacing").inputValue(), "5");
  await page.locator("#latitude").fill("-31.95");
  await page.locator("#longitude").fill("115.86");
  await page.waitForFunction(() => document.querySelector("#total-field").textContent.includes("58,459.4"));
  await page.locator("#preset").selectOption("Golden");
  const globe = page.locator("#globe canvas");
  await globe.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600); // Wait for the preset camera to finish moving.
  const box = await globe.boundingBox();
  const pointer = { x: box.x + box.width / 2 + 30, y: box.y + box.height / 2 + 12 };
  await page.mouse.move(pointer.x, pointer.y);
  await page.mouse.down();
  await page.mouse.move(pointer.x - 25, pointer.y + 10, { steps: 5 });
  await page.mouse.up();
  await page.mouse.wheel(0, -90);
  await page.mouse.click(pointer.x, pointer.y);
  await page.waitForFunction(() => document.querySelector("#preset").value === "" &&
    document.querySelector("#latitude").value !== "39.7");

  await page.setViewportSize({ width: 390, height: 800 });
  await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth);
  assert.deepEqual(errors, []);
  assert.deepEqual(failedResources, []);
  assert.deepEqual(external, []);
  console.log(JSON.stringify({ chromium: browser.version(), timings, profileDifference,
    verticalDifference, totalDifference, singaporeNorthPeak: peak(singaporeNorth),
    singaporeEastPeak: peak(singaporeEast) }, null, 2));
  await page.close();
}

async function checkRuntimeRecovery(browser) {
  const page = await browser.newPage();
  await page.route("**/solver-worker.js", route => route.abort());
  await page.goto(url);
  await page.waitForFunction(() => !document.querySelector("#retry").hidden, null, { timeout: 120000 });
  assert.equal(await page.locator("#run").isDisabled(), true);
  await page.unroute("**/solver-worker.js");
  await page.locator("#retry").click();
  await page.waitForFunction(() => document.querySelector("#total-field").textContent.includes("51,061.3"),
    null, { timeout: 120000 });
  assert.equal(await page.locator("#run").isDisabled(), false);
  await page.close();
}

async function main() {
  const browser = await chromium.launch(launch);
  try {
    await checkPage(browser);
    await checkRuntimeRecovery(browser);
    console.log("Chromium smoke test and runtime recovery passed.");
  } finally {
    await browser.close();
  }
}
main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
