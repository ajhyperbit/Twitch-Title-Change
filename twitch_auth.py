import os
import json
import requests
from datetime import datetime, timedelta, timezone

TOKEN_FILE = "twitch_token.json"
OAUTH_URL = "https://id.twitch.tv/oauth2/token"

def load_dotenv(filepath=".env"):
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        print(f"⚠️ .env file '{filepath}' not found.")

load_dotenv()

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

def log(message: str):
    """Simple UTC timestamped logger."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {message}")

def save_token(data: dict):
    """Write token data to disk."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log("💾 Token data saved to disk.")

def load_token() -> dict | None:
    """Read token data from disk."""
    if not os.path.exists(TOKEN_FILE):
        log("⚠️ No token file found.")
        return None
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)

def refresh_token_if_needed() -> str:
    """Ensure valid token, refreshing automatically if expired."""
    token_data = load_token()
    if not token_data:
        raise RuntimeError("No token file found — generate one via initial OAuth flow.")

    expires_at = datetime.fromisoformat(token_data["expires_at"])
    now = datetime.now(timezone.utc)

    # Display current expiration time
    log(f"🕒 Current token expires at {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    if now < expires_at:
        minutes_left = int((expires_at - now).total_seconds() / 60)
        log(f"✅ Token still valid ({minutes_left} min left).")
        return token_data["access_token"]

    # Otherwise, refresh
    log("🔄 Token expired — attempting to refresh...")

    refresh_resp = requests.post(
        OAUTH_URL,
        params={
            "grant_type": "refresh_token",
            "refresh_token": token_data["refresh_token"],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )

    if refresh_resp.status_code != 200:
        log(f"❌ Failed to refresh token: {refresh_resp.text}")
        raise RuntimeError("Token refresh failed.")

    new_data = refresh_resp.json()
    new_data["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=new_data["expires_in"])
    ).isoformat()

    save_token(new_data)

    expires_display = datetime.fromisoformat(new_data["expires_at"]).strftime("%Y-%m-%d %H:%M:%S UTC")
    log(f"✅ Token refreshed successfully. New expiration: {expires_display}")

    return new_data["access_token"]

def get_headers() -> dict:
    """Return headers for authenticated Twitch API requests."""
    access_token = refresh_token_if_needed()
    return {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }
