// Reads Claude Code's local transcript logs (~/.claude/projects/**/*.jsonl)
// and totals token usage. Each API response can be logged several times
// (once per content block), so entries are de-duplicated by message id + request id.

const fs = require('fs');
const path = require('path');
const os = require('os');

const PROJECTS_DIR = path.join(os.homedir(), '.claude', 'projects');

// file path -> { mtimeMs, size, entries: Map<key, { ts, input, output, cacheWrite, cacheRead }> }
const fileCache = new Map();

function listJsonl(dir) {
  const out = [];
  let items;
  try {
    items = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const item of items) {
    const full = path.join(dir, item.name);
    if (item.isDirectory()) out.push(...listJsonl(full));
    else if (item.name.endsWith('.jsonl')) out.push(full);
  }
  return out;
}

function parseFile(file) {
  const entries = new Map();
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch {
    return entries;
  }
  for (const line of text.split('\n')) {
    if (!line.includes('"usage"')) continue;
    let row;
    try {
      row = JSON.parse(line);
    } catch {
      continue; // partially written last line
    }
    const msg = row.message;
    const u = msg && msg.usage;
    if (!u || !row.timestamp) continue;
    const key = `${msg.id || ''}:${row.requestId || ''}`;
    entries.set(key, {
      ts: Date.parse(row.timestamp),
      model: msg.model || 'unknown',
      input: u.input_tokens || 0,
      output: u.output_tokens || 0,
      cacheWrite: u.cache_creation_input_tokens || 0,
      cacheRead: u.cache_read_input_tokens || 0,
    });
  }
  return entries;
}

function emptyBucket() {
  return { input: 0, output: 0, cacheWrite: 0, cacheRead: 0, total: 0, requests: 0 };
}

function add(bucket, e, countCacheReads) {
  bucket.input += e.input;
  bucket.output += e.output;
  bucket.cacheWrite += e.cacheWrite;
  bucket.cacheRead += e.cacheRead;
  bucket.total += e.input + e.output + e.cacheWrite + (countCacheReads ? e.cacheRead : 0);
  bucket.requests += 1;
}

function getUsage({ countCacheReads = true } = {}) {
  const files = listJsonl(PROJECTS_DIR);
  const seen = new Set(files);
  for (const f of fileCache.keys()) if (!seen.has(f)) fileCache.delete(f);

  for (const file of files) {
    let st;
    try {
      st = fs.statSync(file);
    } catch {
      continue;
    }
    const cached = fileCache.get(file);
    if (cached && cached.mtimeMs === st.mtimeMs && cached.size === st.size) continue;
    fileCache.set(file, { mtimeMs: st.mtimeMs, size: st.size, entries: parseFile(file) });
  }

  // Merge across files so resumed sessions that copy history aren't double counted.
  const all = new Map();
  for (const { entries } of fileCache.values()) {
    for (const [k, v] of entries) all.set(k, v);
  }

  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const todayMs = startOfToday.getTime();
  const weekMs = Date.now() - 7 * 24 * 60 * 60 * 1000;

  const today = emptyBucket();
  const week = emptyBucket();
  const allTime = emptyBucket();
  const days = new Map(); // local date string -> total
  let lastActivity = 0;
  let lastModel = null;

  for (const e of all.values()) {
    add(allTime, e, countCacheReads);
    if (e.ts >= weekMs) add(week, e, countCacheReads);
    if (e.ts >= todayMs) add(today, e, countCacheReads);
    const day = new Date(e.ts).toDateString();
    days.set(day, (days.get(day) || 0) + e.input + e.output + e.cacheWrite + (countCacheReads ? e.cacheRead : 0));
    if (e.ts > lastActivity) {
      lastActivity = e.ts;
      lastModel = e.model;
    }
  }

  const bestDay = Math.max(0, ...days.values());

  // Consecutive days with usage, counting back from today (or yesterday if today is empty so far).
  let streak = 0;
  const d = new Date(todayMs);
  if (!days.has(d.toDateString())) d.setDate(d.getDate() - 1);
  while (days.has(d.toDateString())) {
    streak++;
    d.setDate(d.getDate() - 1);
  }

  return {
    today, week, allTime,
    sessions: files.length,
    activeDays: days.size,
    bestDay,
    streak,
    lastActivity,
    lastModel,
  };
}

module.exports = { getUsage, PROJECTS_DIR };
