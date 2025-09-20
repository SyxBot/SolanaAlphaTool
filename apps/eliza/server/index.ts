// eliza/server/index.ts
import express from "express";
import "dotenv/config";
import { fileURLToPath } from "url";
import path from "path";

const app = express();
app.use(express.json());

const EVENTS: any[] = [];
const MAX_EVENTS = 500;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

app.use(express.static(path.join(__dirname, "../public")));

app.post("/ingest", (req, res) => {
  const count = Array.isArray(req.body) ? req.body.length : req.body ? 1 : 0;
  console.log("[ELIZA][INGEST]", { count, keys: Object.keys(req.body || {}) });

  if (Array.isArray(req.body)) {
    req.body.forEach((payload) => {
      EVENTS.push({ ts: Date.now(), ...payload });
      if (EVENTS.length > MAX_EVENTS) EVENTS.shift();
    });
  }

  res.json({ ok: true, count });
});

app.get("/api/events", (req, res) => {
  const since = Number(req.query.since) || 0;
  const filteredEvents = EVENTS.filter((event) => event.ts > since);
  res.json({ now: Date.now(), events: filteredEvents });
});

// optional seed for UI test
app.post('/api/seed', (req, res) => {
  const ev = { ts: Date.now(), symbol: 'SEED', name: 'Seed Event', mint: 'SeedMint', creator: 'Seed', tx: 'SeedTx' };
  EVENTS.push(ev);
  if (EVENTS.length > MAX_EVENTS) EVENTS.splice(0, EVENTS.length - MAX_EVENTS);
  res.json({ ok: true, added: ev });
});

app.get("/health", (req, res) => {
  res.json({ ok: true });
});

// Minimal inline dashboard
app.get("/__dash", (_req, res) => {
  res.type("html").send(`<!doctype html><meta charset="utf-8">
<title>Eliza Dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{color-scheme:dark light}
  body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;padding:16px;background:#0b0e14;color:#e6e6e6}
  h1{margin:0 0 12px;font-size:18px}
  .row{display:flex;gap:8px;align-items:center;margin:8px 0}
  input,button{padding:8px 10px;border-radius:10px;border:1px solid #2a2f3a;background:#121620;color:#e6e6e6}
  button{cursor:pointer}
  pre{background:#0f1320;border:1px solid #1f2430;border-radius:12px;padding:12px;max-height:60vh;overflow:auto}
  .badge{background:#1f6feb;border-radius:9999px;padding:2px 8px;font-size:12px;margin-left:8px}
</style>
<h1>Eliza Inline Dashboard <span id="count" class="badge">0</span></h1>
<div class="row">
  <button id="refresh">Refresh</button>
  <input id="payload" style="flex:1" placeholder='{"type":"ping","payload":{"msg":"hello"}}'>
  <button id="seed">Seed</button>
</div>
<pre id="out">Loading…</pre>
<script>
  async function fetchEvents(){
    try{
      const r = await fetch('/api/events', { credentials:'include' });
      const data = await r.json();
      const arr = Array.isArray(data) ? data : (data.events || []);
      document.getElementById('count').textContent = arr.length;
      document.getElementById('out').textContent = JSON.stringify(arr.slice(-100), null, 2);
    }catch(e){
      document.getElementById('out').textContent = 'Error loading events: ' + (e && e.message || e);
    }
  }
  async function seedOnce(){
    try{
      const txt = document.getElementById('payload').value || '{"type":"ping","payload":{"msg":"hello"}}';
      const body = JSON.parse(txt);
      await fetch('/ingest', { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(body) });
      fetchEvents();
    }catch(e){ alert(e.message); }
  }
  document.getElementById('refresh').onclick = fetchEvents;
  document.getElementById('seed').onclick = seedOnce;
  fetchEvents();
  setInterval(fetchEvents, 5000);
<\/script>`);
});

// Make crashes visible instead of silent process exits:
process.on('uncaughtException', (err) => {
  console.error('[UNCAUGHT]', err?.stack || err);
});
process.on('unhandledRejection', (reason) => {
  console.error('[UNHANDLED REJECTION]', reason);
});

const PORT = Number(process.env.PORT) || 3001;
app.listen(PORT, () => {
  console.log(`Eliza ingest listening on ${PORT}`);
});