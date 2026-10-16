// Shows your Claude Code token usage as Discord Rich Presence.
// Usage:  node index.js          run the presence
//         node index.js --print  print current stats and exit (no Discord needed)

const fs = require('fs');
const path = require('path');
const { getUsage } = require('./usage');
const { DiscordIPC } = require('./discord-ipc');

const CONFIG_PATH = path.join(__dirname, 'config.json');
const DEFAULTS = {
  clientId: '',
  title: '', // overrides the app name shown after "Playing"
  refreshSeconds: 15,
  countCacheReads: true,
  activityType: 0, // 0 Playing, 2 Listening, 3 Watching, 5 Competing
  showStatsInMemberList: true,
  largeImage: '',
  largeImageText: '',
  smallImage: '',
  buttons: [],
};

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) return { ...DEFAULTS };
  return { ...DEFAULTS, ...JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8')) };
}

function fmt(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
  return String(n);
}

// Unicode "Mathematical Sans-Serif Bold" letters and digits — renders bold anywhere Discord shows text.
function bold(s) {
  return [...s]
    .map((ch) => {
      const c = ch.codePointAt(0);
      if (c >= 65 && c <= 90) return String.fromCodePoint(0x1d5d4 + c - 65);
      if (c >= 97 && c <= 122) return String.fromCodePoint(0x1d5ee + c - 97);
      if (c >= 48 && c <= 57) return String.fromCodePoint(0x1d7ec + c - 48);
      return ch;
    })
    .join('');
}

function bar(fraction, width = 10) {
  const filled = Math.round(Math.min(1, Math.max(0, fraction)) * width);
  return '▰'.repeat(filled) + '▱'.repeat(width - filled);
}

// "claude-opus-5-5" -> "Opus 5.5"
function prettyModel(id) {
  if (!id) return 'Claude';
  const m = id.match(/claude-([a-z]+)-(\d+)(?:-(\d+))?/i);
  if (!m) return id;
  return `${m[1][0].toUpperCase()}${m[1].slice(1)} ${m[2]}${m[3] && m[3].length <= 2 ? '.' + m[3] : ''}`;
}

function slides(u) {
  const pct = u.bestDay ? u.today.total / u.bestDay : 0;
  const avg = u.week.total / 7;
  return [
    {
      details: `⚡ ${bold('TODAY')} » ${bold(fmt(u.today.total))} tokens`,
      state: `${bar(pct)} ${Math.round(pct * 100)}% of best day`,
    },
    {
      details: `🔥 ${bold('THIS WEEK')} » ${bold(fmt(u.week.total))} tokens`,
      state: `📈 avg ${fmt(avg)}/day · ${u.week.requests.toLocaleString()} requests`,
    },
    {
      details: `🏆 ${bold('ALL TIME')} » ${bold(fmt(u.allTime.total))} tokens`,
      state: `💬 ${u.allTime.requests.toLocaleString()} requests · ${u.sessions} sessions`,
    },
    {
      details: `🧠 ${bold(prettyModel(u.lastModel))} ✦ ${fmt(u.today.output)} written today`,
      state: `🔥 ${u.streak} day streak · 👑 best day ${fmt(u.bestDay)}`,
    },
  ];
}

function buildActivity(config, slideIndex = 0) {
  const u = getUsage({ countCacheReads: config.countCacheReads });
  const all = slides(u);
  const slide = all[slideIndex % all.length];
  const activity = {
    type: config.activityType,
    ...(config.title && { name: config.title.slice(0, 128) }),
    details: slide.details.slice(0, 128),
    state: slide.state.slice(0, 128),
    instance: false,
  };
  if (config.showStatsInMemberList) activity.status_display_type = 2; // member list shows `details`

  const hover = `✦ ${fmt(u.today.total)} tokens today ✦`;
  if (config.largeImage || config.smallImage) {
    activity.assets = {};
    if (config.largeImage) {
      activity.assets.large_image = config.largeImage;
      activity.assets.large_text = (config.largeImageText || hover).slice(0, 128);
    }
    if (config.smallImage) {
      activity.assets.small_image = config.smallImage;
      activity.assets.small_text = `🔥 ${u.streak} day streak`;
    }
  }
  if (config.buttons && config.buttons.length) activity.buttons = config.buttons.slice(0, 2);
  return { activity, usage: u, count: all.length };
}

function printStats(config) {
  const u = getUsage({ countCacheReads: config.countCacheReads });
  const row = (label, b) =>
    `${label.padEnd(9)} total ${fmt(b.total).padStart(7)} | in ${fmt(b.input).padStart(6)} | out ${fmt(b.output).padStart(6)}` +
    ` | cache write ${fmt(b.cacheWrite).padStart(6)} | cache read ${fmt(b.cacheRead).padStart(7)} | ${b.requests} requests`;
  console.log(row('Today', u.today));
  console.log(row('7 days', u.week));
  console.log(row('All time', u.allTime));
  console.log(`Sessions: ${u.sessions}  Active days: ${u.activeDays}  Streak: ${u.streak}  Best day: ${fmt(u.bestDay)}  Last model: ${u.lastModel || '-'}`);
  console.log('\nDiscord slides:');
  for (const s of slides(u)) console.log(`  ${s.details}\n  ${s.state}\n`);
}

async function run(config) {
  if (!config.clientId) {
    console.error('No clientId set. Copy config.example.json to config.json and paste your Discord Application ID.');
    process.exit(1);
  }
  const refreshMs = Math.max(15, config.refreshSeconds) * 1000; // Discord rate-limits presence updates
  const startedAt = Date.now();
  let client = null;
  let slideIndex = 0;

  async function ensureConnected() {
    if (client) return true;
    const c = new DiscordIPC(config.clientId);
    try {
      await c.connect();
    } catch (err) {
      console.log(`[${new Date().toLocaleTimeString()}] Waiting for Discord: ${err.message}`);
      return false;
    }
    c.on('close', () => {
      console.log('Discord connection closed, will retry.');
      client = null;
    });
    c.on('error', (err) => console.error('Discord error:', err.message));
    client = c;
    console.log('Connected to Discord.');
    return true;
  }

  async function tick() {
    if (!(await ensureConnected())) return;
    const { activity, count } = buildActivity(config, slideIndex);
    slideIndex = (slideIndex + 1) % count;
    activity.timestamps = { start: startedAt };
    client.setActivity(activity);
    console.log(`[${new Date().toLocaleTimeString()}] ${activity.details} | ${activity.state}`);
  }

  await tick();
  setInterval(() => tick().catch((e) => console.error(e)), refreshMs);

  const shutdown = () => {
    if (client) client.close();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

const config = loadConfig();
if (process.argv.includes('--print')) printStats(config);
else run(config);
