/* Shared helpers */
(function () {
  const root = document.documentElement;

  /* ---- theme ---- */
  const label = document.getElementById("themeLabel");
  function syncLabel() {
    if (label) label.textContent = root.getAttribute("data-theme") === "dark" ? "Light mode" : "Dark mode";
  }
  syncLabel();
  const toggle = document.getElementById("themeToggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      syncLabel();
      document.dispatchEvent(new CustomEvent("themechange"));
    });
  }

  /* ---- mobile nav ---- */
  const navBtn = document.getElementById("navToggle");
  if (navBtn) {
    navBtn.addEventListener("click", () => {
      const open = document.body.classList.toggle("nav-open");
      navBtn.setAttribute("aria-expanded", open);
    });
    document.getElementById("content").addEventListener("click", () => {
      document.body.classList.remove("nav-open");
      navBtn.setAttribute("aria-expanded", "false");
    });
  }

  /* ---- formatters ---- */
  window.fmt = {
    cr: (v) => (v == null ? "-" : Number(v).toFixed(2)),
    inr: (v) => (v == null ? "-" : Number(v).toLocaleString("en-IN")),
    int: (v) => Math.round(v).toLocaleString("en-IN"),
  };

  /* ---- Plotly theme helpers ---- */
  const css = (name) => getComputedStyle(root).getPropertyValue(name).trim();
  window.chartTheme = function () {
    return {
      ink: css("--ink"), ink2: css("--ink-2"), line: css("--line"),
      primary: css("--primary"), accent: css("--accent"), surface: css("--surface"),
      palette: [css("--primary"), css("--accent"), "#5b8def", "#2da38f", "#c9506b", "#8b6fd1"],
    };
  };
  window.baseLayout = function (extra) {
    const t = window.chartTheme();
    return Object.assign({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Public Sans, system-ui, sans-serif", color: t.ink2, size: 12 },
      margin: { l: 52, r: 16, t: 10, b: 44 },
      xaxis: { gridcolor: t.line, zerolinecolor: t.line, linecolor: t.line },
      yaxis: { gridcolor: t.line, zerolinecolor: t.line, linecolor: t.line },
      legend: { orientation: "h", y: -0.2 },
      hoverlabel: { font: { family: "Public Sans, system-ui, sans-serif" } },
    }, extra || {});
  };
  window.plotConfig = { displayModeBar: false, responsive: true };

  window.getJSON = async function (url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("Request failed (" + r.status + ")");
    return r.json();
  };
})();
