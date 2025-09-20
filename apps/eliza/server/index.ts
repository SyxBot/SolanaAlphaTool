// eliza/server/index.ts
import express from "express";

const app = express();
app.use(express.json());

app.post("/ingest", (req, res) => {
  const count = Array.isArray(req.body) ? req.body.length : (req.body ? 1 : 0);
  console.log("[ELIZA][INGEST]", { count, keys: Object.keys(req.body || {}) });
  res.json({ ok: true, count });
});

app.get("/health", (req, res) => {
  res.json({ ok: true });
});

const port = Number(process.env.PORT || 3001);
app.listen(port, () => {
  console.log(`Eliza ingest listening on ${port}`);
});