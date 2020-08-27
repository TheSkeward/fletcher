import aiohttp
import discord
from py3pin.Pinterest import Pinterest
import io
import logging
import messagefuncs
import random
from sys import exc_info
import ujson

logger = logging.getLogger("fletcher")


async def pinterest_randomize_function(message, client, args):
    username = args[0]
    boards = []
    board_batch = pinterest.boards(username=username)
    while len(board_batch) > 0:
        boards += board_batch
        board_batch = pinterest.boards(username=username)
    await messagefuncs.sendWrappedMessage(ujson.dumps(boards), message.author)


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
