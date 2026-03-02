/**
 * Discord Alerts for Options Trading Signals
 * 
 * Sends high-confidence options alerts to Discord #trading-alerts channel
 * Features:
 * - Confidence threshold filtering (>75%)
 * - Duplicate alert prevention (1-hour cooldown per symbol)
 * - Rich Discord embeds with options-specific details
 * - Mission Control dashboard integration
 */

export interface OptionsSignal {
  symbol: string;
  type: 'CALL' | 'PUT';
  confidence: number; // 0-100
  expirationDate: string; // YYYY-MM-DD
  strikePrice: number;
  premium: number;
  underlyingPrice: number;
  unusualVolume?: boolean;
  impliedVolatility?: number;
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  timestamp: string; // ISO 8601
  source?: string;
  strategy?: string;
}

export interface DiscordAlertConfig {
  webhookUrl: string;
  channelName?: string;
  confidenceThreshold?: number;
  duplicateCooldownMs?: number;
  missionControlUrl?: string;
  testMode?: boolean;
}

export interface AlertResult {
  success: boolean;
  messageId?: string;
  error?: string;
  filtered?: boolean;
  reason?: string;
}

/**
 * Alert deduplication cache - tracks recently alerted symbols
 */
class AlertCache {
  private cache: Map<string, number> = new Map();
  private readonly cooldownMs: number;

  constructor(cooldownMs: number = 3600000) { // 1 hour default
    this.cooldownMs = cooldownMs;
  }

  /**
   * Check if symbol was recently alerted (within cooldown period)
   */
  isDuplicate(symbol: string): boolean {
    const lastAlert = this.cache.get(symbol.toUpperCase());
    if (!lastAlert) return false;
    
    const now = Date.now();
    const elapsed = now - lastAlert;
    
    if (elapsed < this.cooldownMs) {
      return true; // Still in cooldown
    }
    
    // Cooldown expired, remove from cache
    this.cache.delete(symbol.toUpperCase());
    return false;
  }

  /**
   * Mark symbol as alerted
   */
  markAlerted(symbol: string): void {
    this.cache.set(symbol.toUpperCase(), Date.now());
  }

  /**
   * Clear expired entries from cache
   */
  cleanup(): void {
    const now = Date.now();
    for (const [symbol, timestamp] of this.cache.entries()) {
      if (now - timestamp >= this.cooldownMs) {
        this.cache.delete(symbol);
      }
    }
  }

  /**
   * Get cache stats
   */
  getStats(): { size: number; symbols: string[] } {
    return {
      size: this.cache.size,
      symbols: Array.from(this.cache.keys())
    };
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
  }
}

/**
 * Discord Webhook client for sending options alerts
 */
export class DiscordOptionsAlerts {
  private config: Required<DiscordAlertConfig>;
  private cache: AlertCache;
  private lastAlertTime: number = 0;

  constructor(config: DiscordAlertConfig) {
    this.config = {
      channelName: 'trading-alerts',
      confidenceThreshold: 75,
      duplicateCooldownMs: 3600000, // 1 hour
      missionControlUrl: 'https://mission-control-lovat-rho.vercel.app',
      testMode: false,
      ...config
    };
    
    this.cache = new AlertCache(this.config.duplicateCooldownMs);
    
    // Periodic cache cleanup every 10 minutes
    setInterval(() => this.cache.cleanup(), 600000);
  }

  /**
   * Send an options alert to Discord
   * Filters low-confidence signals and duplicates
   */
  async sendOptionsAlert(signal: OptionsSignal): Promise<AlertResult> {
    // Check confidence threshold
    if (signal.confidence < this.config.confidenceThreshold) {
      return {
        success: false,
        filtered: true,
        reason: `Confidence ${signal.confidence}% below threshold ${this.config.confidenceThreshold}%`
      };
    }

    // Check for duplicate (same symbol within cooldown period)
    if (this.cache.isDuplicate(signal.symbol)) {
      return {
        success: false,
        filtered: true,
        reason: `Duplicate alert for ${signal.symbol} within cooldown period`
      };
    }

    try {
      const payload = this.buildWebhookPayload(signal);
      const response = await fetch(this.config.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Discord API error: ${response.status} - ${errorText}`);
      }

      // Mark as alerted to prevent duplicates
      this.cache.markAlerted(signal.symbol);
      this.lastAlertTime = Date.now();

      // Extract message ID from response headers if available
      const messageId = response.headers.get('x-message-id') || undefined;

      return {
        success: true,
        messageId,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Send a test alert to verify Discord integration
   */
  async sendTestAlert(): Promise<AlertResult> {
    const testSignal: OptionsSignal = {
      symbol: 'TEST',
      type: 'CALL',
      confidence: 85,
      expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      strikePrice: 150.00,
      premium: 2.50,
      underlyingPrice: 148.50,
      unusualVolume: true,
      impliedVolatility: 0.35,
      delta: 0.45,
      gamma: 0.08,
      theta: -0.05,
      vega: 0.12,
      timestamp: new Date().toISOString(),
      source: 'Test System',
      strategy: 'Unusual Volume Breakout',
    };

    return this.sendOptionsAlert(testSignal);
  }

  /**
   * Build Discord webhook payload with rich embed
   */
  private buildWebhookPayload(signal: OptionsSignal): object {
    const isCall = signal.type === 'CALL';
    const emoji = isCall ? '🟢' : '🔴';
    const color = isCall ? 0x00FF00 : 0xFF0000; // Green for calls, Red for puts
    const volumeEmoji = signal.unusualVolume ? '🔥' : '📊';
    
    const expirationFormatted = new Date(signal.expirationDate).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });

    const daysToExpiration = Math.ceil(
      (new Date(signal.expirationDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );

    const fields = [
      {
        name: `${emoji} Contract`,
        value: `**${signal.symbol}** ${signal.type}\n$${signal.strikePrice.toFixed(2)} ${expirationFormatted}`,
        inline: true,
      },
      {
        name: '🎯 Confidence',
        value: `**${signal.confidence}%**\n${this.getConfidenceBar(signal.confidence)}`,
        inline: true,
      },
      {
        name: `${volumeEmoji} Premium`,
        value: `$${signal.premium.toFixed(2)} per contract`,
        inline: true,
      },
      {
        name: '📈 Underlying',
        value: `$${signal.underlyingPrice.toFixed(2)}`,
        inline: true,
      },
      {
        name: '⏱️ DTE',
        value: `${daysToExpiration} days`,
        inline: true,
      },
      {
        name: '📊 Volume',
        value: signal.unusualVolume ? '**Unusual Activity** 🔥' : 'Normal',
        inline: true,
      },
    ];

    // Add Greeks if available
    if (signal.delta !== undefined || signal.gamma !== undefined) {
      const greeksText = [
        signal.delta !== undefined ? `Delta: ${signal.delta.toFixed(3)}` : null,
        signal.gamma !== undefined ? `Gamma: ${signal.gamma.toFixed(3)}` : null,
        signal.theta !== undefined ? `Theta: ${signal.theta.toFixed(3)}` : null,
        signal.vega !== undefined ? `Vega: ${signal.vega.toFixed(3)}` : null,
        signal.impliedVolatility !== undefined ? `IV: ${(signal.impliedVolatility * 100).toFixed(1)}%` : null,
      ].filter(Boolean).join(' | ');

      if (greeksText) {
        fields.push({
          name: '📐 Greeks',
          value: greeksText,
          inline: false,
        });
      }
    }

    // Add source/strategy if available
    if (signal.strategy || signal.source) {
      fields.push({
        name: '🔍 Signal Source',
        value: signal.strategy || signal.source || 'Unknown',
        inline: false,
      });
    }

    const payload: any = {
      content: this.config.testMode ? '🧪 **TEST ALERT** (This is a test)' : undefined,
      embeds: [
        {
          title: `🚨 OPTIONS ALERT: $${signal.symbol}`,
          description: `${signal.type} | Confidence: **${signal.confidence}%** | ${signal.unusualVolume ? 'Unusual Volume Detected' : 'Standard Signal'}`,
          color: color,
          timestamp: signal.timestamp,
          fields: fields,
          footer: {
            text: `Options Alert System • ${this.config.testMode ? 'TEST MODE' : 'Live'}`,
          },
        },
      ],
    };

    // Add link to Mission Control if configured
    if (this.config.missionControlUrl) {
      payload.embeds[0].url = `${this.config.missionControlUrl}/options/${signal.symbol.toLowerCase()}`;
      
      payload.components = [
        {
          type: 1,
          components: [
            {
              type: 2,
              style: 5,
              label: '📊 View in Mission Control',
              url: `${this.config.missionControlUrl}/options/${signal.symbol.toLowerCase()}`,
            },
          ],
        },
      ];
    }

    return payload;
  }

  /**
   * Generate visual confidence bar
   */
  private getConfidenceBar(confidence: number): string {
    const filled = Math.round(confidence / 10);
    const empty = 10 - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    return bar;
  }

  /**
   * Get cache statistics for monitoring
   */
  getCacheStats(): { size: number; symbols: string[]; lastAlertTime: number | null } {
    return {
      ...this.cache.getStats(),
      lastAlertTime: this.lastAlertTime || null,
    };
  }

  /**
   * Clear the alert cache (useful for testing)
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Check if a signal would be filtered without sending
   */
  wouldBeFiltered(signal: OptionsSignal): { filtered: boolean; reason?: string } {
    if (signal.confidence < this.config.confidenceThreshold) {
      return {
        filtered: true,
        reason: `Confidence ${signal.confidence}% below threshold ${this.config.confidenceThreshold}%`,
      };
    }

    if (this.cache.isDuplicate(signal.symbol)) {
      return {
        filtered: true,
        reason: `Duplicate alert for ${signal.symbol} within cooldown period`,
      };
    }

    return { filtered: false };
  }
}

/**
 * Factory function to create alert instance from environment variables
 */
export function createDiscordAlertsFromEnv(): DiscordOptionsAlerts {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL || process.env.DISCORD_OPTIONS_WEBHOOK_URL;
  
  if (!webhookUrl) {
    throw new Error('DISCORD_WEBHOOK_URL or DISCORD_OPTIONS_WEBHOOK_URL environment variable is required');
  }

  return new DiscordOptionsAlerts({
    webhookUrl,
    channelName: process.env.DISCORD_CHANNEL_NAME || 'trading-alerts',
    confidenceThreshold: parseInt(process.env.CONFIDENCE_THRESHOLD || '75', 10),
    duplicateCooldownMs: parseInt(process.env.DUPLICATE_COOLDOWN_MS || '3600000', 10),
    missionControlUrl: process.env.MISSION_CONTROL_URL || 'https://mission-control-lovat-rho.vercel.app',
    testMode: process.env.TEST_MODE === 'true',
  });
}

/**
 * Singleton instance for global access
 */
let globalInstance: DiscordOptionsAlerts | null = null;

export function getGlobalAlerts(): DiscordOptionsAlerts {
  if (!globalInstance) {
    globalInstance = createDiscordAlertsFromEnv();
  }
  return globalInstance;
}

export function setGlobalAlerts(alerts: DiscordOptionsAlerts): void {
  globalInstance = alerts;
}

// Default export
export default DiscordOptionsAlerts;
