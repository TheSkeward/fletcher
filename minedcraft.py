from mcipc.rcon import Client
import copy
import discord
import ujson
import urllib.parse
import aiohttp
import messagefuncs
import socket
from dataclasses import dataclass
from dacite import from_dict
from sys import exc_info
from typing import List, Dict, Optional

import logging

logger = logging.getLogger("fletcher")

sessions = {}


@dataclass(kw_only=True)
class StackScript:
    @dataclass(kw_only=True)
    class UDF:
        name: str
        label: str
        default: str
        manyof: Optional[str] = None  # comma separated

    id: int
    label: str
    description: str
    script: str
    user_defined_fields: List[UDF]

    def __str__(self):
        return f"""
__{self.label} ({self.id})__
*{self.description}*
Parameters: {", ".join((udf.name for udf in self.user_defined_fields))}
```bash
{self.script}
```
"""


class LinodeAPI:
    session: aiohttp.ClientSession
    base_url: str = "https://api.linode.com/v4"
    headers: Dict[str, str]

    def __init__(self, token: str):
        self.session = aiohttp.ClientSession()
        self.headers = {
            "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
            "Authorization": f"Bearer {token}",
        }

    @classmethod
    def url_generator(cls, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return cls.base_url + path

    async def list_stackscripts(self, mine: bool = True) -> List[StackScript]:
        headers = copy.deepcopy(self.headers)
        filter_body = {"+order_by": "deployments_total", "+order": "desc", "mine": mine}
        headers["X-Filter"] = ujson.dumps(filter_body)
        async with self.session.get(
            type(self).url_generator("/linode/stackscripts"),
            raise_for_status=True,
            headers=headers,
        ) as resp:
            body = await resp.json()
            return [from_dict(data_class=StackScript, data=ss) for ss in body["data"]]


linode_api: LinodeAPI


async def linode_list_ss(message: discord.Message, client, args: List[str]):
    global linode_api
    try:
        ss_list = await linode_api.list_stackscripts()
        ss_list_str = "\n".join([str(ss) for ss in ss_list])
        await messagefuncs.sendWrappedMessage(
            f"""__StackScripts Available__\n{ss_list_str}""",
            target=message.channel,
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LLS[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def minecraft_get_time_function(message, client, args):
    try:
        with Client(
            host=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_host",
                default="34.224.93.95",
            ),
            port=int(
                config.get(
                    guild=message.guild.id,
                    channel=message.channel.id,
                    key="minecraft_rcon-port",
                    default=25575,
                )
            ),
            passwd=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_rcon-password",
                default="",
            ),
        ) as session:
            await messagefuncs.sendWrappedMessage(
                session.time("query daytime"), message.channel
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MCGTF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def minecraft_send_say_function(message, client, args):
    try:
        message_text = " ".join(args)
        with Client(
            host=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_host",
                default="34.224.93.95",
            ),
            port=int(
                config.get(
                    guild=message.guild.id,
                    channel=message.channel.id,
                    key="minecraft_rcon-port",
                    default=25575,
                )
            ),
            passwd=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_rcon-password",
                default="",
            ),
        ) as session:
            session.say(f"<{message.author.display_name}> {message_text}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MCSSF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def autounload(ch):
    pass


def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!mcgettime"],
            "function": minecraft_get_time_function,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 0,
            "args_name": [""],
            "description": "Get current time in minecraft",
        }
    )
    ch.add_command(
        {
            "trigger": ["!linode_list_ss"],
            "function": linode_list_ss,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 0,
            "args_name": [""],
            "description": "List StackScripts for calling account",
            "whitelist_guild": [634249282488107028, 843952851050430475],
        }
    )
    ch.add_command(
        {
            "trigger": ["!minecraftsendsay"],
            "function": minecraft_send_say_function,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 1,
            "args_name": ["tag"],
            "description": "Send message through to minecraft",
        }
    )
    global linode_api
    linode_api = LinodeAPI(
        ch.config.get(section="linode", key="personalAccessToken", default="")
    )
