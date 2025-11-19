import os
import json
import time
import webbrowser
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from scopes import SCOPES

load_dotenv()

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
PORT = 8090
REDIRECT_URI = f"http://localhost:{PORT}"
DEFAULT_SCOPES = ["user:read:email"]

class TwitchAuth:
    def __init__(self, scopes=None, broadcaster_id=None, bot_id=None):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.scopes = scopes if scopes is not None else DEFAULT_SCOPES
        self.broadcaster_id = broadcaster_id
        self.bot_id = bot_id
        self.token_file = None

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Missing TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET")

        if self.broadcaster_id:
            self.token_file = f"twitch_token-{self.broadcaster_id}.json"
        #else:
        #    # fallback to a generic token file
        #    self.token_file = "twitch_token.json"

    # ----------------------------
    # Token storage
    # ----------------------------
    def save_token(self, data):
        data["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        ).isoformat()
        with open(self.token_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Tokens saved to {self.token_file}")

    def load_token(self):
        print("DEBUG: self.token_file =", self.token_file)
        if not os.path.exists(self.token_file):
            return None
        with open(self.token_file, "r") as f:
            return json.load(f)

    # ----------------------------
    # Device flow
    # ----------------------------
    def authenticate_device(self):
        device_data = self._request_device_code()
        print("=== DEVICE AUTHORIZATION ===")
        print(f"Go to: {device_data['verification_uri']}")
        print(f"Enter the code: {device_data['user_code']}")
        print("============================")

        token_data = self._poll_for_token(
            device_code=device_data["device_code"], interval=device_data["interval"]
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
        url = "https://id.twitch.tv/oauth2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        while True:
            time.sleep(interval)
            r = requests.post(url, data=payload)

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
    # Local redirect flow
    # ----------------------------
    def authenticate_local(self):
        scope_str = "+".join(self.scopes)
        auth_url = (
            f"https://id.twitch.tv/oauth2/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={scope_str}"
        )

        print("Opening Twitch OAuth URL in browser...")
        webbrowser.open(auth_url)

        server = HTTPServer(("localhost", PORT), self._make_local_handler())
        print(f"Waiting for Twitch redirect at {REDIRECT_URI}...")
        server.serve_forever()

        return self.load_token()

    def _make_local_handler(self):
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
                print(f"Received authorization code: {code}")

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
                parent.save_token(token_data)

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Twitch token saved successfully! You can close this window.")
                threading.Thread(target=self.server.shutdown).start()

        return OAuthHandler

    # ----------------------------
    # Refresh token
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
    # Unified entry point
    # ----------------------------
    def get_valid_token(self, method="device", validate=False):
        token_data = self.load_token()
        now = datetime.now(timezone.utc)

        if token_data and "access_token" in token_data:
            expires_at = datetime.fromisoformat(token_data["expires_at"])

            if now < expires_at:
                access_token = token_data["access_token"]

                # Optional validation
                if validate:
                    resp = requests.get(
                        "https://id.twitch.tv/oauth2/validate",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if resp.status_code != 200:
                        print("Token invalid according to Twitch:", resp.text)
                    else:
                        data = resp.json()
                        token_scopes = data.get("scopes", [])
                        missing_scopes = [s for s in self.scopes if s not in token_scopes]
                        if missing_scopes:
                            print("Token missing required scopes:", missing_scopes)
                            return self.reauthenticate(method)
                        else:
                            print("Token has all required scopes.")

                return access_token

            print("Token expired locally, attempting refresh...")
            if "refresh_token" in token_data:
                try:
                    token_data = self.refresh_token(token_data["refresh_token"])
                    self.save_token(token_data)
                    return token_data["access_token"]
                except Exception as e:
                    print("Refresh failed:", e)

        # Use the new reauthenticate method
        print("Starting full re-authentication...")
        return self.reauthenticate(method)

    def reauthenticate(self, method="device"):
        """Perform full re-authentication based on the chosen method."""
        if method == "device":
            token_data = self.authenticate_device()
        elif method == "local":
            token_data = self.authenticate_local()
        else:
            raise ValueError(f"Unknown authentication method: {method}")
        return token_data["access_token"]

    # ----------------------------
    # Headers helper
    # ----------------------------
    def get_headers(self, json_body=False, method="device", validate=False):
        access_token = self.get_valid_token(method=method, validate=validate)
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {access_token}",
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers
