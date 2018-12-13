import discord
import schedule
import time

# global conn set by reload_function

async def remind_function(message, client, args):
    global conn
    try:
        cur = conn.cursor()
        # Parser
        from dateparser.search import search_dates
        search_dates(message.content)
        # Schedule reminder
        # Insert into database
        # Reload all reminders
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("DBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def autoload(ch):
    ch.add_command({
        'trigger': ['!remind'],
        'function': remind_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': '`!remind (me|<@User>) [to|that] (.*) [at|in|by] time/date`'
        })
    # Clear any previously set event threads
    # Spawn new event thread with reminder set in it, sleep loop
    # https://github.com/mrhwick/schedule/blob/master/schedule/__init__.py
        while True:
            schedule.run_pending()
            time.sleep(1)
