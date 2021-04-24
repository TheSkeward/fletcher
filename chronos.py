import re
from sys import exc_info
import logging
from geopy.geocoders import Nominatim
import pytz
import discord
from tzwhere import tzwhere
from datetime import datetime

geolocator = None
tzwheremst_cache = None
logger = logging.getLogger("fletcher")


def time_at_place(message, client, args):
    global ch
    global geolocator
    try:
        q = " ".join(args)
        if len(args) > 0:
            try:
                tz = pytz.timezone(q)
            except pytz.UnknownTimeZoneError as e:
                location = geolocator.geocode(q)
                tz = pytz.timezone(
                    tzwheremst().tzNameAt(location.latitude, location.longitude)
                )
        elif ch.user_config(message.author.id, message.guild.id, "tz"):
            tz = pytz.timezone(
                ch.user_config(message.author.id, message.guild.id, "tz")
            )
        else:
            tz = pytz.utc
        now = datetime.now(tz)
        return f'The time is {now.strftime("%Y-%m-%d %H:%M")} ({tz} time zone).'
    except pytz.UnknownTimeZoneError as e:
        return f"Error: {type(e).__name__} for ({location})"
    except AttributeError as e:
        return "Could not find matching place or time"
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TAP[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


def get_tz(message=None, user=None, guild=None):
    global ch
    if message:
        user = message.author
        guild = message.guild
    if user and isinstance(user, discord.User) or isinstance(user, discord.Member):
        user = user.id
    if guild and isinstance(guild, discord.Guild):
        guild = guild.id
    if ch.user_config(user, guild, "tz"):
        tz = pytz.timezone(ch.user_config(user, guild, "tz"))
    elif ch.scope_config(guild=guild, channel=message.channel).get("tz"):
        tz = pytz.timezone(
            ch.scope_config(guild=guild, channel=message.channel).get("tz")
        )
    elif ch.scope_config(guild=guild).get("tz"):
        tz = pytz.timezone(ch.config.get(guild=guild, key="tz"))
    else:
        tz = pytz.utc
    return tz


def get_now(message=None, user=None, guild=None):
    return datetime.now(get_tz(message=message, user=user, guild=guild))


def tzwheremst():
    global tzwheremst_cache
    if not tzwheremst_cache:
        tzwheremst_cache = tzwhere.tzwhere()
    return tzwheremst_cache


def autoload(ch):
    global config
    global geolocator
    if not geolocator:
        geolocator = Nominatim(
            user_agent=config.get("discord", dict()).get("botLogName", "botLogName")
        )
    ch.add_command(
        {
            "trigger": ["!now", "!time"],
            "function": time_at_place,
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": ["[place name]"],
            "description": "Current time (at optional location)",
        }
    )


parse_interval = re.compile(
    r"(?:[\d.]+\s*?y(?:ears?)?)?[,\s]*(?:[\d.]+\s*?mon(?:ths?)??)?[,\s]*(?:[\d.]+\s*?w(?:e*ks?)?)?[,\s]*(?:[\d.]+\s*?d(?:ays?)?)?[,\s]*(?:[\d.]+\s*?h(?:[ou]*rs?)?)?[,:\s]*(?:[\d.]+\s*?min(?:utes?)?)?",
    re.IGNORECASE,
)

parse_instant = re.compile(
    r"(?:[\d.]+\s*?y(?:ears?)?)?[,\s]*(?:[\d.]+\s*?mon(?:ths?)??)?[,\s]*(?:[\d.]+\s*?w(?:e*ks?)?)?[,\s]*(?:[\d.]+\s*?d(?:ays?)?)?[,\s]*(?:[\d.]+\s*?h(?:[ou]*rs?)?)?[,:\s]*(?:[\d.]+\s*?min(?:utes?)?)?",
    re.IGNORECASE,
)


async def autounload(ch):
    pass
