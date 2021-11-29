import configparser
import json
import discord
import os
import sys

FLETCHER_CONFIG = os.getenv('FLETCHER_CONFIG', './.fletcherrc')

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents, chunk_guilds_at_startup=False)

# token from https://discordapp.com/developers
token = config['discord']['botToken']

@client.event
async def on_ready():
    try:
        argv = sys.argv
        if len(argv) > 1:
            argv[1] = int(argv[1])
            argv[2] = int(argv[2])
        guild = await client.fetch_guild(argv[1])
        await guild.chunk()
        channels = await guild.fetch_channels()
        channel = discord.utils.get(channels, id=argv[2])
        entries = []
        async for message in channel.history(limit=None, oldest_first=True):
            if message.raw_channel_mentions:
                entries.append({
                    "name": discord.utils.get(channels, id=message.raw_channel_mentions[0]).name,
                    "created": str(message.created_at),
                    "author": str(message.author),
                    "content": message.clean_content.replace(f'<#{message.raw_channel_mentions[0]}>', f'#{discord.utils.get(channels, id=message.raw_channel_mentions[0]).name}'),
                    "jump_url": message.jump_url
                    })
        print(json.dumps(entries))
    except Exception as e:
        print(e)
    await client.close()
client.run(token)
