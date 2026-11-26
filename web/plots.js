const colors = [
  [0, "#214b88"], [0.25, "#70a9cf"], [0.5, "#fafaf6"],
  [0.75, "#e59670"], [1, "#9f3028"],
];
const config = { responsive: true, displaylogo: false, scrollZoom: false };
const axisStyle = { gridcolor: "#e0ebe5", zerolinecolor: "#8ca39b", automargin: true };
const base = {
  font: { family: "system-ui, sans-serif", size: 11, color: "#203830" },
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#f7faf8",
  margin: { l: 58, r: 58, b: 49, t: 39 },
};

function extent(values) {
  let max = 0;
  for (const value of values) max = Math.max(max, Math.abs(value));
  return max || 1;
}

function horizontalLine(y, color, dash) {
  return { type: "line", xref: "paper", x0: 0, x1: 1, y0: y, y1: y,
    line: { color, dash, width: 1.5 } };
}

export function plotHeatmap(result, quantity) {
  const { arrays, inputs, metadata } = result;
  const [nz, nx] = metadata.shape;
  const values = arrays[quantity];
  const rows = Array.from({ length: nz }, (_, row) => values.subarray(row * nx, (row + 1) * nx));
  const scale = extent(values);
  const [x0, x1, z0, z1] = metadata.diagnostics.body_bounds_m;
  const height = inputs.height;
  const horizontal = Math.min(800, Math.max(240, 2.5 * x1, z1 * 1.5, height * 2));
  const symbol = quantity === "vertical" ? "ΔBz" : "ΔF";
  const title = quantity === "vertical" ? "Vertical magnetic anomaly" : "Exact total-field anomaly";
  const traces = [{
    type: "heatmap", x: arrays.x, y: arrays.z, z: rows, colorscale: colors,
    zmin: -scale, zmax: scale, zmid: 0, zsmooth: false,
    colorbar: { title: { text: symbol + "<br>(nT)", side: "top" }, thickness: 12, outlinewidth: 0 },
    hovertemplate: "Distance %{x:.1f} m<br>Depth %{y:.1f} m<br>" + symbol +
      " %{z:.2f} nT<extra></extra>",
  }];
  const shapes = [
    { type: "rect", x0, x1, y0: z0, y1: z1, line: { color: "#0c231b", width: 2.2 } },
    horizontalLine(0, "#243932", "solid"),
  ];
  const annotations = [
    { xref: "paper", x: .015, y: 0, text: height ? "Ground surface" : "Ground / observation",
      showarrow: false, xanchor: "left", yanchor: "bottom", bgcolor: "#ffffffde" },
    { x: (x0 + x1) / 2, y: z1, text: "Ore body", showarrow: false,
      yanchor: "top", yshift: -3, bgcolor: "#ffffffde" },
  ];
  if (height > 0) {
    shapes.push(horizontalLine(-height, "#12684f", "dash"));
    annotations.push({ xref: "paper", x: .985, y: -height, text: "Observation line",
      showarrow: false, xanchor: "right", yanchor: "bottom", bgcolor: "#ffffffde" });
  }
  return Plotly.react("heatmap", traces, {
    ...base, title: { text: title, x: .04, font: { size: 14 } },
    xaxis: { ...axisStyle, title: "Distance along survey (m)", range: [-horizontal, horizontal] },
    yaxis: { ...axisStyle, title: "Depth (m, positive down)",
      range: [Math.min(800, Math.max(165, z1 + 65)), -Math.min(800, Math.max(70, height + 45))] },
    shapes, annotations,
  }, config);
}

export function plotProfile(result) {
  const { arrays, inputs } = result;
  return Plotly.react("profile", [{
    type: "scatter", mode: "lines", x: arrays.x, y: arrays.profile,
    line: { color: "#11735b", width: 2.4 },
    hovertemplate: "Distance %{x:.1f} m<br>ΔF %{y:.2f} nT<extra></extra>",
  }], {
    ...base, title: { text: "Exact total-field anomaly · " + inputs.height + " m above ground",
      x: .04, font: { size: 14 } },
    xaxis: { ...axisStyle, title: "Distance along survey (m)" },
    yaxis: { ...axisStyle, title: "ΔF (nT)" },
  }, config);
}
