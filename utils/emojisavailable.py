import configparser
import json
import discord
import os
import sys

FLETCHER_CONFIG = os.getenv("FLETCHER_CONFIG", "./.fletcherrc")

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents, chunk_guilds_at_startup=False)

# token from https://discordapp.com/developers
token = config["discord"]["botToken"]


@client.event
async def on_ready():
    print(
        "<ul>"
        + "".join(
            [
                f"<li><img src='{emoji.url_as()}' style='height:2em; width:2em' loading='lazy' />{emoji.name}</li>"
                for emoji in client.emojis
                if emoji.is_usable()
            ]
        )
        + "</ul>"
    )
    await client.close()


client.run(token)
