import configparser
import aio_pika
import asyncio
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
    print('Gateway Ready')
    channel = client.get_channel(int(sys.argv[1]))
    loop = asyncio.get_event_loop()
    def send():
        body = sys.stdin.readline()
        print(f"Send {body}")
        asyncio.create_task(channel.send(body))
    async def sendq(message: aio_pika.IncomingMessage):
        body = message.body
        print(f"Sendq {message}")
        asyncio.create_task(channel.send(body))
    task = loop.add_reader(sys.stdin.fileno(), send)

    connection = await aio_pika.connect_robust(
            "amqp://localhost/", loop=loop)
    print("Pika pika")
    async with connection:
        rabbit_channel = await connection.channel()
        queue = await rabbit_channel.declare_queue(sys.argv[2], durable=True, arguments={"x-message-ttl": 14400})
        await queue.consume(sendq, no_ack=False)
        print("Pika nom")
    pass

client.run(token)
