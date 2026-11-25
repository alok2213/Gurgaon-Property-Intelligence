(function () {
  const form = document.getElementById("predictForm");
  const errBox = document.getElementById("formErrors");
  const btn = document.getElementById("submitBtn");
  const empty = document.getElementById("emptyState");
  const body = document.getElementById("resultBody");

  /* ---- prefill from query string (used by the home page quick form) ---- */
  const q = new URLSearchParams(location.search);
  q.forEach((v, k) => {
    const els = form.querySelectorAll(`[name="${k}"]`);
    if (!els.length) return;
    if (els[0].type === "radio") els.forEach((e) => (e.checked = e.value === v));
    else if (els[0].type === "checkbox") els[0].checked = v === "1";
    else els[0].value = v;
  });

  function collect() {
    const d = {};
    new FormData(form).forEach((v, k) => (d[k] = v));
    d.servant_room = form.servant_room.checked ? "1" : "0";
    d.store_room = form.store_room.checked ? "1" : "0";
    return d;
  }

  function words(cr) {
    const lakh = cr * 100;
    return cr >= 1 ? `₹ ${fmt.inr(Math.round(cr * 1e7))}` : `₹ ${lakh.toFixed(0)} lakh`;
  }

  function render(r) {
    document.getElementById("rPrice").textContent = fmt.cr(r.price_cr);
    document.getElementById("rWords").textContent = words(r.price_cr);
    document.getElementById("rLow").textContent = fmt.cr(r.low_cr) + " Cr";
    document.getElementById("rHigh").textContent = fmt.cr(r.high_cr) + " Cr";
    document.getElementById("rPpsf").textContent = "₹ " + fmt.inr(r.price_per_sqft);
    document.getElementById("rMae").textContent = "± " + fmt.cr(r.mae_cr);

    // range bar: scale track to 0.6x .. 1.5x of the estimate so the band is readable
    const lo = r.price_cr * 0.6, hi = r.price_cr * 1.5;
    const pos = (v) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
    const fill = document.getElementById("rFill");
    fill.style.left = pos(r.low_cr) + "%";
    fill.style.width = Math.max(2, pos(r.high_cr) - pos(r.low_cr)) + "%";
    document.getElementById("rMark").style.left = pos(r.price_cr) + "%";

    const tb = document.getElementById("rComps");
    tb.innerHTML = "";
    if (!r.comparables.length) {
      tb.innerHTML = '<tr><td colspan="4" class="muted">No similar listings found.</td></tr>';
    }
    r.comparables.forEach((c) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${c.sector}<div class="small muted">${c.type} · ${c.age}</div></td>
        <td class="num">${c.bhk}</td><td class="r num">${fmt.int(c.area)}</td>
        <td class="r num"><b>${fmt.cr(c.price_cr)} Cr</b></td>`;
      tb.appendChild(tr);
    });
    empty.hidden = true;
    body.hidden = false;
  }

  function showErrors(list) {
    errBox.innerHTML = "<ul>" + list.map((e) => `<li>${e}</li>`).join("") + "</ul>";
    errBox.hidden = false;
  }

  async function submit(e) {
    if (e) e.preventDefault();
    errBox.hidden = true;
    btn.disabled = true;
    const original = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span> Estimating';
    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collect()),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showErrors(data.errors || ["Could not get an estimate. Please try again."]);
      } else {
        render(data);
        if (window.matchMedia("(max-width:1100px)").matches) {
          document.getElementById("resultPanel").scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    } catch (err) {
      showErrors(["Network problem. Check that the server is running and try again."]);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  form.addEventListener("submit", submit);
  form.addEventListener("reset", () => {
    errBox.hidden = true;
    body.hidden = true;
    empty.hidden = false;
  });

  // auto-run when arriving from the quick form with a sector chosen
  if (q.get("sector")) submit();
})();
