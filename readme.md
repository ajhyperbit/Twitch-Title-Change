To download:
```
git clone https://github.com/ajhyperbit/Twitch-Projects.git
```

If you need help installing python, refer here:
https://realpython.com/installing-python/

Next:

To get a client ID and secret go to:
https://dev.twitch.tv/console/apps/create
Name it whatever you want
OAuth Redirect URLs must be:
http://localhost:8090
Category: Website Integration
Client Type: Confidential

After you have python installed, ensure you have all the neccesary dependancies by running
```
pip install -r requirements.txt
```

After that, copy the contents of `.envexample` into a `.env`, change all the relevant variables
Once you do that, run `main.py` and. Authorize the connection to your account in the browser window that pops up.
That should populate a `twitch_token.json` within the same directory (if it has number like `twitch_token-124213.json` that is fine and intended.)
Variables are mostly documented in the `.envexample`