Host (the person who creates the room)

Unzip the P2P_Chess.zip to a folder (e.g., Desktop\P2P_Chess).
You should see: P2Pchess.exe, signal_server.exe, Host-Game.bat, Join-Game.bat, Start-Server.bat.

Start the relay (signaling) server

Double-click Start-Server.bat.

A small black window appears and says something like:
Running on http://0.0.0.0:8080

Leave this window open while you play.

If Windows asks about firewall access, click Allow (both Private & Public).

Start the game as host

Double-click Host-Game.bat.

In the game window, press H for Host.

You’ll see a ROOM CODE (e.g., KGZOJ). Keep that window open.

Tell your friend two things

Your IP address for the signaling server (see below).

The ROOM CODE the game shows.

Which IP should you give?

Same Wi-Fi / LAN: your local IPv4 (open Command Prompt → ipconfig → find “IPv4 Address”, usually 192.168.x.x).

Over the internet: your public IP (google “what is my ip”).

Port is 8080 (already handled by the .bat files).

Make sure your firewall/router lets inbound TCP on 8080 to your PC (you may need to allow it the first time).

Wait for your friend to join. When they connect, you’ll both see “Connected” and the board. Play!

When done, close the game and then close the server window.

Joiner (the person who connects)

Unzip the P2P_Chess.zip somewhere (e.g., Desktop\P2P_Chess).

Start the game as joiner

Double-click Join-Game.bat.

It will ask for the host’s IP. Type the IP the host sent you (just the numbers/hostname, no http://, no port). Press Enter.

The game opens. Press J for Join.

Enter the ROOM CODE the host gave you (e.g., KGZOJ).

If Windows asks about firewall access, click Allow (both Private & Public).

You should see “Connected” and then the chess board. Play!

Quick Troubleshooting (super short)

Stuck on “Waiting for peer…”

Joiner: double-check you entered the host’s IP (numbers only).

Host: make sure Start-Server.bat is still running and firewall allowed it.

If you’re on different networks, the host might need to allow/forward port 8080 on their router.

We connect but the board never appears / disconnects

Try again; close both apps and start from step 2.

Different networks can be picky; if it keeps failing, try playing while you’re on the same Wi-Fi to verify everything works.

That’s it. Two double-clicks for the host, one for the joiner + room code & IP.