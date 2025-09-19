// popup.js - analytics + config UI for Market Analyser

// tab switching
document.getElementById('tab-config').addEventListener('click', () => {
  document.getElementById('tab-config').classList.add('active');
  document.getElementById('tab-analytics').classList.remove('active');
  document.getElementById('section-config').classList.add('active');
  document.getElementById('section-analytics').classList.remove('active');
});
document.getElementById('tab-analytics').addEventListener('click', () => {
  document.getElementById('tab-analytics').classList.add('active');
  document.getElementById('tab-config').classList.remove('active');
  document.getElementById('section-analytics').classList.add('active');
  document.getElementById('section-config').classList.remove('active');
});

// helper
function showStatus(msg, color='green') {
  const s = document.getElementById('status');
  s.style.color = color;
  s.textContent = msg;
}

async function postJSON(path, payload) {
  const resp = await fetch('http://localhost:8000' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return resp.json();
}

async function getJSON(path) {
  const resp = await fetch('http://localhost:8000' + path);
  return resp.json();
}

// save config
document.getElementById('save').addEventListener('click', async () => {
  const tickers = document.getElementById('tickers').value.split(',').map(s => s.trim()).filter(Boolean);
  const send_time = document.getElementById('send_time').value || '08:30';
  const sender = document.getElementById('sender').value;
  const recipient = document.getElementById('recipient').value;

  const payload = { symbols: tickers, send_time, email: { smtp_server: 'smtp.gmail.com', smtp_port: 587, sender, recipient } };

  try {
    await postJSON('/config', payload);
    showStatus('Saved to backend ✓', 'green');
  } catch (e) {
    showStatus('Failed to save: ' + e.toString(), 'red');
  }
});

// send now
document.getElementById('sendnow').addEventListener('click', async () => {
  try {
    await fetch('http://localhost:8000/run', { method: 'POST' });
    showStatus('Triggered send-now ✓', 'green');
  } catch (e) {
    showStatus('Failed to trigger: ' + e.toString(), 'red');
  }
});

// refresh LLM status (last run)
document.getElementById('refresh_status').addEventListener('click', async () => {
  const wrap = document.getElementById('analytics_status');
  wrap.textContent = 'Loading...';
  try {
    const data = await getJSON('/status');
    wrap.textContent = data.last_run_preview || 'No last run available.';
  } catch (e) {
    wrap.textContent = 'Backend not running.';
  }
});

// analytics: run for tickers & period (daily,3mo,6mo)
document.getElementById('run_analytics').addEventListener('click', async () => {
  let raw = document.getElementById('ana_tickers').value || '';
  let tickers = raw.split(',').map(s => s.trim()).filter(Boolean);
  if (tickers.length === 0) {
    tickers = ['GC=F','SI=F'];
  }
  const period = document.getElementById('period').value || 'daily';
  const wrap = document.getElementById('analytics_status');
  wrap.textContent = 'Running analytics...';

  try {
    const q = '?period=' + encodeURIComponent(period) + '&symbols=' + encodeURIComponent(tickers.join(','));
    const data = await getJSON('/analytics' + q);
    renderTable(data.results);
    wrap.textContent = `Analytics for period: ${period}`;
  } catch (e) {
    wrap.textContent = 'Analytics failed: ' + e.toString();
  }
});

// gainers/losers (top 5)
document.getElementById('gainers').addEventListener('click', async () => {
  let raw = document.getElementById('ana_tickers').value || '';
  let tickers = raw.split(',').map(s => s.trim()).filter(Boolean);
  if (tickers.length === 0) tickers = ['GC=F','SI=F'];
  const period = document.getElementById('period').value || 'daily';
  const wrap = document.getElementById('analytics_status');
  wrap.textContent = 'Computing gainers/losers...';
  try {
    const q = '?period=' + encodeURIComponent(period) + '&symbols=' + encodeURIComponent(tickers.join(','));
    const data = await getJSON('/analytics' + q);
    const results = data.results;
    // sort by pct_change (handle null)
    results.sort((a,b) => (b.pct_change||0) - (a.pct_change||0));
    const topG = results.slice(0,5);
    const topL = results.slice(-5).reverse();
    renderTable([...topG, {symbol:'---','start_usd':'','end_usd':'','pct_change':''}, ...topL]);
    wrap.textContent = `Top gainers & losers (${period})`;
  } catch (e) {
    wrap.textContent = 'Failed: ' + e.toString();
  }
});

// render table - prefer INR per10g, then INR, then USD
function renderTable(rows) {
  const tbl = document.getElementById('results_table');
  const body = document.getElementById('results_body');
  body.innerHTML = '';
  for (const r of rows) {
    let displayStart = '';
    let displayEnd = '';
    let unit = '';
    if (r && r.per10g_end_inr !== undefined && r.per10g_end_inr !== null) {
      displayStart = r.per10g_start_inr !== null ? '₹' + Number(r.per10g_start_inr).toFixed(2) : '';
      displayEnd = r.per10g_end_inr !== null ? '₹' + Number(r.per10g_end_inr).toFixed(2) : '';
      unit = ' (₹/10g)';
    } else if (r && r.end_inr !== undefined && r.end_inr !== null) {
      displayStart = r.start_inr !== null ? '₹' + Number(r.start_inr).toFixed(2) : '';
      displayEnd = r.end_inr !== null ? '₹' + Number(r.end_inr).toFixed(2) : '';
      unit = ' (₹)';
    } else if (r && r.end_usd !== undefined && r.end_usd !== null) {
      displayStart = r.start_usd !== null ? '$' + Number(r.start_usd).toFixed(2) : '';
      displayEnd = r.end_usd !== null ? '$' + Number(r.end_usd).toFixed(2) : '';
      unit = ' (USD)';
    }

    const pct = (r && typeof r.pct_change === 'number') ? Number(r.pct_change).toFixed(2) + '%' : (r && r.pct_change ? r.pct_change : '');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r && r.symbol ? r.symbol : ''}${unit}</td><td>${displayStart}</td><td>${displayEnd}</td><td class="${(r && r.pct_change>0)?'gain':(r && r.pct_change<0)?'loss':''}">${pct}</td>`;
    body.appendChild(tr);
  }
  tbl.style.display = 'table';
}

// on load: fetch config and populate fields
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const cfg = await getJSON('/config');
    if (cfg && cfg.symbols) document.getElementById('tickers').value = cfg.symbols.join(',');
    if (cfg && cfg.send_time) document.getElementById('send_time').value = cfg.send_time;
    if (cfg && cfg.email) {
      document.getElementById('sender').value = cfg.email.sender || '';
      document.getElementById('recipient').value = cfg.email.recipient || '';
    }
    const status = await getJSON('/status');
    const wrap = document.getElementById('analytics_status');
    wrap.textContent = status.last_run_preview || 'No analysis yet.';
  } catch (e) {
    console.log('Backend not reachable on load.', e);
    document.getElementById('analytics_status').textContent = 'Backend not running.';
  }
});
