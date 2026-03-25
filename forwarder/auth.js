/**
 * auth.js — One-time Telegram session generator
 *
 * Run this LOCALLY (not on Railway) to authenticate your Telegram account
 * and generate the TELEGRAM_STRING_SESSION value.
 *
 * Usage:
 *   1. Create a .env file with TELEGRAM_API_ID and TELEGRAM_API_HASH
 *   2. Run: node auth.js
 *   3. Enter your phone number (with country code, e.g. +972501234567)
 *   4. Enter the code Telegram sends you via SMS/app
 *   5. Enter your 2FA password if you have one (press Enter to skip)
 *   6. Copy the printed TELEGRAM_STRING_SESSION value to Railway env vars
 *
 * ⚠️  NEVER commit the session string to git or share it publicly.
 *     It gives full access to your Telegram account.
 */

require('dotenv').config();
const { TelegramClient } = require('telegram');
const { StringSession } = require('telegram/sessions');
const input = require('input');

const API_ID   = parseInt(process.env.TELEGRAM_API_ID);
const API_HASH = process.env.TELEGRAM_API_HASH;

if (!API_ID || !API_HASH) {
  console.error('❌ Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env');
  console.error('   Get them from https://my.telegram.org → API development tools');
  process.exit(1);
}

(async () => {
  console.log('🔐 Telegram User-Bot Authentication\n');
  console.log('This will authenticate your personal Telegram account.');
  console.log('The session string allows the forwarder to read channels you are subscribed to.\n');

  const client = new TelegramClient(new StringSession(''), API_ID, API_HASH, {
    connectionRetries: 5,
  });

  await client.start({
    phoneNumber: async () => {
      return input.text('📱 Phone number (with country code, e.g. +972501234567): ');
    },
    phoneCode: async () => {
      return input.text('📨 Verification code from Telegram: ');
    },
    password: async () => {
      const pw = await input.text('🔒 2FA password (press Enter if none): ');
      return pw || undefined;
    },
    onError: (err) => {
      console.error('Auth error:', err.message);
    },
  });

  const sessionString = client.session.save();

  console.log('\n✅ Authentication successful!\n');
  console.log('═'.repeat(70));
  console.log('Copy this value into Railway as TELEGRAM_STRING_SESSION:');
  console.log('═'.repeat(70));
  console.log('\n' + sessionString + '\n');
  console.log('═'.repeat(70));
  console.log('\n⚠️  Keep this secret — it grants full access to your Telegram account.\n');

  await client.disconnect();
  process.exit(0);
})().catch(err => {
  console.error('❌ Fatal error:', err.message);
  process.exit(1);
});
