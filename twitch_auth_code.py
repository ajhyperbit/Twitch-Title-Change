import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from twitch_functions import get_channel_id

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
BROADCASTER_USERNAME = os.getenv("BROADCASTER_USERNAME")
BROADCASTER_ID = get_channel_id(BROADCASTER_USERNAME)
TOKEN_FILE = f"twitch_token-{BROADCASTER_ID}.json"

DEFAULT_SCOPES = ["user:read:email"]

class TwitchAuth:
    def __init__(self, scopes=None):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.scopes = scopes or DEFAULT_SCOPES
        self.token_file = TOKEN_FILE

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Missing TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET")

    # ----------------------------
    # Token storage utilities
    # ----------------------------
    def save_token(self, data):
        """Save token to disk, adding expires_at timestamp."""
        data["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        ).isoformat()
        with open(self.token_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Tokens saved to {self.token_file}")

    def load_token(self):
        """Load token from disk if present."""
        if not os.path.exists(self.token_file):
            return None
        with open(self.token_file, "r") as f:
            return json.load(f)

    # ----------------------------
    # Token refresh
    # ----------------------------
    def refresh_token(self, refresh_token):
        url = "https://id.twitch.tv/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        r = requests.post(url, data=payload)
        r.raise_for_status()
        return r.json()

    # ----------------------------
    # Device flow authentication
    # ----------------------------
    def authenticate_device(self):
        device_data = self._request_device_code()
        print(f"\n=== DEVICE AUTHORIZATION ===")
        print(f"Go to: {device_data['verification_uri']}")
        print(f"Enter the code: {device_data['user_code']}")
        print("============================\n")
        token_data = self._poll_for_token(
            device_code=device_data["device_code"],
            interval=device_data["interval"],
        )
        self.save_token(token_data)
        return token_data

    def _request_device_code(self):
        url = "https://id.twitch.tv/oauth2/device"
        payload = {"client_id": self.client_id, "scopes": " ".join(self.scopes)}
        r = requests.post(url, data=payload)
        r.raise_for_status()
        return r.json()

    def _poll_for_token(self, device_code, interval):
        token_url = "https://id.twitch.tv/oauth2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        while True:
            time.sleep(interval)
            r = requests.post(token_url, data=payload)
            if r.status_code == 200:
                print("Authorization complete!")
                return r.json()

            data = r.json()
            msg = data.get("error") or data.get("message")

            if msg == "authorization_pending":
                print("Waiting for user authorization...")
                continue
            if msg == "slow_down":
                interval += 5
                print("Slowing down polling...")
                continue
            raise Exception(f"Token polling failed: {data}")

    # ----------------------------
    # Public method: get valid token
    # ----------------------------
    def get_valid_token(self):
        token_data = self.load_token()
        if token_data:
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(timezone.utc) < expires_at:
                if set(self.scopes).issubset(set(token_data.get("scope", []))):
                    print("✅ Using existing token.")
                    return token_data
                else:
                    print("⚠️ Scopes mismatch, re-authenticating...")
            else:
                print("⚠️ Token expired, attempting to refresh...")
                if "refresh_token" in token_data:
                    try:
                        token_data = self.refresh_token(token_data["refresh_token"])
                        self.save_token(token_data)
                        print("✅ Token refreshed successfully.")
                        return token_data
                    except Exception as e:
                        print("⚠️ Refresh failed:", e)
                        print("🔄 Falling back to full re-authentication...")

        # No valid token, authenticate
        return self.authenticate_device()
