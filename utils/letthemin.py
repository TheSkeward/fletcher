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
    message = await client.get_guild(sys.argv.get(1, 630487117688078358)).get_channel(sys.argv.get(2, 631197469497360415)).fetch_message(sys.argv.get(3, 717173524925644870))
    target_channel = message.guild.get_channel(sys.argv.get(4, 717170421979676712))
    for reaction in message.reactions:
        async for user in reaction.users():
            if user.id in [336572756705673226, 429368441577930753, 382984420321263617] or target_channel.permissions_for(user).read_messages:
                pass
            else:
                print(user)
                await target_channel.set_permissions(user, read_messages=True)

    await client.close()
client.run(token)
