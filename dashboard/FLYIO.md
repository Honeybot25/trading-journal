# GEX Terminal - Fly.io Deployment

## Why Fly.io
- Persistent volumes (SQLite works great)
- Edge deployment (fast globally)
- Easy CLI deployment
- Good free tier

## Quick Deploy

### 1. Install Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
```

### 2. Login
```bash
fly auth login
```

### 3. Launch App
```bash
cd dashboard
fly launch --name gex-terminal --region lax --no-deploy
```

### 4. Create Volume (for SQLite persistence)
```bash
fly volumes create gex_data --size 1 --region lax
```

### 5. Set Secrets
```bash
fly secrets set POLYGON_API_KEY=JlAQap9qJ8F8VrfChiPmYpticVo6SMPO
fly secrets set SUPABASE_URL=your_supabase_url
fly secrets set SUPABASE_ANON_KEY=your_supabase_key
```

### 6. Deploy
```bash
fly deploy
```

## Access App
- App URL: https://gex-terminal.fly.dev
- Status: fly status
- Logs: fly logs

## Configuration
See `fly.toml` for app configuration.