require('dotenv').config();
const { TelegramClient } = require('telegram');
const { StringSession } = require('telegram/sessions');
const { NewMessage } = require('telegram/events');
const { Client: WhatsAppClient, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

// ─── Startup Validation ───────────────────────────────────────────────────────
const REQUIRED_VARS = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_STRING_SESSION'];
const missing = REQUIRED_VARS.filter(v => !process.env[v]);
if (missing.length) {
  console.error(`\n❌ Missing required environment variables: ${missing.join(', ')}`);
  if (missing.includes('TELEGRAM_STRING_SESSION')) {
    console.error('   → Run "node auth.js" locally to generate your session string.');
  }
  if (missing.includes('TELEGRAM_API_ID') || missing.includes('TELEGRAM_API_HASH')) {
    console.error('   → Get API credentials from https://my.telegram.org');
  }
  process.exit(1);
}

// ─── Config ───────────────────────────────────────────────────────────────────
const API_ID    = parseInt(process.env.TELEGRAM_API_ID);
const API_HASH  = process.env.TELEGRAM_API_HASH;
const SESSION   = process.env.TELEGRAM_STRING_SESSION;
const WA_GROUP  = process.env.WHATSAPP_GROUP_ID || '';
const PORT      = process.env.PORT || 3000;

// Comma-separated negative channel IDs, e.g. -1001234567890,-1009876543210
// Leave empty to monitor ALL channels (useful during first-run discovery)
const CHANNEL_IDS = (process.env.TELEGRAM_CHANNEL_IDS || '')
  .split(',')
  .map(s => s.trim())
  .filter(Boolean)
  .map(s => parseInt(s));

if (CHANNEL_IDS.length === 0) {
  console.warn('⚠️  TELEGRAM_CHANNEL_IDS not set — listening to ALL channels. Run "node discover.js" to find your target IDs.');
}

// ─── Hebrew Keywords ──────────────────────────────────────────────────────────

/** Phase A — launch detected (triggers immediate WhatsApp alert) */
const PHASE_A_KEYWORDS = [
  'זוהה שיגור', 'שיגורים', 'ירי מ', 'דיווח ראשוני',
  'צבע אדום', 'אזעקה', 'כיפת ברזל', 'יירוט'
];

/** Phase C — event over (triggers all-clear message + reset) */
const PHASE_C_KEYWORDS = [
  'האירוע הסתיים', 'ניתן לצאת מהמרחב המוגן', 'כל ברור',
  'סיום אירוע', 'אין סכנה', 'הסתיים האירוע'
];

/** Launch origin keywords */
const ORIGINS = [
  'איראן', 'לבנון', 'תימן', 'עזה', 'הרצועה',
  'סוריה', 'עיראק', 'חיזבאללה', "חות'י"
];

/** Target area/direction keywords */
const TARGETS = [
  'מרכז', 'דרום', 'צפון', 'נגב', 'אילת', 'גוש דן',
  'בית שמש', 'ירושלים', 'דימונה', "ת\"א", "פ\"ת",
  'תל אביב', 'פתח תקווה', 'בני ברק', 'חיפה', 'גליל',
  'שרון', 'שפלה', 'עמק', 'גולן', 'ים המלח',
  'ראשון לציון', 'נתניה', 'אשדוד', 'אשקלון',
  'באר שבע', 'רחובות', 'מודיעין', 'כרמל', 'עכו',
  'טבריה', 'צפת', 'קריות', 'חדרה', 'נהריה'
];

/** Timing patterns — matched in order, first match wins */
const TIMING_PATTERNS = [
  { re: /בעוד (\d+) דקות?/, fmt: m => `בעוד ${m[1]} דקות` },
  { re: /בעוד שתי דקות/,   fmt: () => 'בעוד ~2 דקות' },
  { re: /בעוד דקה/,         fmt: () => 'בעוד דקה (~1 דקה)' },
  { re: /בעוד חצי דקה/,    fmt: () => 'בעוד ~30 שניות' },
  { re: /צפי[: ]+([^\n.]+)/,fmt: m => `צפי: ${m[1].trim()}` },
  { re: /(\d{1,2}:\d{2})/,  fmt: m => `בשעה ${m[1]}` },
];

// ─── Event State Machine ──────────────────────────────────────────────────────
// States: IDLE → ALERTING → ENDED → IDLE
//
// IDLE:     Waiting for Phase A keywords
// ALERTING: Active event, first message sent, collecting updates
// ENDED:    Phase C detected, all-clear sent, waiting 60s then resetting

function makeIdleState() {
  return {
    state: 'IDLE',
    startTime: null,
    // Info already sent in WhatsApp messages
    sentOrigins:  new Set(),
    sentTargets:  new Set(),
    sentTiming:   null,
    // Pending info received but not yet sent (batched for 20s)
    pendingOrigins:  new Set(),
    pendingTargets:  new Set(),
    pendingTiming:   null,
    pendingChannels: new Set(),
    pendingTimer:    null,
    endedTimer:      null,
  };
}

let ev = makeIdleState();

function resetToIdle() {
  clearTimeout(ev.pendingTimer);
  clearTimeout(ev.endedTimer);
  ev = makeIdleState();
  console.log('[State] → IDLE');
}

// ─── Parser ───────────────────────────────────────────────────────────────────
function parseMessage(text) {
  const result = {
    isPhaseA: PHASE_A_KEYWORDS.some(kw => text.includes(kw)),
    isPhaseC: PHASE_C_KEYWORDS.some(kw => text.includes(kw)),
    origins:  ORIGINS.filter(o => text.includes(o)),
    targets:  TARGETS.filter(t => text.includes(t)),
    timing:   null,
  };
  for (const { re, fmt } of TIMING_PATTERNS) {
    const m = text.match(re);
    if (m) { result.timing = fmt(m); break; }
  }
  return result;
}

// ─── Formatting ───────────────────────────────────────────────────────────────
function nowStr() {
  return new Date().toLocaleTimeString('he-IL', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    timeZone: 'Asia/Jerusalem'
  });
}

function buildInitialAlert(channelTitle, parsed) {
  let msg = `🚨 *זוהה שיגור!*\n\n`;
  if (parsed.origins.length)  msg += `🎯 *מקור:* ${parsed.origins.join(', ')}\n`;
  if (parsed.targets.length)  msg += `📍 *כיוון:* ${parsed.targets.join(', ')}\n`;
  else                         msg += `📍 *כיוון:* בבירור\n`;
  if (parsed.timing)          msg += `⏱️ *צפי אזעקות:* ${parsed.timing}\n`;
  else                         msg += `⏱️ *צפי:* בבירור\n`;
  msg += `\n📡 *מדווח:* ${channelTitle}`;
  msg += `\n🕐 ${nowStr()}`;
  return msg;
}

function buildUpdateMessage(origins, targets, timing, channels) {
  const channelList = [...channels].slice(0, 3).join(', ');
  let msg = `🔄 *עדכון — שיגור בתהליך*\n\n`;
  if (origins.length) msg += `🎯 *מקור:* ${origins.join(', ')}\n`;
  if (targets.length) msg += `📍 *אזורים:* ${targets.join(', ')}\n`;
  if (timing)         msg += `⏱️ *צפי אזעקות:* ${timing}\n`;
  msg += `\n📡 *מדווח:* ${channelList}`;
  msg += `\n🕐 ${nowStr()}`;
  return msg;
}

function buildAllClear(channelTitle) {
  return (
    `✅ *האירוע הסתיים*\n\n` +
    `ניתן לצאת מהמרחב המוגן.\n\n` +
    `📡 *מדווח:* ${channelTitle}\n` +
    `🕐 ${nowStr()}`
  );
}

// ─── Pending Update Batching ──────────────────────────────────────────────────
// When new info arrives during an active event, we batch it for 20 seconds
// and then send a single consolidated update — avoiding 5 messages from 5 channels.
const PENDING_BATCH_MS = 20_000;

function flushPendingUpdate() {
  if (ev.state !== 'ALERTING') return;

  const origins  = [...ev.pendingOrigins];
  const targets  = [...ev.pendingTargets];
  const timing   = ev.pendingTiming;
  const channels = new Set(ev.pendingChannels);

  // Clear pending
  ev.pendingOrigins  = new Set();
  ev.pendingTargets  = new Set();
  ev.pendingTiming   = null;
  ev.pendingChannels = new Set();
  ev.pendingTimer    = null;

  if (origins.length === 0 && targets.length === 0 && !timing) return;

  // Record as sent
  origins.forEach(o => ev.sentOrigins.add(o));
  targets.forEach(t => ev.sentTargets.add(t));
  if (timing) ev.sentTiming = timing;

  sendWhatsApp(buildUpdateMessage(origins, targets, timing, channels));
}

function queuePendingUpdate(channelTitle, parsed) {
  let addedSomething = false;

  parsed.origins.forEach(o => {
    if (!ev.sentOrigins.has(o) && !ev.pendingOrigins.has(o)) {
      ev.pendingOrigins.add(o);
      addedSomething = true;
    }
  });
  parsed.targets.forEach(t => {
    if (!ev.sentTargets.has(t) && !ev.pendingTargets.has(t)) {
      ev.pendingTargets.add(t);
      addedSomething = true;
    }
  });
  if (parsed.timing && parsed.timing !== ev.sentTiming && parsed.timing !== ev.pendingTiming) {
    ev.pendingTiming = parsed.timing;
    addedSomething = true;
  }

  if (!addedSomething) return; // nothing new

  ev.pendingChannels.add(channelTitle);

  // Start batch timer if not already running
  if (!ev.pendingTimer) {
    ev.pendingTimer = setTimeout(flushPendingUpdate, PENDING_BATCH_MS);
  }
}

// ─── Main Event Handler ───────────────────────────────────────────────────────
async function handleMessage(channelTitle, text) {
  const parsed = parseMessage(text);

  // ── Phase C: Event ended ────────────────────────────────────────────────────
  if (parsed.isPhaseC && ev.state === 'ALERTING') {
    console.log(`[State] Phase C from: ${channelTitle}`);
    // Cancel any pending update — the event is over
    clearTimeout(ev.pendingTimer);
    ev.pendingTimer = null;
    ev.state = 'ENDED';
    await sendWhatsApp(buildAllClear(channelTitle));
    // Auto-reset after 60s in case more messages arrive
    ev.endedTimer = setTimeout(resetToIdle, 60_000);
    return;
  }

  // ── Phase A: New launch detected ────────────────────────────────────────────
  if (parsed.isPhaseA && ev.state === 'IDLE') {
    console.log(`[State] → ALERTING | Phase A from: ${channelTitle}`);
    ev.state     = 'ALERTING';
    ev.startTime = new Date();

    // Record what we know so far as "sent"
    parsed.origins.forEach(o => ev.sentOrigins.add(o));
    parsed.targets.forEach(t => ev.sentTargets.add(t));
    ev.sentTiming = parsed.timing;

    // Send IMMEDIATELY — speed is critical
    await sendWhatsApp(buildInitialAlert(channelTitle, parsed));
    return;
  }

  // ── ALERTING: Collect new info for update ───────────────────────────────────
  if (ev.state === 'ALERTING') {
    // Only process messages with at least some relevant content
    const hasContent = parsed.origins.length || parsed.targets.length || parsed.timing;
    if (!hasContent) return;

    queuePendingUpdate(channelTitle, parsed);
  }
}

// ─── WhatsApp Client ──────────────────────────────────────────────────────────
const waClient = new WhatsAppClient({
  authStrategy: new LocalAuth(),
  puppeteer: {
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    headless: true,
  },
});

let waReady = false;

waClient.on('qr', qr => {
  console.log('\n📱 Scan this QR code with WhatsApp:\n');
  qrcode.generate(qr, { small: true });
  console.log('');
});

waClient.on('ready', async () => {
  waReady = true;
  console.log('✅ WhatsApp ready\n');

  if (!WA_GROUP) {
    // Print all group JIDs so the user can find their target
    try {
      const chats = await waClient.getChats();
      const groups = chats.filter(c => c.isGroup);
      console.log('📋 WhatsApp Groups (set WHATSAPP_GROUP_ID to one of these):');
      groups.forEach(g =>
        console.log(`   ${g.name.padEnd(40)} → ${g.id._serialized}`)
      );
      console.log('');
    } catch (e) {
      console.error('[WhatsApp] Could not list groups:', e.message);
    }
  }
});

waClient.on('auth_failure', msg => {
  console.error('[WhatsApp] Auth failure:', msg);
});

waClient.on('disconnected', reason => {
  waReady = false;
  console.warn('[WhatsApp] Disconnected:', reason);
});

async function sendWhatsApp(text) {
  if (!waReady) {
    console.warn('[WhatsApp] Not ready — queued message dropped:\n' + text.slice(0, 100));
    return;
  }
  if (!WA_GROUP) {
    console.log('[WhatsApp] WHATSAPP_GROUP_ID not set. Message that would have been sent:\n' + text + '\n');
    return;
  }
  try {
    await waClient.sendMessage(WA_GROUP, text);
    console.log(`[WhatsApp] ✅ Sent (${text.length} chars)`);
  } catch (err) {
    console.error('[WhatsApp] Send error:', err.message);
  }
}

// ─── Telegram Client (GramJS User-Bot) ────────────────────────────────────────
async function startTelegram() {
  const client = new TelegramClient(
    new StringSession(SESSION),
    API_ID,
    API_HASH,
    {
      connectionRetries: 10,
      retryDelay: 2000,
      autoReconnect: true,
    }
  );

  // Connect using existing session (no interactive auth needed here)
  await client.connect();

  const me = await client.getMe();
  console.log(`✅ Telegram connected as: ${me.firstName} ${me.lastName || ''} (@${me.username || 'no username'})`);

  client.addEventHandler(async (update) => {
    try {
      const msg = update.message;
      if (!msg?.text) return;

      // ── Resolve channel ID ────────────────────────────────────────────────
      const peerId = msg.peerId;
      if (!peerId?.className?.includes('Channel') && !peerId?.channelId) return;

      // GramJS stores channel IDs as BigInt without the -100 prefix
      const rawId = peerId.channelId || peerId.chatId;
      if (!rawId) return;
      const channelId = Number(`-100${rawId.toString()}`);

      // ── Channel filter ────────────────────────────────────────────────────
      if (CHANNEL_IDS.length > 0 && !CHANNEL_IDS.includes(channelId)) {
        // Log unrecognized channels only during discovery mode
        if (CHANNEL_IDS.length === 0) {
          console.log(`[Telegram] Unknown channel ${channelId} — add to TELEGRAM_CHANNEL_IDS if relevant`);
        }
        return;
      }

      // ── Resolve channel title ─────────────────────────────────────────────
      let channelTitle = `Channel ${channelId}`;
      try {
        const entity = await client.getEntity(peerId);
        channelTitle = entity.title || channelTitle;
      } catch (_) {}

      const text = msg.text;
      console.log(`[Telegram] "${channelTitle}" → ${text.slice(0, 120).replace(/\n/g, ' ')}`);

      await handleMessage(channelTitle, text);
    } catch (err) {
      console.error('[Telegram] Handler error:', err.message);
    }
  }, new NewMessage({}));

  console.log(`👂 Listening to ${CHANNEL_IDS.length > 0 ? CHANNEL_IDS.length + ' channels' : 'ALL channels'}`);
}

// ─── Express Health Check ─────────────────────────────────────────────────────
const app = express();
app.get('/health', (_req, res) => res.json({
  status: 'ok',
  state: ev.state,
  uptime: process.uptime(),
  waReady,
}));
app.listen(PORT, () => console.log(`✅ Health check running on port ${PORT}`));

// ─── Boot ─────────────────────────────────────────────────────────────────────
(async () => {
  console.log('🚀 Iron Dome Forwarder starting...\n');
  waClient.initialize();
  await startTelegram();
})().catch(err => {
  console.error('❌ Fatal startup error:', err.message);
  process.exit(1);
});
