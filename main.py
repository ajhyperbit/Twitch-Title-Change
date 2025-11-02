import time
import requests
import os
from twitch_auth import get_headers

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
        print(f".env file '{filepath}' not found.")

load_dotenv()

# Variables
BROADCASTER_USERNAME = (os.getenv("BROADCASTER_USERNAME"))
BASE_SUBS = int(os.getenv("BASE_SUBS"))
UPDATE_INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES"))

LINEAR = os.getenv("LINEAR")

#TODO: Needs better names
title0 = os.getenv("Title0")
title1 = os.getenv("Title1")

# Functions
def subs_logic(SUBS):
    mult = os.getenv("BASE_MULT")

    if SUBS == None:
        SUBS = BASE_SUBS

    if LINEAR == True:
        SUBS += BASE_SUBS
    elif LINEAR == False:
        SUBS = (SUBS * mult) // 1
    
    
    return SUBS

def get_channel_id(username: str) -> str:
    """Fetch the broadcaster's user ID (channel ID) from their username."""
    headers = get_headers()
    params = {"login": username}
    response = requests.get("https://api.twitch.tv/helix/users", headers=headers, params=params)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch user ID: {response.status_code} {response.text}")
    
    data = response.json()
    if not data["data"]:
        raise ValueError(f"No user found with username '{username}'")
    
    return data["data"][0]["id"]

def update_title(channel_id: str, new_title: str):
    """Update the channel title using Twitch API."""
    headers = get_headers()
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

def main():
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
        if SUBS >= 100:
            SUBS == 100
            return

if __name__ == "__main__":
    main()
