To download:
```
git clone https://github.com/ajhyperbit/Twitch-Projects.git
```

If you need to install python, you can install it from the Microsoft store if you are on Windows:
Instructions here:
https://realpython.com/installing-python/#windows-how-to-install-python-from-the-microsoft-store

Next:

To get a client ID and secret go to:
https://dev.twitch.tv/console/apps/create
Name it whatever you want
OAuth Redirect URLs must be:
http://localhost:8090
Category: Website Integration
Client Type: Confidential

After that, copy the .envexample into a .env, change all the relevant variables
Once you do that, run main.py and. Authorize the connection to your account in the browser window that pops up.
That should populate a twitch_token.json within the same directory (if it has number like `twitch_token-124213.json` that is fine and intended.)
Variables are mostly documented in the .envexample