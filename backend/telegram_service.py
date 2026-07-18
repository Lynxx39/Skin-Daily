import urllib.request
import urllib.parse
import json
import os

def _get_supabase_credentials():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY")
    if url and key:
        return url, key
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("VITE_SUPABASE_URL="):
                        url = line.strip().split("=")[1].strip()
                    elif line.startswith("VITE_SUPABASE_PUBLISHABLE_KEY="):
                        key = line.strip().split("=")[1].strip()
    except Exception:
        pass
    return url, key

def _lookup_chat_id(username: str) -> str:
    """Lookup the Telegram chat_id for a given username from telegram_bindings."""
    url, key = _get_supabase_credentials()
    if not url or not key or not username:
        return None
    try:
        full_url = f"{url.rstrip('/')}/rest/v1/telegram_bindings?username=eq.{username}&select=chat_id"
        req = urllib.request.Request(full_url, headers={
            "apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data and len(data) > 0:
                return data[0]["chat_id"]
    except Exception as e:
        print(f"Failed to lookup chat_id for {username}: {e}")
    return None

def send_telegram_message(message: str, username: str = None) -> bool:
    """Send a Telegram message. If username is provided, sends to that user's bound chat_id.
    Falls back to TELEGRAM_CHAT_ID env var if no username or binding not found."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("Telegram bot token missing. Message not sent.")
        return False

    chat_id = None
    if username:
        chat_id = _lookup_chat_id(username)
    
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not chat_id:
        print("No chat_id found. Message not sent.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("ok", False)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False
