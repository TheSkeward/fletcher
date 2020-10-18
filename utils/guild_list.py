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

@client.event
async def on_ready():
    argv = sys.argv
    if len(argv) > 1:
        argv[1] = int(argv[1])
    for guild in client.guilds:
        print(f'{guild.name} {guild.id}')
        print(f'{guild.text_channels[0].overwrites}')
    await client.close()
client.run(token)
