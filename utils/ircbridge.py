import configparser
import discord
from typing import Optional
import asyncio

from irclib.parser import Message
from asyncirc.protocol import IrcProtocol
from asyncirc.server import Server
import re
import textwrap

import os

FLETCHER_CONFIG = os.getenv("FLETCHER_CONFIG", "./.fletcherrc")

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

servers = [
    Server(
        config["irc"]["server"],
        int(config["irc"]["port"]),
        bool(config["irc"]["ssl"]),
        password=config["irc"]["password"],
    ),
]

intents = discord.Intents.all()
intents.presences = False
client = discord.Client(intents=intents, chunk_guilds_at_startup=False)

# token from https://discordapp.com/developers
token = config["discord"]["botToken"]

g: discord.Guild
c: discord.CategoryChannel
conn: IrcProtocol

main_buffer: str = ""


@client.event
async def on_ready():
    print("Discord Ready")
    global g
    global c
    global conn
    global main_buffer
    g = client.get_guild(634249282488107028)
    print("Chunking...", end="", flush=True)
    await g.chunk()
    print("done!")
    c = g.get_channel(996963385562374147)
    n = discord.utils.get(c.channels, name="main")
    conn = IrcProtocol(servers, config["irc"]["user"], loop=asyncio.get_event_loop())
    conn.register_cap("userhost-in-names")
    conn.register("*", log)
    print("Connecting to IRC...", end="", flush=True)
    await conn.connect()
    print("done!")
    while True:
        if main_buffer:
            for chunk in textwrap.wrap(
                str(main_buffer), 1999, replace_whitespace=False
            ):
                await n.send(chunk)
                await asyncio.sleep(1)
            main_buffer = ""
        await asyncio.sleep(1)


@client.event
async def on_message(message):
    try:
        g
    except NameError:
        return
    if (
        message.guild
        and message.guild.id == g.id
        and message.channel.category
        and message.channel.category.id == c.id
        and message.author.id != client.user.id
    ):
        if message.channel.name == "main":
            conn.send(message.clean_content)
        elif message.channel.name.startswith("＠"):
            for line in message.clean_content.splitlines() + [
                a.url for a in message.attachments
            ]:
                msg = f"PRIVMSG {message.channel.name.removeprefix('＠')} :{line}"
                conn.send(msg)
        else:
            name = (
                message.channel.name.replace("⌗", "#", 1)
                if message.channel.name.startswith("⌗")
                else message.channel.name
            )
            for line in message.clean_content.splitlines() + [
                a.url for a in message.attachments
            ]:
                msg = f"PRIVMSG #{name} :{line}"
                conn.send(msg)


@client.event
async def on_guild_channel_delete(channel):
    try:
        g
    except NameError:
        return
    if (
        channel.guild
        and channel.guild.id == g.id
        and channel.category
        and channel.category.id == c.id
        and not channel.name.startswith("＠")
    ):
        name = (
            channel.name.replace("⌗", "#", 1)
            if channel.name.startswith("⌗")
            else channel.name
        )
        conn.send(f"PART #{name}")


@client.event
async def on_guild_channel_create(channel):
    try:
        g
    except NameError:
        return
    if (
        channel.guild
        and channel.guild.id == g.id
        and channel.category
        and channel.category.id == c.id
        and not channel.name.startswith("＠")
    ):
        name = (
            channel.name.replace("⌗", "#", 1)
            if channel.name.startswith("⌗")
            else channel.name
        )
        conn.send(f"JOIN #{name}")


three_seven_six_sent = False


async def log(conn, msg):
    global c
    global three_seven_six_sent
    global main_buffer
    if msg.command in ("PONG", "JOIN", "MODE", "PART"):
        return
    target: Optional[discord.TextChannel] = None
    if msg.parameters:
        if msg.command == "332":
            n = 1
        else:
            n = 0
        name = (
            msg.parameters[n].removeprefix("#").replace("#", "⌗", 1)
            if msg.parameters[n].startswith("#")
            else (("＠" + msg.prefix.nick) if msg.prefix else "main")
        )
        target = next((c for c in c.text_channels if c.name == name), None)
        if not target and name.startswith("＠") and msg.command == "PRIVMSG":
            target = await c.create_text_channel(name)
        elif not target:
            target = next((c for c in c.text_channels if c.name == "main"), None)
    if (
        msg.parameters
        and target
        and msg.command not in ["332", "QUIT"]
        and three_seven_six_sent
    ):
        send_buffer = ""
        if msg.command in ["PRIVMSG", "NOTICE"]:
            nick = f"{msg.prefix.nick} " if not target.name.startswith("＠") else ""
            content = msg.parameters[1].strip("\x01")
            content = re.sub(
                r"\x03(?:\d{1,2}(?:,\d{1,2})?)?", "", content, flags=re.UNICODE
            )
            if content.lstrip().startswith("ACTION"):
                action = content.lstrip().removeprefix("ACTION ")
                send_buffer = f"_{nick}{action}_"
            elif msg.command == "NOTICE":
                if nick:
                    nick = "<" + nick[:-1] + "> "
                notice = content.lstrip().removeprefix("NOTICE ")
                send_buffer = f"{nick}**{notice}**"
            else:
                if nick:
                    nick = "<" + nick[:-1] + "> "
                send_buffer = f"{nick}{content}"
        else:
            send_buffer = str(msg)
        if send_buffer and target.name == "main":
            main_buffer += "\n" + send_buffer
        elif send_buffer:
            await target.send(send_buffer)
    if msg.command == "332" and target:
        await target.edit(topic=msg.parameters[2])
    if msg.command == "376":
        three_seven_six_sent = True
        conn.send(f"PRIVMSG NickServ :IDENTIFY {config['irc']['password']}")
        await asyncio.sleep(1)
        joins = []
        for channel in c.text_channels:
            if channel.name != "main" and not channel.name.startswith("＠"):
                name = (
                    channel.name.replace("⌗", "#", 1)
                    if channel.name.startswith("⌗")
                    else channel.name
                )
                joins.append(f"#{name}")
        join_cmd = f"JOIN {','.join(joins)}"
        print(join_cmd)
        conn.send(join_cmd)


client.run(token)
