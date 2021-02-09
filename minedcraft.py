from mcipc.rcon.je import Client
import socket
from sys import exc_info

import logging

logger = logging.getLogger("fletcher")


sessions = {}


def get_session(guild_id, channel_id):
    if not sessions.get(channel_id):
        session[channel_id] = Client(
            config.get(
                guild=guild_id,
                channel=channel_id,
                key="minecraft_host",
                default="34.224.93.95",
            ),
            int(
                config.get(
                    guild=guild_id,
                    channel=channel_id,
                    key="minecraft_rcon-port",
                    default=25575,
                )
            ),
            config.get(
                guild=guild_id,
                channel=channel_id,
                key="minecraft_rcon-password",
                default="",
            ),
        )
    return session[channel_id]


async def minecraft_send_say_function(message, client, args):
    try:
        message_text = " ".join(args)
        with get_session(message.guild.id, message.channel.id) as session:
            session.say(message_text)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MCSSF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def autounload(ch):
    pass


def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!minecraftsendsay"],
            "function": minecraft_send_say_function,
            "async": True,
            "long_run": True,
            "admin": False,
            "hidden": True,
            "args_num": 1,
            "args_name": ["tag"],
            "description": "Send message through to minecraft",
        }
    )
