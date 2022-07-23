import configparser
from io import BytesIO
import discord
import os
import sys

FLETCHER_CONFIG = os.getenv("FLETCHER_CONFIG", "./.fletcherrc")

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

client = discord.Client()

# token from https://discordapp.com/developers
token = config["discord"]["botToken"]


@client.event
async def on_ready():
    argv = sys.argv
    argv[1] = int(argv[1])
    argv[1] = client.get_channel(argv[1])
    argv[2] = int(argv[2])
    argv[2] = client.get_channel(argv[2])
    wh = await argv[2].webhooks()
    if len(wh):
        webhook = wh[0]
    else:
        webhook = await argv[2].create_webhook(name="Porting using Fletcher")
    print(dict(argv[2].permissions_for(argv[1].guild.get_member(client.user.id))))
    messages = (
        argv[1].history(
            limit=None,
            oldest_first=True,
            after=await argv[1].fetch_message(int(argv[3])),
        )
        if len(argv) > 3
        else argv[1].history(limit=None, oldest_first=True)
    )
    async for message in messages:
        print(f"Syncing message ID {message.id}")
        attachments = []
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                attachment_blob = BytesIO()
                await attachment.save(attachment_blob)
                attachments.append(discord.File(attachment_blob, attachment.filename))
        local_author = webhook.guild.get_member(message.author.id)
        author = local_author or message.author
        try:
            await webhook.send(
                content=message.content,
                username=author.display_name,
                avatar_url=author.display_avatar,
                embeds=message.embeds,
                tts=message.tts,
                files=attachments,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False
                ),
                wait=True,
            )
        except discord.errors.HTTPException as e:
            print(e)
            pass
    await client.close()


client.run(token)
