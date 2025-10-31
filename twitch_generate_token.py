import os
import json
import webbrowser
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
import threading

# ----------------------------
# Load .env manually
# ----------------------------
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

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("❌ Missing TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET in .env or environment variables.")

# ----------------------------
# Configuration
# ----------------------------
PORT = 8090
REDIRECT = "http://localhost"
REDIRECT_URI = f"{REDIRECT}:{PORT}"  # Must match Twitch app
SCOPES = [
    "channel:manage:broadcast"
]
TOKEN_FILE = "twitch_token.json"

# ----------------------------
# OAuth handler
# ----------------------------
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Request path:", self.path)
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" not in params:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b"Missing ?code= in callback URL. Make sure you authorized the app."
            )
            return

        code = params["code"][0]
        print(f"✅ Received authorization code: {code}")

        # Exchange code for tokens
        token_resp = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            },
        )

        if token_resp.status_code != 200:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Failed to exchange code for token.")
            print("❌ Token exchange failed:", token_resp.text)
            return

        data = token_resp.json()
        data["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        ).isoformat()

        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)

        print(f"💾 Tokens saved to {TOKEN_FILE}")

        # Respond to browser
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            "✅ Twitch token saved successfully! You can close this window.".encode("utf-8")
        )

        # Shutdown server in a separate thread to avoid blocking
        threading.Thread(target=self.server.shutdown).start()

# ----------------------------
# Run server and open OAuth URL
# ----------------------------
def generate_token():
    scope_str = "+".join(SCOPES)
    auth_url = (
        f"https://id.twitch.tv/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope_str}"
    )

    print("🌐 Opening Twitch OAuth URL in browser...")
    print(auth_url)
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), OAuthHandler)
    print(f"🚀 Waiting for Twitch to redirect to {REDIRECT_URI} ...")
    server.serve_forever()


if __name__ == "__main__":
    generate_token()
