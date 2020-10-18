import configparser
import discord
import os
import sys

FLETCHER_CONFIG = os.getenv('FLETCHER_CONFIG', './.fletcherrc')

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

client = discord.Client()
# token from https://discordapp.com/developers
token = config['discord']['botToken']

Ans = None

@client.event
async def on_ready():
    await client.get_channel(int(sys.argv[1])).send(sys.argv[2])
    await client.logout()
    pass

client.run(token)
