import configparser
from aiohttp import web
import asyncio
import discord
import psycopg2
import asyncpraw
import os
import sys

sys.path.append(".")
import messagefuncs

FLETCHER_CONFIG = os.getenv("FLETCHER_CONFIG", "./.fletcherrc")

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

client = discord.Client(intents=discord.Intents.none())
# token from https://discordapp.com/developers
token = config["discord"]["botToken"]
thread = config["reddit"]["live_thread"] or sys.argv[1]
reddit = asyncpraw.Reddit(
    client_id=config["reddit"]["client_id"],
    client_secret=config["reddit"]["client_secret"],
    user_agent="Fletcher/0.1",
)

conn = psycopg2.connect(
    host=config["database"]["host"],
    database=config["database"]["tablespace"],
    user=config["database"]["user"],
    password=config["database"]["password"],
)

messagefuncs.conn = conn


@client.event
async def on_ready():
    cur = conn.cursor()
    while True:
        try:
            stream = (await reddit.live(thread)).stream
            last_live_update_body = ""
            print("Stream Time")
            async for live_update in stream.updates(skip_existing=True):
                if live_update.body == last_live_update_body:
                    next
                else:
                    last_live_update_body = live_update.body
                if not live_update.body:
                    next
                print(live_update)
                cur.execute(
                    "SELECT value, user_id FROM user_preferences WHERE key = %s;",
                    [thread],
                )
                for row in cur:
                    print(row)
                    try:
                        channel = client.get_channel(
                            int(row[0])
                        ) or await client.fetch_channel(int(row[0]))
                        await messagefuncs.sendWrappedMessage(
                            f"u/{live_update.author.name} via <https://www.redditmedia.com/live/{thread}/>\n> {live_update.body}",
                            channel,
                            current_user_id=row[1],
                        )
                    except Exception as e:
                        print(f"{type(e)}: {e}")
        except Exception as e:
            print(f"{type(e)}: {e}")
            pass
    await client.close()
    sys.exit(0)


client.run(token)
