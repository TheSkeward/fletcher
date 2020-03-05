from sys import exc_info
import logging
from geopy.geocoders import Nominatim
import pytz
import discord
from tzwhere import tzwhere
from datetime import datetime

geolocator = None
tzwheremst = None
logger = logging.getLogger("fletcher")

def time_at_place(message, client, args):
    global ch
    global geolocator
    global tzwheremst
    try:
        if len(args) > 0:
            location = geolocator.geocode(" ".join(args))
            tz = pytz.timezone(tzwheremst.tzNameAt(location.latitude, location.longitude))
        elif ch.user_config(message.author.id, message.guild.id, 'tz'):
            tz = pytz.timezone(ch.user_config(message.author.id, message.guild.id, 'tz'))
        else:
            tz = pytz.utc
        now = datetime.now(tz)
        return f'The time is {now.strftime("%Y-%m-%d %H:%M")}.'
    except pytz.UnknownTimeZoneError as e:
        return f'Error: {type(e).__name__} for {e}'
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
    if ch.user_config(user, guild, 'tz'):
        tz = pytz.timezone(ch.user_config(message.author.id, message.guild.id, 'tz'))
    elif ch.scoped_config(guild=guild, channel=message.channel).get('tz'):
        tz = pytz.timezone(ch.scoped_config(guild=guild, channel=message.channel).get('tz'))
    elif ch.scoped_config(guild=guild).get('tz'):
        tz = pytz.timezone(ch.scoped_config(guild=guild).get('tz'))
    else:
        tz = pytz.utc
    return tz

def get_now(message=None, user=None, guild=None):
    return datetime.now(get_tz(message=message, user=user, guild=guild))

def autoload(ch):
    global config
    global geolocator
    global tzwheremst
    geolocator = Nominatim(user_agent=config.get("discord", dict()).get("botLogName", "botLogName"))
    tzwheremst = tzwhere.tzwhere()
    ch.add_command(
        {
            "trigger": ["!now"],
            "function": time_at_place,
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": ['[place name]'],
            "description": "Current time (at optional location)",
        }
    )
