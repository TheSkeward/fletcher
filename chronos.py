from sys import exc_info
import logging
from geopy.geocoders import Nominatim
import pytz
from tzwhere import tzwhere
import datetime

geolocator = None
tzwheremst = None
logger = logging.getLogger("fletcher")

def time_at_place(message, client, args):
    global ch
    try:
        if len(args) > 0:
            location = geolocator.geocode(" ".join(args))
            tz = pytz.timezone(tzwheremst.tzNameAt(location[0], location[1]))
        elif ch.user_config(message.author.id, message.guild.id, 'tz'):
            tz = pytz.timezone(ch.user_config(message.author, message.guild, 'tz'))
        else:
            tz = pytz.utc
        now = datetime.now(tz)
        return f'The time is {now.strftime("%Y-%m-%d %H:%M")}.'
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TAP[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

def autoload(ch):
    global config
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
