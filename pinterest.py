import aiohttp
import copy
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
    global board_cache
    username = args[0]
    boardname = " ".join(args[1:])
    cachekey = f"u:{username},b:{boardname}"
    try:
        board_entry = board_cache[cachekey].pop()
    except (IndexError, KeyError):
        await message.channel.trigger_typing()
        board_cache[cachekey] = copy.deepcopy(get_board(username, boardname))
        random.shuffle(board_cache[cachekey])
        board_entry = board_cache[cachekey].pop()
    logger.debug(board_entry)
    title = board_entry.get("grid_title", "")
    attribution = board_entry.get("attribution", {}) or {}
    author = attribution.get("author_name", "")
    url = board_entry.get("link", "")
    images = board_entry.get("images", {}) or {}
    orig = images.get("orig", {}) or {}
    orig_url = orig.get("url", "")
    embedPreview = discord.Embed(title=title, description=author, url=url,)
    embedPreview.set_footer(
        icon_url="http://download.nova.anticlack.com/fletcher/pinterest.png",
        text=f"On behalf of {message.author.display_name}",
    )
    embedPreview.set_image(url=orig_url)
    await messagefuncs.sendWrappedMessage(target=message.channel, embed=embedPreview)


@cached(TTLCache(1024, 600))
def get_boards(username):
    boards = []
    board_batch = pinterest.boards(username=username)
    while len(board_batch) > 0:
        boards += board_batch
        board_batch = pinterest.boards(username=username)
    return boards


@cached(TTLCache(1024, 600))
def get_feeds(board_id):
    board_feed = []
    feed_batch = pinterest.board_feed(board_id=board_id)
    while len(feed_batch) > 0:
        board_feed += feed_batch
        feed_batch = pinterest.board_feed(board_id=board_id)
    return board_feed


@cached(TTLCache(1024, 600))
def get_board(username, boardname):
    board_id = discord.utils.find(
        lambda b: b["name"] == boardname, get_boards(username)
    )["id"]
    return get_feeds(board_id)


def autoload(ch):
    global config
    global pinterest
    ch.add_command(
        {
            "trigger": ["!debug_prt"],
            "function": lambda message, client, args: get_boards(args[0]),
            "async": False,
            "admin": False,
            "hidden": True,
            "args_num": 1,
            "args_name": ["username"],
            "description": "Return a random image from the board specified",
        }
    )
    ch.add_command(
        {
            "trigger": ["!prt"],
            "function": pinterest_randomize_function,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 2,
            "args_name": ["username", "board"],
            "description": "Return a random image from the board specified",
        }
    )
    ch.add_command(
        {
            "trigger": ["!possum"],
            "function": lambda message, client, args: pinterest_randomize_function(
                message, client, ["jerryob1", "Opossums"]
            ),
            "async": True,
            "admin": False,
            "hidden": False,
            "args_num": 0,
            "args_name": ["username", "board"],
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
    # pinterest.login()


async def autounload(ch):
    pass
