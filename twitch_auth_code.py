import os
import json
import time
import webbrowser
import threading
import requests
from twitch_functions import get_channel_id
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------
# ENVIRONMENT / CONFIG
# -------------------------------------
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
BROADCASTER_USERNAME = (os.getenv("BROADCASTER_USERNAME"))
BROADCASTER_ID = get_channel_id(BROADCASTER_USERNAME)
TOKEN_FILE = f"twitch_token-{BROADCASTER_ID}.json"

# Default scopes (can be overridden)
DEFAULT_SCOPES = [
    "user:read:email"
]

# Used only for local redirect flow
PORT = 8090
REDIRECT = "http://localhost"
REDIRECT_URI = f"{REDIRECT}:{PORT}"


# ==================================================================
#                        TOKEN STORAGE UTILITIES
# ==================================================================
def save_token(data):
    """Save token to disk, adding expires_at timestamp."""
    data["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
    ).isoformat()

    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"💾 Tokens saved to {TOKEN_FILE}")


def load_token():
    """Load token from disk if present."""
    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


# ==================================================================
#             BASE CLASS FOR TWITCH AUTHORIZATION
# ==================================================================
class TwitchAuth:
    def __init__(self, scopes=None):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.scopes = scopes or DEFAULT_SCOPES

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Missing TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET")

    # ==============================================================
    #                  DEVICE AUTHORIZATION FLOW
    # ==============================================================
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

        save_token(token_data)
        return token_data

    def _request_device_code(self):
        url = "https://id.twitch.tv/oauth2/device"
        payload = {
            "client_id": self.client_id,
            "scopes": " ".join(self.scopes)
        }

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

    # ==============================================================
    #                 LOCAL REDIRECT FLOW (BROWSER)
    # ==============================================================
    def authenticate_local(self):
        scope_str = "+".join(self.scopes)

        auth_url = (
            f"https://id.twitch.tv/oauth2/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={scope_str}"
        )

        print("🌐 Opening Twitch OAuth URL in browser...")
        print(auth_url)
        webbrowser.open(auth_url)

        server = HTTPServer(("localhost", PORT),
                            self._make_handler())
        print(f"🚀 Waiting for Twitch redirect at {REDIRECT_URI}...")
        server.serve_forever()

    def _make_handler(self):
        parent = self

        class OAuthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                if "code" not in params:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing ?code= in callback.")
                    return

                code = params["code"][0]
                print(f"✅ Received authorization code: {code}")

                token_resp = requests.post(
                    "https://id.twitch.tv/oauth2/token",
                    params={
                        "client_id": parent.client_id,
                        "client_secret": parent.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": REDIRECT_URI,
                    },
                )

                if token_resp.status_code != 200:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"Failed to exchange code for token.")
                    print("Token exchange failed:", token_resp.text)
                    return

                token_data = token_resp.json()
                save_token(token_data)

                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    b"Twitch token saved successfully! You can close this window."
                )

                threading.Thread(target=self.server.shutdown).start()

        return OAuthHandler
