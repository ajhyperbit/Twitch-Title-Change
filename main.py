import os
from dotenv import load_dotenv
import asyncio
from twitch_functions import twitch_listener
from twitch_auth_code import TwitchAuth

scopes = (os.getenv("SCOPES"))

load_dotenv()

# Variables
BASE_SUBS = int(os.getenv("BASE_SUBS"))
BOT_USERNAME = (os.getenv("BOT_USERNAME"))
#For messages event sub
TWITCH_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
TWITCH_API_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"

SCOPES = [
    "bits:read",
    "channel:bot",
    "channel:manage:broadcast",
    "channel:manage:clips",
    "channel:read:goals",
    "channel:read:hype_train",
    "channel:read:polls",
    "channel:manage:polls",
    "channel:read:predictions",
    "channel:manage:predictions",
    "channel:manage:raids",
    "channel:read:redemptions",
    "channel:read:subscriptions",
    "channel:read:vips",
    "channel:moderate",
    #"moderation:read",
    #"moderator:manage:announcements",
    #"moderator:manage:automod",
    #"moderator:read:automod_settings",
    #"moderator:manage:automod_settings",
    #"moderator:read:banned_users",
    #"moderator:manage:banned_users",
    #"moderator:read:blocked_terms",
    #"moderator:read:chat_messages",
    #"moderator:manage:blocked_terms",
    #"moderator:manage:chat_messages",
    #"moderator:read:chat_settings",
    #"moderator:manage:chat_settings",
    #"moderator:read:chatters",
    #"moderator:read:followers",
    #"moderator:read:guest_star",
    #"moderator:read:moderators",
    #"moderator:read:shoutouts",
    #"moderator:manage:shoutouts",
    #"moderator:read:suspicious_users",
    #"moderator:read:unban_requests",
    #"moderator:manage:unban_requests",
    #"moderator:read:vips",
    #"moderator:read:warnings",
    #"moderator:manage:warnings",
    "user:bot",
    "user:edit",
    "user:read:chat",
    "user:manage:chat_color",
    "user:read:emotes",
    "user:read:follows",
    "user:read:moderated_channels",
    "user:read:subscriptions",
    "user:read:whispers",
    "user:manage:whispers",
    "user:write:chat"
]

auth = TwitchAuth(scopes=SCOPES)

def main():
    auth.get_valid_token()
    #update_title_loop()
    asyncio.run(twitch_listener())

if __name__ == "__main__":
    main()
