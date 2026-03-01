# GEX Terminal Railway Deployment

## Railway Environment Variables

Set these in Railway Dashboard:

### Required
- `POLYGON_API_KEY` - Your Polygon.io API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key

### Optional
- `DISCORD_WEBHOOK_URL` - For signal alerts
- `REDIS_URL` - For caching (Railway provides this)

## Deployment

1. Push to GitHub or use Railway CLI
2. Railway auto-detects Dockerfile
3. Environment variables auto-populate
4. Health check at `/health`

## URLs
- App: https://[project].up.railway.app
- Health: https://[project].up.railway.app/health
- API Signals: https://[project].up.railway.app/api/signals

## Features
- Persistent SQLite storage in `/app/data/`
- Gunicorn with 2 workers
- Health checks enabled
- Auto-restart on failure