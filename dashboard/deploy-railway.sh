#!/bin/bash
# Deploy to Railway using CLI with token

set -e

echo "🚀 GEX Terminal Railway Deploy Script"
echo "======================================"

# Check for Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check for token
if [ -z "$RAILWAY_TOKEN" ]; then
    echo "⚠️  RAILWAY_TOKEN not set"
    echo "Get your token from: https://railway.app/account/tokens"
    echo "Then run: export RAILWAY_TOKEN=your_token"
    exit 1
fi

echo "✅ Railway CLI found"
echo "📦 Checking project..."

# Try to link or create project
if [ ! -f .railway/config.json ]; then
    echo "🆕 Creating new Railway project..."
    railway init --name gex-terminal
fi

echo "🔧 Setting environment variables..."
railway variables set POLYGON_API_KEY="${POLYGON_API_KEY:-JlAQap9qJ8F8VrfChiPmYpticVo6SMPO}"
railway variables set PORT="8000"
railway variables set PYTHONUNBUFFERED="1"
railway variables set DASH_DEBUG="false"

# Optional vars if set
if [ -n "$SUPABASE_URL" ]; then
    railway variables set SUPABASE_URL="$SUPABASE_URL"
fi
if [ -n "$SUPABASE_ANON_KEY" ]; then
    railway variables set SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"
fi
if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    railway variables set DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL"
fi

echo "🚀 Deploying..."
railway up

echo "✅ Deployment complete!"
echo ""
echo "Get your URL with: railway domain"