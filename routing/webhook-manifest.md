# Webhook Routing Manifest (Source of Truth)

Last updated: 2026-03-09
Owner: AppDev (forensics draft)

## Producer → Transport → Destination

| Producer | Transport | Env key / config | Destination | Status |
|---|---|---|---|---|
| `options_alerts_bridge.py` | Discord Webhook HTTP POST | `DISCORD_OPTIONS_WEBHOOK_URL` | Discord channel (ID to be documented) | Active |
| `dashboard/discord_alerts.py` | Discord Webhook HTTP POST | `DISCORD_WEBHOOK_URL` | Discord channel (ID to be documented) | Active |
| `discord_alert_sender.py` | Discord Webhook HTTP POST | `DISCORD_WEBHOOK_URL` (has fallback hardcoded URL) | Discord channel (undocumented) | **Risk: fallback** |
| `gex_webhook_server.py` | Webhook server endpoint | N/A | Downstream path unclear | **Needs ownership** |
| `webhook_server.py` | Webhook server endpoint | N/A | Downstream path unclear | **Needs ownership** |

## Known Risks

1. Duplicate sender paths (`dashboard/discord_alerts.py` and `discord_alert_sender.py`) may create duplicate alerts.
2. Hardcoded webhook fallback in `discord_alert_sender.py` bypasses env governance.
3. Two webhook server entrypoints with unclear separation (`gex_webhook_server.py` vs `webhook_server.py`).
4. Destination channel IDs are not explicitly documented.

## Remediation (ordered)

1. Remove hardcoded webhook fallback and require env-only routing.
2. Choose one canonical sender path per alert type and deprecate duplicates.
3. Define ownership/scope for webhook server entrypoints; retire one if redundant.
4. Add destination channel IDs to this manifest.
5. Add startup validation for required webhook env keys.
