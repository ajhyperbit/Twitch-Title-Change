import os
from dotenv import load_dotenv
import asyncio
from twitch_functions import *
from twitch_auth import TwitchAuth
from scopes import SCOPES
#from chat import main_chat

load_dotenv()

# Variables
BASE_SUBS = int(os.getenv("BASE_SUBS"))
BOT_USERNAME = (os.getenv("BOT_USERNAME"))
BROADCASTER_USERNAME = (os.getenv("BROADCASTER_USERNAME"))
#For messages event sub
TWITCH_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
TWITCH_API_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"

BROADCASTER_ID = get_channel_id(BROADCASTER_USERNAME)
auth = TwitchAuth(scopes=SCOPES, broadcaster_id=BROADCASTER_ID)

#def main():
#    #print(auth.get_headers())
#    auth.get_valid_token(validate=True)
#    #update_title_loop()
#    #asyncio.run(main_chat())
#    asyncio.run(twitch_listener(auth))


async def main(auth):
    consumer_task = asyncio.create_task(process_messages(rate_per_second=1))
    listener_task = asyncio.create_task(twitch_listener(auth))
    
    await asyncio.gather(listener_task, consumer_task)

# Run with your auth object
# asyncio.run(main(auth))


if __name__ == "__main__":
    asyncio.run(main(auth))
