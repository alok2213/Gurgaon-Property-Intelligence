(function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  /* ---- tabs ---- */
  function showTab(which) {
    const loc = which === "loc";
    $("tab-loc").setAttribute("aria-selected", loc);
    $("tab-sim").setAttribute("aria-selected", !loc);
    $("pane-loc").hidden = !loc;
    $("pane-sim").hidden = loc;
  }
  $("tab-loc").onclick = () => showTab("loc");
  $("tab-sim").onclick = () => showTab("sim");

  function err(el, msg) { el.textContent = msg; el.hidden = !msg; }

  function card(a, extra) {
    const tags = a.configs.map((c) => `<span class="chip hl">${esc(c)}</span>`).join("") +
      a.facilities.map((f) => `<span class="chip">${esc(f)}</span>`).join("");
    return `<article class="item">
      <div>
        <h4>${esc(a.name)}</h4>
        <p class="sub">${esc(a.area || a.sub)}${a.price_hint ? " · " + esc(a.price_hint) : ""}</p>
        <div class="tags">${tags}</div>
      </div>
      <div class="side">${extra}
        <button class="btn ghost small" data-similar="${esc(a.name)}">Find similar</button>
      </div></article>`;
  }

  /* ---- search by location ---- */
  $("radius").addEventListener("input", (e) => ($("radiusVal").textContent = e.target.value));
  async function searchLoc() {
    const loc = $("locInput").value.trim();
    err($("locErr"), "");
    if (!loc) return err($("locErr"), "Enter a landmark or place to search around.");
    $("locBtn").disabled = true;
    try {
      const d = await getJSON(`/api/recommend/nearby?location=${encodeURIComponent(loc)}&radius=${$("radius").value}`);
      const list = d.results;
      $("locPanel").hidden = false;
      $("locTitle").textContent = list.length
        ? `${list.length} apartment${list.length > 1 ? "s" : ""} within ${$("radius").value} km of ${loc}`
        : `No apartments within ${$("radius").value} km of ${loc}`;
      $("locResults").innerHTML = list.length
        ? list.map((a) => card(a, `<b>${a.distance_txt}</b>away`)).join("")
        : '<p class="muted" style="padding:14px 0">Try a larger radius or choose a suggestion from the list.</p>';
    } catch (e) { err($("locErr"), "Could not search right now. Please try again."); }
    finally { $("locBtn").disabled = false; }
  }
  $("locBtn").onclick = searchLoc;
  $("locInput").addEventListener("keydown", (e) => e.key === "Enter" && searchLoc());

  /* ---- similar apartments ---- */
  async function similar(name) {
    err($("simErr"), "");
    if (!name) return err($("simErr"), "Choose an apartment from the list.");
    $("simBtn").disabled = true;
    try {
      const res = await fetch(`/api/recommend/similar?name=${encodeURIComponent(name)}`);
      const d = await res.json();
      if (!res.ok || !d.ok) { $("simOut").hidden = true; return err($("simErr"), "We couldn't find that apartment. Pick one from the suggestions."); }
      const x = d.detail;
      $("detailPanel").innerHTML = `
        <div class="detail-head">
          <div><h3>${esc(x.name)}</h3><p class="muted">${esc(x.sub)}</p></div>
          <a class="btn ghost small" href="${esc(x.link)}" target="_blank" rel="noopener noreferrer">View listing</a>
        </div>
        <div class="grid two" style="margin-top:12px">
          <div>
            <h4 class="subhead" style="margin-top:0">Configurations</h4>
            <div class="table-wrap"><table><thead><tr><th>Type</th><th>Area</th><th class="r">Price</th></tr></thead><tbody>
              ${x.prices.map((p) => `<tr><td>${esc(p.config)}</td><td class="num">${esc(p.area)}</td><td class="r num">${esc(p.price)}</td></tr>`).join("") ||
                '<tr><td colspan="3" class="muted">Pricing not available.</td></tr>'}
            </tbody></table></div>
          </div>
          <div>
            <h4 class="subhead" style="margin-top:0">Top facilities</h4>
            <div class="tags" style="display:flex;gap:6px;flex-wrap:wrap">${x.facilities.map((f) => `<span class="chip">${esc(f)}</span>`).join("")}</div>
            <h4 class="subhead">Nearby</h4>
            <div class="table-wrap"><table><tbody>${x.nearby.map((n) => `<tr><td>${esc(n.place)}</td><td class="r num">${esc(n.dist)}</td></tr>`).join("")}</tbody></table></div>
          </div>
        </div>`;
      $("simResults").innerHTML = d.similar.map((a) => card(a,
        `<b>${a.score}%</b>similar<span class="inline-bar score"><span style="width:${a.score}%"></span></span>`)).join("");
      $("simOut").hidden = false;
      $("simOut").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) { err($("simErr"), "Something went wrong. Please try again."); }
    finally { $("simBtn").disabled = false; }
  }
  $("simBtn").onclick = () => similar($("aptInput").value.trim());
  $("aptInput").addEventListener("keydown", (e) => e.key === "Enter" && similar($("aptInput").value.trim()));

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-similar]");
    if (!b) return;
    $("aptInput").value = b.dataset.similar;
    showTab("sim");
    similar(b.dataset.similar);
  });
})();
