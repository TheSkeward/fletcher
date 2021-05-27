from mcipc.rcon import Client
import messagefuncs
import socket
from sys import exc_info

import logging

logger = logging.getLogger("fletcher")

sessions = {}


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
            await messagefuncs.sendWrappedMessage(session.time("query daytime"), message.channel)
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
