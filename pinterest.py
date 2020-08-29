import aiohttp
import discord
from py3pin.Pinterest import Pinterest
import io
import logging
import messagefuncs
import random
from sys import exc_info
import ujson
from cachetools import cached, TTLCache

logger = logging.getLogger("fletcher")

board_cache = {}


async def pinterest_randomize_function(message, client, args):
    username = args[0]
    boardname = " ".join(args[1:])
    cachekey = f"u:{username},b:{boardname}"
    board = board_cache.get(cachekey)
    if board is None or not len(board):
        board_cache[cachekey] = get_board(username, boardname)
        random.shuffle(board_cache[cachekey])
    board_entry = board_cache[cachekey].pop()
    embedPreview = discord.Embed(
        title=board_entry["grid_title"],
        description=board_entry.get("attribution", dict()).get("author_name", ""),
        url=board_entry.get("link", "")
    )
    embedPreview.set_footer(
        icon_url="http://download.nova.anticlack.com/fletcher/pinterest.png",
        text=f"On behalf of {message.author.display_name}",
    )
    embedPreview.set_thumbnail(url=board_entry["images"]["orig"]["url"])
    await message.channel.send(embed=embedPreview)


@cached(TTLCache(1024, 600))
def get_board(username, boardname):
    boards = []
    board_batch = pinterest.boards(username=username)
    while len(board_batch) > 0:
        boards += board_batch
        board_batch = pinterest.boards(username=username)
    board_id = discord.utils.find(lambda b: b["name"] == boardname, boards)["id"]
    board_feed = []
    feed_batch = pinterest.board_feed(board_id=board_id)
    while len(feed_batch) > 0:
        board_feed += feed_batch
        feed_batch = pinterest.board_feed(board_id=board_id)
    return board_feed


def autoload(ch):
    global config
    global pinterest
    ch.add_command(
        {
            "trigger": ["!prt"],
            "function": pinterest_randomize_function,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 1,
            "args_name": [],
            "description": "Return a random image from the board specified",
        }
    )
    # for guild in ch.guilds:
    #     for ch.config.get(guild=guild, section="pinterest"):
    pinterest = Pinterest(
        email=ch.config.get(section="pinterest", key="email"),
        password=ch.config.get(section="pinterest", key="password"),
        username=ch.config.get(section="pinterest", key="username"),
        cred_root=ch.config.get(section="pinterest", key="tmpdir"),
    )
    pinterest.login()


async def autounload(ch):
    pass
