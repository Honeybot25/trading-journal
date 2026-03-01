# 🚀 GEX Terminal - Deployment Options

## Overview
Your GEX Terminal is ready for deployment! Here are your options, ranked by ease and reliability:

---

## 🥇 Option 1: Railway (Recommended)
**Why**: Best Python support, persistent SQLite, no cold starts

### Quick Deploy
```bash
# 1. Get a Railway token from https://railway.app/account/tokens
export RAILWAY_TOKEN=your_token

# 2. Run deploy script
cd dashboard
./deploy-railway.sh
```

### Manual Deploy
1. Go to https://railway.app/new
2. Select "Deploy from GitHub repo"
3. Choose `Honeybot25/trading-journal`
4. Set root directory: `dashboard`
5. Add environment variables:
   - `POLYGON_API_KEY` = `JlAQap9qJ8F8VrfChiPmYpticVo6SMPO`
   - `PORT` = `8000`
   - `DASH_DEBUG` = `false`

**Files created**: `railway.json`, `Dockerfile`, `nixpacks.toml`

---

## 🥈 Option 2: Render (Easiest)
**Why**: One-click deploy, native Python support, free tier

### Quick Deploy
1. Go to https://dashboard.render.com/blueprint
2. Paste your GitHub repo URL: `https://github.com/Honeybot25/trading-journal`
3. Render auto-detects `render.yaml`
4. Click "Apply"

### Manual Deploy
1. Go to https://dashboard.render.com/
2. New + → Web Service
3. Connect GitHub repo
4. Settings:
   - **Root Directory**: `dashboard`
   - **Runtime**: Python 3
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `gunicorn -b 0.0.0.0:$PORT -w 2 --timeout 60 wsgi:application`

**Files created**: `render.yaml`, `RENDER.md`

---

## 🥉 Option 3: Fly.io (Most Control)
**Why**: Edge deployment, persistent volumes, great CLI

### Quick Deploy
```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Login
fly auth login

# 3. Deploy
cd dashboard
fly launch --name gex-terminal --no-deploy
fly volumes create gex_data --size 1 -r lax
fly secrets set POLYGON_API_KEY=JlAQap9qJ8F8VrfChiPmYpticVo6SMPO
fly deploy
```

**Files created**: `fly.toml`, `FLYIO.md`

---

## 🔧 Environment Variables

### Required
| Variable | Value | Description |
|----------|-------|-------------|
| `POLYGON_API_KEY` | `JlAQap9qJ8F8VrfChiPmYpticVo6SMPO` | Market data API |
| `PORT` | `8000` | Server port |

### Optional
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Database URL |
| `SUPABASE_ANON_KEY` | Database key |
| `DISCORD_WEBHOOK_URL` | Alert notifications |
| `DASH_DEBUG` | Set to `false` for production |

---

## ✅ Health Check

All deployments include health check at:
```
GET /health
```

Response:
```json
{"status": "ok", "service": "gex-terminal"}
```

---

## 🔗 URLs After Deploy

| Service | URL Pattern |
|---------|-------------|
| Railway | `https://gex-terminal.up.railway.app` |
| Render | `https://gex-terminal.onrender.com` |
| Fly.io | `https://gex-terminal.fly.dev` |

---

## 📁 Deployment Files Created

```
dashboard/
├── railway.json           # Railway config
├── nixpacks.toml          # Nixpacks build config
├── render.yaml            # Render infrastructure
├── fly.toml               # Fly.io config
├── Dockerfile             # Docker build
├── deploy-railway.sh      # Railway deploy script
├── RAILWAY.md             # Railway instructions
├── RENDER.md              # Render instructions
├── FLYIO.md               # Fly.io instructions
└── .github/workflows/
    └── railway-deploy.yml # GitHub Actions for Railway
```

---

## 🎯 Recommended Path

1. **Try Render first** - Easiest one-click deploy
2. **Then Railway** - Best long-term for Python apps
3. **Fly.io as backup** - Most control and flexibility

---

## 🧪 Testing After Deploy

1. Visit the root URL → GEX Terminal loads
2. Visit `/health` → Returns `{"status": "ok"}`
3. Visit `/api/signals` → Returns signal data
4. Test ticker selection → Charts update
5. Wait 60 seconds → Auto-refresh works

---

## 📊 GitHub Repo
All deployment configs are in:
https://github.com/Honeybot25/trading-journal/tree/main/dashboard