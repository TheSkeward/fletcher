import configparser
import datetime
import discord
import json
import os
import sys

FLETCHER_CONFIG = os.getenv('FLETCHER_CONFIG', './.fletcherrc')

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

client = discord.Client(intents=discord.Intents.all(), chunk_guilds_at_startup=False)

# token from https://discordapp.com/developers
token = config['discord']['botToken']

@client.event
async def on_ready():
    argv = sys.argv
    guild = None
    if len(argv) > 1:
        argv[1] = int(argv[1])
        guild = client.get_guild(argv[1])
        await guild.chunk()
    users_last = {}
    for user in guild.members:
        users_last[user.id] = [user.name, None]
        if not os.getenv('FLETCHER_LOG_LEVEL', 0):
            print(users_last[user.id])
    today = datetime.datetime.today()

    if today.month == 1:
        two_month_ago = today.replace(year=today.year - 1, month=11)
    elif today.month == 2:
        two_month_ago = today.replace(year=today.year - 1, month=12)
    else:
        extra_days = 0
        while True:
            try:
                two_month_ago = today.replace(month=today.month - 2, day=today.day - extra_days)
                break
            except ValueError:
                extra_days += 1

    i = 0
    for channel in guild.text_channels:
        try:
            i += 1
            if not os.getenv('FLETCHER_LOG_LEVEL', 0):
                print(f'{channel.name} {i}/{len(guild.text_channels)}')
            async for message in channel.history(limit=None, after=two_month_ago):
                if users_last.get(message.author.id) is None:
                    users_last[message.author.id] = [message.author.name, None]
                if users_last.get(message.author.id) and users_last[message.author.id][1] is None or users_last[message.author.id][1] < message.created_at:
                    users_last[message.author.id][1] = message.created_at
        except discord.Forbidden as e:
            if not os.getenv('FLETCHER_LOG_LEVEL', 0):
                print("Not enough permissions to retrieve logs for {}:{}".format(guild.name, channel.name))
            pass
    for key in users_last.keys():
        users_last[key][1] = str(users_last[key][1])
    print(json.dumps(users_last))
    await client.close()
client.run(token)
