# GEX Terminal - Render Deployment

## Why Render (Backup to Railway)
- Native Python/Docker support
- Persistent disks (SQLite works)
- Free tier with custom domains
- Easy GitHub integration
- No cold starts

## Deployment Steps

### 1. Via Web Dashboard
1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect GitHub repo: `Honeybot25/trading-journal`
4. Configure:
   - **Name**: `gex-terminal`
   - **Root Directory**: `dashboard`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -b 0.0.0.0:$PORT -w 2 --timeout 60 wsgi:application`

### 2. Environment Variables
Add in Render dashboard:
- `POLYGON_API_KEY` = `JlAQap9qJ8F8VrfChiPmYpticVo6SMPO`
- `PORT` = `8000`
- `PYTHONUNBUFFERED` = `1`
- `DASH_DEBUG` = `false`
- `SUPABASE_URL` = (your Supabase URL)
- `SUPABASE_ANON_KEY` = (your Supabase key)

### 3. Deploy
Click "Create Web Service" - auto-deploys on git push!

## Features
- Health check at `/health`
- Auto-deploy on git push
- Free SSL certificate
- Persistent disk available