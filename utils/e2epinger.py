import asyncio
from collections import deque
from datetime import datetime, timedelta
import configparser
import discord
from math import ceil
import re
import logging
from aiolimiter import AsyncLimiter

ping_throttler = AsyncLimiter(1, 5)


logging.basicConfig(level=logging.INFO)


import os

global intended_channel
global t0
global t1

FLETCHER_CONFIG = os.getenv("FLETCHER_CONFIG", "/pub/lin/.harvestmanrc")

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

# token from https://discordapp.com/developers
token = config.get("discord", "botToken")

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
client = discord.Client(chunk_guilds_at_startup=False, intents=intents)

t0 = datetime.now()


@client.event
async def on_ready():
    global intended_channel
    global t0
    intended_channel = await client.fetch_thread(1188600413503619175)
    t0 = datetime.now()
    assert isinstance(intended_channel, discord.Thread)
    async with ping_throttler:
        await intended_channel.send("!ping")


global last_received_message
last_received_message = datetime.now()

global all_latencies
all_latencies: deque[dict] = deque(maxlen=60 * 10)


def plot():
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib import dates as mdates
    from io import BytesIO

    # Extract data
    times = [p["sent_time"] for p in all_latencies]
    received = [p["received_latency"].microseconds / 1000 for p in all_latencies]
    reply = [p["reply_sent_latency"].microseconds / 1000 for p in all_latencies]
    e2e = [p["e2e_latency"].microseconds / 1000 for p in all_latencies]

    # Plot setup
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title("Latency Metrics", fontsize=18, fontweight="bold")
    ax.set_facecolor("#E6E6E6")
    ax.grid(color="white", linestyle="solid")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    n = len(times)
    tick_space = ceil(n / 10)
    ax.set_xticks(times[::tick_space])

    # Plot data
    ax.plot(times, received, "-o", markersize=4, linewidth=2, label="Received")
    ax.plot(times, reply, "-o", markersize=4, linewidth=2, label="Reply")
    ax.plot(times, e2e, "-o", color="r", markersize=4, linewidth=3, label="End-to-End")

    p99_received = np.percentile(received, 99)
    p50_received = np.percentile(received, 50)

    p99_reply = np.percentile(reply, 99)
    p50_reply = np.percentile(reply, 50)

    p99_e2e = np.percentile(e2e, 99)
    p50_e2e = np.percentile(e2e, 50)

    # Received bars
    ax.hlines(p99_received, times[0], times[-1], colors="C0", linestyles="dashed")
    ax.hlines(p50_received, times[0], times[-1], colors="C0")

    # Reply bars
    ax.hlines(p99_reply, times[0], times[-1], colors="C1", linestyles="dashed")
    ax.hlines(p50_reply, times[0], times[-1], colors="C1")

    # E2E bars
    ax.hlines(p99_e2e, times[0], times[-1], colors="C2", linestyles="dashed")
    ax.hlines(p50_e2e, times[0], times[-1], colors="C2")

    # Styling
    ax.set_ylabel("Latency (ms)", fontsize=14)
    ax.legend(loc="upper left")
    fig.tight_layout()

    # Save figure to bytesio in PNG format
    buffer = BytesIO()
    plt.savefig(buffer, format="png")

    # Seek back to start of buffer
    buffer.seek(0)

    return buffer


@client.event
async def on_message(message: discord.Message):
    global intended_channel
    global t0
    global t1
    global last_received_message
    if not message.author.bot and intended_channel == message.channel:
        return await message.author.send(
            files=[discord.File(plot(), filename="graph.png")]
        )
    if intended_channel != message.channel or (message.author.id == client.user.id):
        return
    last_received_message = datetime.now()
    t1 = datetime.now()
    # logging.info(message.content)
    # Message was sent at 2023-08-23 02:39:24.221000, received at 2023-08-23 02:39:24.252284 (31.284 ms), reply sent at 2023-08-23 02:39:24.253650 (1.366 ms). Pong!
    pattern = r"received at (?:[\d\.: -]+)\s+\(([0-9.]+)\sms\)\, reply sent at (?:[\d\.: -]+)\s+\(([0-9.]+)\sms\)"

    match = re.search(pattern, message.content)

    received_latency = timedelta(seconds=float(match.group(1)) / 1000)
    reply_sent_latency = timedelta(seconds=float(match.group(2)) / 1000)
    e2e_latency = t1 - t0

    logging.info(f"{received_latency=}, {reply_sent_latency=}, {e2e_latency=}")
    all_latencies.append(
        dict(
            sent_time=t0,
            received_latency=received_latency,
            reply_sent_latency=reply_sent_latency,
            e2e_latency=e2e_latency,
        )
    )
    assert isinstance(intended_channel, discord.TextChannel)
    while True:
        async with ping_throttler:
            t0 = datetime.now()
            await intended_channel.send("!ping")
        await asyncio.sleep(60)
        if datetime.now() - last_received_message > timedelta(seconds=10):
            break


client.run(token)
