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
guild_id = sys.argv.get(1, 630837856075513856)
channel_id = sys.argv.get(2, 677963073159430144)
message_id = sys.argv.get(3, 677964145358012417)
role_id = sys.argv.get(4, 677964299926372393)

@client.event
async def on_ready():
    message = await client.get_guild(guild_id).get_channel(channel_id).fetch_message(message_id)
    role = client.get_guild(guild_id).get_role(role_id)
    async for user in message.reactions[0].users():
        print(user)
        if type(user) == discord.User:
            print('User is GONE')
            continue
        if role not in user.roles:
            try:
                print(await user.add_roles(role))
            except Exception as e:
                print(e)
        else:
            print('Already has, skipping')
    await client.close()
    sys.exit(0)
    pass

client.run(token)
