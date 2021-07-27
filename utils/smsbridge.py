import asyncio
from quart import Quart, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import configparser
import json
import discord
import os
import sys

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_from = os.environ['TWILIO_FROM']
twilio_to = os.environ['TWILIO_TO']
twilio = Client(account_sid, auth_token)

app = Quart(__name__)

FLETCHER_CONFIG = os.getenv('FLETCHER_CONFIG', './.fletcherrc')

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
# token from https://discordapp.com/developers
token = config['discord']['botToken']

global last_channel
@client.event
async def on_message(message):
    global last_channel
    if message.author == client.user:
        return
    if message.guild and message.guild.id in [843952851050430475]:
        body = f"#{message.channel.name} <{message.author.display_name}> {message.clean_content}"
        for attachment in message.attachments:
            body += "\n{attachment.url}"
        twilio.messages.create(
                body=body,
                from_=TWILIO_FROM,
                to=TWILIO_TO
                )
        last_channel = message.channel
        print(body)

loop = asyncio.get_event_loop()
@client.event
async def on_ready():
    print("Ready")
    last_channel = client.get_channel(843952851050430477)
    pass

@app.route("/sms", methods=['GET', 'POST'])
async def sms_reply():
    """Respond to incoming calls with a simple text message."""
    global last_channel
    body = (await request.form).get('Body', "")
    if body.startswith("#"):
        channel_name = body.split(" ", 1)[0][1:]
        body = body.split(" ")[1]
        last_channel = discord.utils.get(client.get_guild(843952851050430475).text_channels, name=channel_name)
    await last_channel.send(f"> <Kaepricorn> {body}")
    return ("", 204)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_task(port=2304))
    client.run(token)
