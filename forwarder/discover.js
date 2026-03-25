/**
 * discover.js — List all Telegram channels/groups you are subscribed to
 *
 * Run this LOCALLY after completing auth.js to find the channel IDs
 * you need for TELEGRAM_CHANNEL_IDS.
 *
 * Usage:
 *   1. Make sure .env has TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_STRING_SESSION
 *   2. Run: node discover.js
 *   3. Look for the Israeli news/security channels in the output
 *   4. Copy their IDs (negative numbers like -1001234567890) into
 *      TELEGRAM_CHANNEL_IDS as a comma-separated list
 *
 * Tip: Run with --filter to search by name:
 *   node discover.js --filter חדשות
 */

require('dotenv').config();
const { TelegramClient } = require('telegram');
const { StringSession } = require('telegram/sessions');

const API_ID   = parseInt(process.env.TELEGRAM_API_ID);
const API_HASH = process.env.TELEGRAM_API_HASH;
const SESSION  = process.env.TELEGRAM_STRING_SESSION || '';

if (!API_ID || !API_HASH || !SESSION) {
  console.error('❌ Missing TELEGRAM_API_ID, TELEGRAM_API_HASH, or TELEGRAM_STRING_SESSION in .env');
  console.error('   Run "node auth.js" first to generate the session string.');
  process.exit(1);
}

const filterArg = process.argv.includes('--filter')
  ? process.argv[process.argv.indexOf('--filter') + 1]
  : null;

(async () => {
  const client = new TelegramClient(new StringSession(SESSION), API_ID, API_HASH, {
    connectionRetries: 5,
  });

  await client.connect();
  console.log('✅ Connected\n');

  const dialogs = await client.getDialogs({ limit: 500 });

  // Separate channels from groups/chats
  const channels = [];
  const groups   = [];

  for (const dialog of dialogs) {
    const entity = dialog.entity;
    if (!entity) continue;

    const isChannel = entity.className === 'Channel';
    if (!isChannel) continue;

    const isMegagroup = !!entity.megagroup;
    const fullId = Number(`-100${entity.id.toString()}`);
    const title  = dialog.title || entity.title || 'Unknown';

    if (filterArg && !title.includes(filterArg)) continue;

    const entry = { id: fullId, title };
    if (isMegagroup) groups.push(entry);
    else             channels.push(entry);
  }

  const pad = (s, n) => s.toString().padEnd(n);

  if (channels.length) {
    console.log('📢 Broadcast Channels:');
    console.log(pad('ID', 22) + 'NAME');
    console.log('─'.repeat(70));
    channels.forEach(c => console.log(pad(c.id, 22) + c.title));
    console.log('');
  }

  if (groups.length) {
    console.log('👥 Megagroups / Supergroups:');
    console.log(pad('ID', 22) + 'NAME');
    console.log('─'.repeat(70));
    groups.forEach(g => console.log(pad(g.id, 22) + g.title));
    console.log('');
  }

  if (!channels.length && !groups.length) {
    console.log(filterArg
      ? `No channels/groups matching "${filterArg}" found.`
      : 'No channels or groups found.'
    );
  } else {
    console.log('─'.repeat(70));
    console.log(`Found: ${channels.length} channels, ${groups.length} megagroups`);
    if (!filterArg) {
      console.log('\nTip: Use --filter <keyword> to search, e.g.:');
      console.log('  node discover.js --filter חדשות');
      console.log('  node discover.js --filter פיקוד');
    }
    console.log('\nCopy the relevant IDs into TELEGRAM_CHANNEL_IDS (comma-separated):');
    console.log('Example: TELEGRAM_CHANNEL_IDS=-1001234567890,-1009876543210,-1005555555555');
  }

  await client.disconnect();
  process.exit(0);
})().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
