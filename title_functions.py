import os
import requests
import time
from twitch_functions import get_channel_id
from twitch_auth import TwitchAuth

BROADCASTER_USERNAME = (os.getenv("BROADCASTER_USERNAME"))
MAX_SUBS = os.getenv("MAX_SUBS")
UPDATE_INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES"))

#TODO: Needs better names
LINEAR = os.getenv("LINEAR")
title0 = os.getenv("Title0")
title1 = os.getenv("Title1")

BASE_SUBS = int(os.getenv("BASE_SUBS"))

def subs_logic(SUBS):
    mult = os.getenv("BASE_MULT")

    if SUBS == None:
        SUBS = BASE_SUBS

    if LINEAR == True:
        SUBS += BASE_SUBS
    elif LINEAR == False:
        SUBS = (SUBS * mult) // 1
    
    
    return SUBS

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

def update_title_loop():
    print("Fetching channel ID...")
    channel_id = get_channel_id(BROADCASTER_USERNAME)
    print(f"Channel ID for '{BROADCASTER_USERNAME}': {channel_id}")
    
    SUBS = BASE_SUBS

    while True:
        print("Updating title...")
        print(SUBS)
        NEW_TITLE = f"{title0} {SUBS} {title1}"  # Change to your desired title
        update_title(channel_id, NEW_TITLE)
        print(f"Waiting {UPDATE_INTERVAL_MINUTES} minutes before next update...")
        time.sleep(UPDATE_INTERVAL_MINUTES * 15)
        SUBS += subs_logic(SUBS)
        if SUBS >= MAX_SUBS:
            SUBS == MAX_SUBS
            return