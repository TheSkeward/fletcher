## Minecraft chat bridging
The needed configuration for bridging the chat of a Minecraft server to a Discord channel.
There are two parts to this function - sending messages from the Discord channel to Minecraft using RCON (the Minecraft remote connection protocol), and watching the logs of the server for new in-game chat messages to send to Discord. The Channel Configuration section details the first part, while the Script section details the second.

#### Channel Configuration
The "Preferences" table for the channel you wish to bridge the Minecraft chat to (Add Section > enter the Channel ID on your server's configuration panel at https://fletcher.fun ) should look like this:

| Key                    |  Value |
| -----------------------|-----------|
| remote\_ip              | [server IP] |
| minecraft\_host         | [server IP] |
| bridge\_function        | `!minecraftsendsay` |
| minecraft\_rcon-port    | [MC server port number (rcon.port in `server.properties`)] |
| minecraft\_rcon-password| [MC server RCON password (rcon.password in `server.properties`. This will display as three stars after you set it)] |

Preferences apply aproximately four times per hour, so it may take some time before this takes effect.

### Script
NOTE: Some of the values in this script are example values and will need to be replaced. In particular, replace all of the `guild_id`s and `channel_id`s with your actual values. This script assumes that you are using PaperMC which has an Asynchronous Chat Thread. Store this in a file called `minecraft-forward-bridge.sh` in the same directory as your `server.properties` file.

```
#!/bin/bash
while true;
do
    echo "Running..."
    echo "Server Name Minecraft Bridge connected" | perl -MJSON -pe 's/^.*?: //; chomp; $_ = "curl -4 https://fletcher.fun:25586/ --data '\''".(encode_json {"guild_id" => 843952851050430475, "channel_id" => 843952851050430478, "message" => "> $_", "rcon-password" => "'$(fgrep rcon.password server.properties | cut -f 2 -d =)'"}) . "'\'' -H '\''Content-Type: application/json'\'' -m 5 --connect-time 5 -D - \n"; system $_;'
    tail -n 1 -F /path/to/logs/latest.log | fgrep -e 'left the game' -e 'Async Chat Thread' -e 'Server thread/INFO' -e 'logged in' -e ' has made the advancement' -e 'went up in flames' -e 'burned to death' -e 'tried to swim in lava' -e 'suffocated in a wall' -e 'drowned' -e 'starved to death' -e 'was pricked to death' -e 'hit the ground too hard' -e 'fell out of the world' -e 'died' -e 'blew up' -e 'was killed by magic' -e 'was slain by' -e 'was slain by' -e 'was shot by' -e 'was fireballed by' -e 'was pummeled by' -e 'was killed by' --line-buffer | fgrep -ve ': Modified entity data' -e 'issued server command: /tell' -e 'issued server command: /msg' -e 'issued server command: /w' -e 'issued server command: /data' -e Rcon -e 'lost connection: Disconnected' -e 'joined the game' --line-buffer | perl -MJSON -pe 'BEGIN{$|=1} s/\[\/[0-9:.]*\] logged in.*/ logged in/; s/^.*?: //; s/[\x27"]//g; chomp; $_ = "curl -4 https://fletcher.fun:25586/ --data '\''".(encode_json {"guild_id" => 843952851050430475, "channel_id" => 843952851050430478, "message" => "> $_", "rcon-password" => "'$(fgrep rcon.password server.properties | cut -f 2 -d =)'"}) . "'\'' -H '\''Content-Type: application/json'\'' -m 5 --connect-time 5 -D - \n"; system $_;'
    echo "Restarting due to error..."
done
```

#### SystemD configuration
This section requires technical knowledge to implement. You can get some of that knowledge at https://wiki.archlinux.org/title/Systemd. If your server is running a non-Linux operating system, you will need to launch the script above differently.

NOTE: This systemd configuration is an example and will need to be edited to suit the circumstances of the individual user. Also included is a service for starting your minecraft server - this is for reference only, and is not required to be used. Replace `minecraft.service` in `minecraft-bridge.service` with the correct service file name to automatically start this service after your minecraft server starts.

Replace `User=opc` with the an unprivileged user that has access to your server's log directories (the one you use to launch minecraft should be fine). Replace `WorkingDirectory=/srv/mc` with the actual directory that your minecraft server lives in. You can enable a SystemD service using a command like `sudo systemctl daemon-reload; sudo systemctl enable --now minecraft-bridge.service`.

`/etc/systemd/system/minecraft-bridge.service`

```
[Unit]
Description=Minecraft (Bridge)
After=network.target auditd.service minecraft.service

[Service]
User=opc
WorkingDirectory=/srv/mc
ExecStart=/bin/sh minecraft-bridge.sh
KillMode=control-group
Restart=on-failure
RestartPreventExitStatus=255
Type=simple

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/minecraft.service`

```
[Unit]
Description=Minecraft
After=network.target auditd.service

[Service]
User=opc
WorkingDirectory=/srv/mc
ExecStart=/usr/bin/java -Xms8G -Xmx8G -jar paper-1.17.1-278.jar --nogui

KillMode=process
Restart=on-failure
RestartPreventExitStatus=255
Type=simple

[Install]
WantedBy=multi-user.target
```

