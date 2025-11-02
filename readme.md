To download:
```
git clone -b title-change-code --single-branch https://github.com/ajhyperbit/Twitch-Projects.git
```

If you need to install python, you can install it from the Microsoft store if you are on Windows:
Instructions here:
https://realpython.com/installing-python/#windows-how-to-install-python-from-the-microsoft-store

Next:

To get a client ID and secret go to:
https://dev.twitch.tv/console/apps/create

Name the Application whatever you want, personally I named mine AJAPInterface

OAuth Redirect URLs must be: `http://localhost:8090`

Category: `Website Integration`

Client Type: `Confidential`

After that, run twitch_generate_token.py, authorize in the browser window that pops up
That should populate a twitch_token.json within the same directory

Some of these instructions are repeated in .envexample
But there are more instructions in there too

P.S. I personally use NixOS, which is why shell.nix and .envrc exist. Those two files can be safely ignored if you are not making use of Nix