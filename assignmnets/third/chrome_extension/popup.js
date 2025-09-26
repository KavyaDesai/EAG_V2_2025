const BASE = "http://127.0.0.1:8000";

// -------- Tabs --------
const tabBtns = document.querySelectorAll(".tabs button");
const tabs = document.querySelectorAll(".tab");
tabBtns.forEach(btn => btn.addEventListener("click", () => {
  tabBtns.forEach(b => b.classList.remove("active"));
  tabs.forEach(s => s.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(btn.dataset.tab).classList.add("active");
}));

// -------- Helpers --------
function fmt(n, digits=2) { return (n === null || n === undefined || isNaN(n)) ? "" : Number(n).toFixed(digits); }

function renderTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return `<div class="muted">No rows.</div>`;
  const cols = ["symbol","start_usd","end_usd","pct_change","end_inr","error"];
  const head = `<tr>${cols.map(c=>`<th>${c}</th>`).join("")}</tr>`;
  const body = rows.map(r => {
    return `<tr>
      <td>${(r.resolved_from ? `${r.resolved_from} → ` : "") + (r.symbol ?? "")}</td>
      <td>${fmt(r.start_usd,2)}</td>
      <td>${fmt(r.end_usd,2)}</td>
      <td>${fmt(r.pct_change,2)}</td>
      <td>${fmt(r.end_inr,2)}</td>
      <td>${r.error ? `<span class="err">${r.error}</span>` : ""}</td>
    </tr>`;
  }).join("");
  return `<table>${head}${body}</table>`;
}

function setStatus(el, text, ok=false, isError=false) {
  el.classList.remove("ok","err","muted");
  if (isError) el.classList.add("err");
  else el.classList.add(ok ? "ok" : "muted");
  el.textContent = text;
}

function disable(el, on=true){ el.disabled = !!on; el.classList.toggle("muted", !!on); }

// -------- Prefill from GET /config on load --------
(async function initFromConfig(){
  try {
    const r = await fetch(`${BASE}/config`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    const cfg = await r.json();

    document.getElementById("cfg_symbols").value = (cfg.symbols || []).join(", ");
    document.getElementById("cfg_sendtime").value = cfg.send_time || "08:30";
    document.getElementById("cfg_sender").value = (cfg.email && cfg.email.sender) || "";
    document.getElementById("cfg_recipient").value = (cfg.email && cfg.email.recipient) || "";
  } catch (e) {
    const box = document.getElementById("status_box");
    setStatus(box, "Could not load config: " + e.message, false, true);
  }
})();

// -------- Config tab --------
document.getElementById("btn_save_cfg").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget, box = document.getElementById("status_box");
  disable(btn, true);
  const cfg = {
    symbols: (document.getElementById("cfg_symbols").value || "GC=F,SI=F").split(",").map(s=>s.trim()).filter(Boolean),
    send_time: document.getElementById("cfg_sendtime").value || "08:30",
    email: {
      sender: document.getElementById("cfg_sender").value || "",
      recipient: document.getElementById("cfg_recipient").value || ""
    }
  };
  try {
    const r = await fetch(`${BASE}/config`, {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(cfg)
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    await r.json().catch(()=>{});
    setStatus(box, "Saved configuration.", true);
  } catch (e) {
    setStatus(box, "Save failed: " + e.message, false, true);
  } finally {
    disable(btn, false);
  }
});

document.getElementById("btn_send_now").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget, box = document.getElementById("status_box");
  disable(btn, true);
  try {
    const r = await fetch(`${BASE}/run`, { method:"POST" });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    setStatus(box, "Triggered run. Refresh status in a few seconds…");
  } catch (e) {
    setStatus(box, "Run failed: " + e.message, false, true);
  } finally {
    disable(btn, false);
  }
});

document.getElementById("btn_refresh_status").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget, box = document.getElementById("status_box");
  disable(btn, true);
  try {
    const r = await fetch(`${BASE}/status`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    const j = await r.json();
    const txt = typeof j.last_run_preview === "string" ? j.last_run_preview
              : j.last_run_preview ? JSON.stringify(j.last_run_preview, null, 2)
              : "No analysis yet.";
    box.textContent = txt;
    box.classList.remove("muted","err"); // neutral display for server text
  } catch (e) {
    setStatus(box, "Status error: " + e.message, false, true);
  } finally {
    disable(btn, false);
  }
});

// -------- Movers tab --------
document.getElementById("btn_run_movers").addEventListener("click", async () => {
  const market = document.getElementById("mov_market").value;
  const period = document.getElementById("mov_period").value; // daily | 3mo | 6mo
  const top = document.getElementById("mov_top").value || 10;
  const out = document.getElementById("mov_out");
  out.textContent = "Loading…";
  try {
    const r = await fetch(`${BASE}/movers?market=${encodeURIComponent(market)}&period=${encodeURIComponent(period)}&top=${encodeURIComponent(top)}`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    const j = await r.json();

    const metals = renderTable(j.metals || []);
    const g = renderTable(j.gainers || []);
    const l = renderTable(j.losers || []);
    const commodities = renderTable(j.commodities || []);
    out.innerHTML = `<h4>Commodities (Gold, Silver, Crude, Copper)</h4>${commodities}
                    <h4>Top Gainers</h4>${g}
                    <h4>Top Losers</h4>${l}`;

    out.classList.remove("muted","err");
  } catch (e) {
    out.innerHTML = `<span class="err">Error: ${e.message}</span>`;
  }
});

// Initial status fetch on open
document.getElementById("btn_refresh_status").click();
