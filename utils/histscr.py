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
        for channel in guild.text_channels:
            try:
                if len(argv) > 1 and guild.id != argv[1] and channel.id != argv[1]:
                    continue
                async for message in channel.history(limit=None):
                    print("{} {}:{} {} <{}>: {}".format(message.id, message.guild.name, message.channel.name, message.created_at, message.author.display_name, message.content))
                    for attachment in message.attachments:
                        print("{} Attachment: {}".format(message.id, attachment.url))
                    for reaction in message.reactions:
                        async for user in reaction.users():
                            print("{} from {}".format(str(reaction), str(user)))
            except discord.Forbidden as e:
                print("Not enough permissions to retrieve logs for {}:{}".format(guild.name, channel.name))
                pass
    await client.close()
client.run(token)
