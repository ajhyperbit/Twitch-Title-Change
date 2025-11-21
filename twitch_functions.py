import os
import sys
import json
import time
import aiohttp
import asyncio
import requests
import websockets
from scopes import SCOPES
from twitch_auth import TwitchAuth

TWITCH_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
TWITCH_API_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
BROADCASTER_USERNAME = os.getenv("BROADCASTER_USERNAME")
BOT_USERNAME = os.getenv("BOT_USERNAME")

#Title variables
MAX_SUBS = int(os.getenv("MAX_SUBS"))
UPDATE_INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES"))
BASE_SUBS = int(os.getenv("BASE_SUBS"))
LINEAR = os.getenv("LINEAR")
title = os.getenv("title")
insert_after = int(os.getenv("insert_after"))

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
    Subscribes to a Twitch EventSub topic with debug logging.
    """

    payload = {
        "type": event_type,
        "version": version,
        "condition": condition,
        "transport": {"method": "websocket", "session_id": session_id}
    }
    headers = auth.get_headers(json_body=True)

    print("\n=== EventSub Debug ===")
    print("Payload:", json.dumps(payload, indent=2))
    print("Headers:", json.dumps(headers, indent=2))
    print("Sending Request...\n")

    async with aiohttp.ClientSession() as session:
        async with session.post(TWITCH_API_URL, headers=headers, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                text = await resp.text()
                print("Non-JSON Response:", text)
                return

            print("Status:", resp.status)
            print("Response:", json.dumps(data, indent=2))

            if resp.status == 403:
                print(f"\nAuthorization failed for subscription {event_type} v{version} with condition {condition}")
                sys.exit(1)

            return data

message_queue = asyncio.Queue()

async def twitch_listener(auth: TwitchAuth):
    async with websockets.connect(TWITCH_WS_URL) as ws:
        async for msg in ws:
            #print(msg)
            data = json.loads(msg)
            mtype = data["metadata"]["message_type"]

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

                #await subscribe_event(
                #    auth,
                #    session_id,
                #    "channel.cheer",
                #    { "broadcaster_user_id": broadcaster_id }
                #)

            elif mtype == "notification":
                event_type = data["metadata"]["subscription_type"]
                event = data["payload"]["event"]

                if event_type == "channel.chat.message":
                    user = event["chatter_user_name"]
                    msg_text = event["message"]["text"]
                    broadcaster_user_name = event["broadcaster_user_name"]
                    print(f"[Chat: {broadcaster_user_name}] {user}: {msg_text}")
                    #await message_queue.put({'user': user, 'message': msg_text})
                
                elif event_type == "":
                    pass

            elif mtype == "session_reconnect":
                new_url = data["payload"]["session"]["reconnect_url"]
                print("Reconnect to:", new_url)
                return await twitch_listener()  # Reconnect loop

async def process_messages(rate_per_second=1):
    if rate_per_second == -1:
        pass
    else:
        interval = 1 / rate_per_second
        while True:
            event = await message_queue.get()
            user = event['user']
            msg_text = event['message']

            # Here you can do anything with the message
            print(f"Processing message from {user}: {msg_text}")

            await asyncio.sleep(interval)  # Wait before processing next message

######### Title Functions #########

def insertSubs(subs):
    words = title.split()
    words.insert(insert_after, str(subs))
    new_title = " ".join(words)
    return new_title

def subs_logic(subs):
    mult = os.getenv("BASE_MULT")

    if subs == None:
        subs = BASE_SUBS

    if LINEAR == True:
        subs += BASE_SUBS
    elif LINEAR == False:
        subs = (subs * mult) // 1
    return subs

def update_title(auth: TwitchAuth ,channel_id: str, new_title: str):
    """Update the channel title using Twitch API."""
    headers = auth.get_headers()
    data = {"title": new_title}

    response = requests.patch(
        f"https://api.twitch.tv/helix/channels?broadcaster_id={channel_id}",
        headers=headers,
        json=data
    )
    
    if response.status_code == 204:
        print("Title updated successfully!")
    else:
        print(f"Failed to update title ({response.status_code}): {response.text}")

def update_title_loop(auth):
    print("Fetching channel ID...")
    channel_id = get_channel_id(BROADCASTER_USERNAME)
    print(f"Channel ID for '{BROADCASTER_USERNAME}': {channel_id}")
    
    subs = BASE_SUBS

    while True:
        print("Updating title...")
        print(subs)
        new_title = insertSubs(subs)
        update_title(auth, channel_id, new_title)
        print(f"Waiting {UPDATE_INTERVAL_MINUTES} minutes before next update...")
        time.sleep(UPDATE_INTERVAL_MINUTES * 60)
        subs += subs_logic(subs)
        if subs >= MAX_SUBS:
            subs == MAX_SUBS
            return