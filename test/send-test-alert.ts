/**
 * Test script for Discord Options Alerts
 * Sends a test alert to verify the integration is working
 * 
 * Usage:
 *   DISCORD_WEBHOOK_URL=<your_webhook> npx tsx test/send-test-alert.ts
 *   # Or with test mode (prefixes message with TEST):
 *   TEST_MODE=true DISCORD_WEBHOOK_URL=<webhook> npx tsx test/send-test-alert.ts
 */

import { DiscordOptionsAlerts, OptionsSignal } from '../src/lib/discord-alerts';

const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const RESET = '\x1b[0m';

async function main() {
  console.log('🚀 Discord Options Alert Test\n');

  // Get webhook URL from environment
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL || process.env.DISCORD_OPTIONS_WEBHOOK_URL;
  
  if (!webhookUrl) {
    console.error(`${RED}❌ Error: DISCORD_WEBHOOK_URL environment variable is required${RESET}`);
    console.log('\nUsage:');
    console.log('  DISCORD_WEBHOOK_URL=<your_webhook_url> npx tsx test/send-test-alert.ts');
    console.log('\nOr set it in a .env file:');
    console.log('  echo "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..." > .env');
    process.exit(1);
  }

  // Create alert instance
  const alerts = new DiscordOptionsAlerts({
    webhookUrl,
    channelName: process.env.DISCORD_CHANNEL_NAME || 'trading-alerts',
    confidenceThreshold: 75,
    duplicateCooldownMs: 3600000, // 1 hour
    missionControlUrl: process.env.MISSION_CONTROL_URL || 'https://mission-control-lovat-rho.vercel.app',
    testMode: process.env.TEST_MODE === 'true',
  });

  console.log('📋 Configuration:');
  console.log(`   Webhook: ${webhookUrl.substring(0, 40)}...`);
  console.log(`   Channel: ${alerts['config'].channelName}`);
  console.log(`   Confidence Threshold: ${alerts['config'].confidenceThreshold}%`);
  console.log(`   Test Mode: ${alerts['config'].testMode ? '✅ YES' : '❌ NO'}\n`);

  // Test 1: Filter low confidence signals
  console.log('🧪 Test 1: Low confidence signal filtering...');
  const lowConfidenceSignal: OptionsSignal = {
    symbol: 'AAPL',
    type: 'CALL',
    confidence: 50, // Below 75% threshold
    expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    strikePrice: 185.00,
    premium: 3.50,
    underlyingPrice: 182.50,
    timestamp: new Date().toISOString(),
  };

  const filterCheck = alerts.wouldBeFiltered(lowConfidenceSignal);
  if (filterCheck.filtered) {
    console.log(`${GREEN}✅ PASS: Low confidence signal correctly filtered${RESET}`);
    console.log(`   Reason: ${filterCheck.reason}\n`);
  } else {
    console.log(`${RED}❌ FAIL: Low confidence signal should have been filtered${RESET}\n`);
  }

  // Test 2: Send test alert
  console.log('🧪 Test 2: Sending test alert to Discord...');
  
  const testSignal: OptionsSignal = {
    symbol: 'NVDA',
    type: 'CALL',
    confidence: 87,
    expirationDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    strikePrice: 875.00,
    premium: 12.50,
    underlyingPrice: 860.25,
    unusualVolume: true,
    impliedVolatility: 0.42,
    delta: 0.52,
    gamma: 0.012,
    theta: -0.35,
    vega: 0.85,
    timestamp: new Date().toISOString(),
    source: 'Options Flow Scanner',
    strategy: 'Unusual Volume + Momentum Breakout',
  };

  try {
    const result = await alerts.sendOptionsAlert(testSignal);
    
    if (result.success) {
      console.log(`${GREEN}✅ PASS: Test alert sent successfully!${RESET}`);
      if (result.messageId) {
        console.log(`   Message ID: ${result.messageId}`);
      }
    } else if (result.filtered) {
      console.log(`${YELLOW}⚠️  FILTERED: ${result.reason}${RESET}`);
    } else {
      console.log(`${RED}❌ FAIL: ${result.error}${RESET}`);
    }
  } catch (error) {
    console.error(`${RED}❌ ERROR: ${error}${RESET}`);
  }

  // Test 3: Duplicate prevention
  console.log('\n🧪 Test 3: Duplicate prevention...');
  const duplicateCheck = alerts.wouldBeFiltered(testSignal);
  if (duplicateCheck.filtered && duplicateCheck.reason?.includes('Duplicate')) {
    console.log(`${GREEN}✅ PASS: Duplicate detection working${RESET}`);
    console.log(`   Reason: ${duplicateCheck.reason}\n`);
  } else {
    console.log(`${RED}❌ FAIL: Duplicate should have been detected${RESET}\n`);
  }

  // Test 4: Cache stats
  console.log('📊 Cache Stats:');
  const stats = alerts.getCacheStats();
  console.log(`   Cached symbols: ${stats.size}`);
  console.log(`   Symbols: ${stats.symbols.join(', ') || '(none)'}`);
  console.log(`   Last alert: ${stats.lastAlertTime ? new Date(stats.lastAlertTime).toLocaleTimeString() : 'N/A'}\n`);

  // Test 5: PUT option test
  console.log('🧪 Test 4: Sending PUT option test alert...');
  
  // Clear cache first to allow the new alert
  alerts.clearCache();
  
  const putSignal: OptionsSignal = {
    symbol: 'TSLA',
    type: 'PUT',
    confidence: 82,
    expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    strikePrice: 175.00,
    premium: 4.25,
    underlyingPrice: 180.50,
    unusualVolume: true,
    impliedVolatility: 0.58,
    delta: -0.48,
    gamma: 0.015,
    theta: -0.42,
    vega: 0.22,
    timestamp: new Date().toISOString(),
    source: 'Dark Pool Scanner',
    strategy: 'Dark Pool Block Trade Detection',
  };

  try {
    const putResult = await alerts.sendOptionsAlert(putSignal);
    
    if (putResult.success) {
      console.log(`${GREEN}✅ PASS: PUT alert sent successfully!${RESET}\n`);
    } else if (putResult.filtered) {
      console.log(`${YELLOW}⚠️  FILTERED: ${putResult.reason}${RESET}\n`);
    } else {
      console.log(`${RED}❌ FAIL: ${putResult.error}${RESET}\n`);
    }
  } catch (error) {
    console.error(`${RED}❌ ERROR: ${error}${RESET}\n`);
  }

  console.log('✨ All tests completed!');
  console.log('\n📖 Next steps:');
  console.log('   1. Check your Discord #trading-alerts channel for the test messages');
  console.log('   2. Verify the formatting and links look correct');
  console.log('   3. Set up the webhook URL in your production environment');
  console.log('   4. Import and use sendOptionsAlert() in your signal generation code\n');
}

main().catch(console.error);
