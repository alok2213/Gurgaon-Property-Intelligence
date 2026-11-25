(function () {
  const sel = document.getElementById("sectorFilter");
  let current = null;

  function kpis(k) {
    const items = [
      [fmt.int(k.listings), "Listings"],
      [fmt.cr(k.median_price) + "<small>Cr</small>", "Median price"],
      [fmt.cr(k.avg_price) + "<small>Cr</small>", "Average price"],
      [fmt.int(k.avg_ppsf), "Avg ₹ per sq.ft."],
      [fmt.int(k.avg_area) + "<small>sq.ft.</small>", "Avg built-up area"],
      [fmt.int(k.flats) + " / " + fmt.int(k.houses), "Flats / houses"],
    ];
    document.getElementById("kpis").innerHTML = items
      .map((i) => `<div class="stat"><div class="v">${i[0]}</div><div class="l">${i[1]}</div></div>`).join("");
  }

  function mapChart(d) {
    const t = chartTheme();
    const pts = d.map;
    Plotly.react("mapChart", [{
      type: "scattermapbox", mode: "markers",
      lat: pts.map((p) => p.lat), lon: pts.map((p) => p.lon),
      text: pts.map((p) => `<b>${p.sector}</b><br>₹ ${fmt.int(p.ppsf)} / sq.ft.<br>Avg ${fmt.cr(p.price)} Cr · ${p.n} listings`),
      hoverinfo: "text",
      marker: {
        size: pts.map((p) => Math.max(8, Math.min(30, p.area / 110))),
        color: pts.map((p) => p.ppsf),
        colorscale: "YlGnBu", reversescale: true, opacity: 0.85,
        colorbar: { title: { text: "₹/sq.ft.", font: { color: t.ink2 } }, thickness: 12, len: 0.6, tickfont: { color: t.ink2 } },
      },
    }], {
      mapbox: { style: "open-street-map", center: { lat: 28.43, lon: 77.03 }, zoom: 10 },
      margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)",
      font: { color: t.ink2 },
    }, plotConfig);
  }

  function scatter(d) {
    const t = chartTheme();
    const groups = { "1": [], "2": [], "3": [], "4": [], "5+": [] };
    d.scatter.x.forEach((x, i) => {
      const b = d.scatter.bhk[i];
      groups[b >= 5 ? "5+" : String(b)].push(i);
    });
    const traces = Object.entries(groups).filter(([, v]) => v.length).map(([k, idx], n) => ({
      type: "scattergl", mode: "markers", name: k + " BHK",
      x: idx.map((i) => d.scatter.x[i]), y: idx.map((i) => d.scatter.y[i]),
      text: idx.map((i) => d.scatter.sector[i]),
      hovertemplate: "%{text}<br>%{x} sq.ft. · %{y} Cr<extra>" + k + " BHK</extra>",
      marker: { size: 6, opacity: 0.7, color: t.palette[n % t.palette.length] },
    }));
    Plotly.react("scatterChart", traces, baseLayout({
      xaxis: { title: "Built-up area (sq.ft.)", gridcolor: t.line },
      yaxis: { title: "Price (Cr)", gridcolor: t.line },
    }), plotConfig);
  }

  function box(d) {
    const t = chartTheme();
    const traces = Object.entries(d.box).map(([k, v], n) => ({
      type: "box", y: v, name: k + " BHK", boxpoints: false,
      marker: { color: t.palette[n % t.palette.length] },
    }));
    Plotly.react("boxChart", traces, baseLayout({
      showlegend: false, yaxis: { title: "Price (Cr)", gridcolor: t.line },
    }), plotConfig);
  }

  function dist(d) {
    const t = chartTheme();
    const mk = (name, key, color) => ({
      type: "histogram", name, x: d.dist[key], opacity: 0.65, marker: { color }, nbinsx: 30,
    });
    Plotly.react("distChart", [mk("Flats", "flat", t.primary), mk("Houses", "house", t.accent)],
      baseLayout({ barmode: "overlay", xaxis: { title: "Price (Cr)", gridcolor: t.line },
        yaxis: { title: "Listings", gridcolor: t.line } }), plotConfig);
  }

  function pie(d) {
    const t = chartTheme();
    Plotly.react("pieChart", [{
      type: "pie", hole: 0.55, labels: d.pie.labels, values: d.pie.values,
      marker: { colors: t.palette, line: { color: t.surface, width: 2 } },
      textinfo: "label+percent", sort: false,
    }], baseLayout({ margin: { l: 10, r: 10, t: 10, b: 10 }, showlegend: false }), plotConfig);
  }

  function top(d) {
    const t = chartTheme();
    const rows = d.top_sectors.slice().reverse();
    Plotly.react("topChart", [{
      type: "bar", orientation: "h",
      x: rows.map((r) => r.ppsf), y: rows.map((r) => r.sector),
      marker: { color: t.primary },
      customdata: rows.map((r) => [r.price, r.n]),
      hovertemplate: "%{y}<br>₹ %{x:,} / sq.ft.<br>Avg %{customdata[0]} Cr · %{customdata[1]} listings<extra></extra>",
    }], baseLayout({ margin: { l: 90, r: 16, t: 10, b: 40 },
      xaxis: { title: "₹ per sq.ft.", gridcolor: t.line } }), plotConfig);
  }

  async function cloud() {
    const data = await getJSON("/api/features");
    const el = document.getElementById("cloud");
    const max = data[0][1], min = data[data.length - 1][1];
    const t = chartTheme();
    const shuffled = data.slice().sort((a, b) => a[0].localeCompare(b[0]));
    el.innerHTML = shuffled.map(([name, n], i) => {
      const size = 13 + ((n - min) / (max - min || 1)) * 22;
      const color = t.palette[i % 3 === 0 ? 0 : i % 3 === 1 ? 1 : 2];
      const op = 0.55 + ((n - min) / (max - min || 1)) * 0.45;
      return `<span title="${n} listings" style="font-size:${size.toFixed(1)}px;color:${color};opacity:${op.toFixed(2)}">${name}</span>`;
    }).join("");
  }

  async function load(sector) {
    const d = await getJSON("/api/analytics?sector=" + encodeURIComponent(sector));
    current = d;
    document.getElementById("filterNote").textContent =
      d.sector === "overall" ? "" : "Charts and numbers below are for this sector only. The map and ranking always show all of Gurgaon.";
    kpis(d.kpi); scatter(d); box(d); dist(d); pie(d);
    if (!window.__mapDone) { mapChart(d); top(d); window.__mapDone = true; }
  }

  sel.addEventListener("change", () => load(sel.value).catch(console.error));
  document.addEventListener("themechange", () => {
    if (!current) return;
    mapChart(current); top(current); scatter(current); box(current); dist(current); pie(current); cloud();
  });
  load("overall").catch((e) => {
    document.getElementById("kpis").innerHTML = '<div class="stat"><div class="l">Could not load analytics data.</div></div>';
    console.error(e);
  });
  cloud().catch(console.error);
})();
