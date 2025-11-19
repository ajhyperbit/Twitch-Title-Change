import os
import sys
import json
import aiohttp
import asyncio
import requests
import websockets
from twitch_auth import TwitchAuth

TWITCH_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
TWITCH_API_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
BROADCASTER_USERNAME = os.getenv("BROADCASTER_USERNAME")
BOT_USERNAME = os.getenv("BOT_USERNAME")

def get_app_token(client_id: str, client_secret: str) -> str:
    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["access_token"]

def get_channel_id(username: str) -> str:
    """Fetch the broadcaster's user ID using an app access token."""
    app_token = get_app_token(CLIENT_ID, CLIENT_SECRET)
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {app_token}"
    }
    params = {"login": username}
    response = requests.get("https://api.twitch.tv/helix/users", headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if not data["data"]:
        raise ValueError(f"No user found with username '{username}'")
    return data["data"][0]["id"]

async def subscribe_event(auth: TwitchAuth, session_id, event_type, condition, version=1):
    """
    Subscribes to a Twitch EventSub topic with detailed debug logging so you
    can identify which subscription failed authorization.
    """

    payload = {
        "type": event_type,
        "version": version,
        "condition": condition,
        "transport": {
            "method": "websocket",
            "session_id": session_id
        }
    }

    headers = auth.get_headers(json_body=True)

    print("\n=== EventSub Debug ===")
    print("Attempting Subscription:")
    print(json.dumps(payload, indent=2))
    print("\nHeaders:")
    print(json.dumps(headers, indent=2))
    print("\nSending Request...\n")

    async with aiohttp.ClientSession() as session:
        async with session.post(TWITCH_API_URL, headers=headers, json=payload) as resp:
            status = resp.status
            try:
                data = await resp.json()
            except Exception:
                text = await resp.text()
                print("Non-JSON Response:")
                print(text)
                return

            print("Response Status:", status)
            print("Response JSON:")
            print(json.dumps(data, indent=2))

            if status == 403:
                print("\nAuthorization failed for subscription:")
                print(f"  type:      {event_type}")
                print(f"  version:   {version}")
                print(f"  condition: {condition}")
                print("  --> This subscription did not have required authorization.\n")
                sys.exit(1)

            return data


async def twitch_listener(auth: TwitchAuth):
    async with websockets.connect(TWITCH_WS_URL) as ws:
        async for msg in ws:
            data = json.loads(msg)
            mtype = data["metadata"]["message_type"]
            print(mtype)

            if mtype == "session_welcome":
                session_id = data["payload"]["session"]["id"]
                print(f"Connected with session {session_id}")

                broadcaster_id = get_channel_id(BROADCASTER_USERNAME)
                user_id = get_channel_id(BOT_USERNAME)

                # Chat messages
                await subscribe_event(
                    auth,
                    session_id,
                    "channel.chat.message",
                    {
                        "broadcaster_user_id": broadcaster_id,
                        "user_id": user_id
                    }
                )

                # Uncomment if needed:
                # await subscribe_event(
                #     session_id,
                #     "channel.cheer",
                #     { "broadcaster_user_id": broadcaster_id }
                # )

                # await subscribe_event(
                #     session_id,
                #     "channel.bits.use",
                #     { "broadcaster_user_id": broadcaster_id }
                # )

            elif mtype == "notification":
                event_type = data["metadata"]["subscription_type"]
                event = data["payload"]["event"]

                if event_type == "channel.chat.message":
                    user = event["chatter_user_name"]
                    msg_text = event["message"]["text"]
                    print(f"[Chat] {user}: {msg_text}")

            elif mtype == "session_reconnect":
                new_url = data["payload"]["session"]["reconnect_url"]
                print("Reconnect to:", new_url)
                return await twitch_listener()  # Reconnect loop
