import os
import json
import aiohttp
import asyncio
import requests
import websockets
from twitch_auth import TwitchAuth

TWITCH_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
TWITCH_API_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"
BROADCASTER_USERNAME = os.getenv("BROADCASTER_USERNAME")
BOT_USERNAME = os.getenv("BOT_USERNAME")

auth = TwitchAuth()

def get_channel_id(username: str) -> str:
    """Fetch the broadcaster's user ID (channel ID) from their username."""
    headers = auth.get_headers()
    params = {"login": username}
    response = requests.get("https://api.twitch.tv/helix/users", headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if not data["data"]:
        raise ValueError(f"No user found with username '{username}'")
    return data["data"][0]["id"]

async def subscribe_event(session_id, event_type, condition, version=1):
    async with aiohttp.ClientSession() as session:
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

        async with session.post(TWITCH_API_URL, headers=headers, json=payload) as resp:
            data = await resp.json()
            print("Subscription:", json.dumps(data, indent=2))

async def twitch_listener():
    async with websockets.connect(TWITCH_WS_URL) as ws:
        async for msg in ws:
            data = json.loads(msg)
            mtype = data["metadata"]["message_type"]

            if mtype == "session_welcome":
                session_id = data["payload"]["session"]["id"]
                print(f"Connected with session {session_id}")

                broadcaster_id = get_channel_id(BROADCASTER_USERNAME)
                user_id = get_channel_id(BOT_USERNAME)
                
                # Subscribe to chat messages
                await subscribe_event(
                    session_id,
                    "channel.chat.message",
                    {
                        "broadcaster_user_id": broadcaster_id,
                        "user_id": user_id
                    }
                )
                await subscribe_event(
                    session_id,
                    "channel.cheer",
                    {
                        "broadcaster_user_id": broadcaster_id,
                    }
                )
                #await subscribe_event(
                #    session_id,
                #    "channel.bits.use",
                #    {
                #        "broadcaster_user_id": broadcaster_id,
                #    }
                #)

            elif mtype == "notification":
                event_type = data["metadata"]["subscription_type"]
                event = data["payload"]["event"]

                if event_type == "channel.chat.message":
                    user = event["chatter_user_name"]
                    msg_text = event["message"]["text"]
                    print(f"[Chat] {user}: {msg_text}")

                #elif event_type == "channel.follow":
                #    print(f"[Follow] {event['user_name']} followed!")

            #elif mtype == "session_keepalive":
                #print("Keepalive received.")

            elif mtype == "session_reconnect":
                new_url = data["payload"]["session"]["reconnect_url"]
                print("Reconnect to:", new_url)
                return await twitch_listener()  # simple reconnect logic
