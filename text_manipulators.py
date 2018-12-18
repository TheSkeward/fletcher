import codecs
from datetime import datetime, timedelta
import math
import discord
from sys import exc_info

def smallcaps(text=False):
    if text:
        return text.translate(str.maketrans({'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ'}))
    return None

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])

def convert_hex_to_ascii(h):
    chars_in_reverse = []
    while h != 0x0:
        chars_in_reverse.append(chr(h & 0xFF))
        h = h >> 8

    chars_in_reverse.reverse()
    return ''.join(chars_in_reverse)

def memfrob(plain=""):
    plain = list(plain)
    xok = 0x2a
    length = len(plain)
    kek = []
    for x in range(0,length):
            kek.append(hex(ord(plain[x])))
    for x in range(0,length):
            kek[x] = hex(int(kek[x], 16) ^ int(hex(xok), 16))
    
    cipher = ""
    for x in range(0,length):
        cipher = cipher + convert_hex_to_ascii(int(kek[x], 16))
    return cipher

def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(int(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months ago"
    return str(int(day_diff / 365)) + " years ago"

async def rot13_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            return await args[1].send(codecs.encode(message.content, 'rot_13'))
        elif len(args) == 2 and args[1] == 'INTPROC':
            return codecs.encode(args[0], 'rot_13')
        else:
            messageContent = message.author.user.name+": "+codecs.encode(" ".join(args), 'rot_13')
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction('🕜')
            try: 
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("R13F[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def memfrob_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            return await args[1].send(memfrob(message.content))
        else:
            messageContent = message.author.user.name+": "+memfrob(" ".join(args))
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction('🕦')
            try: 
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("MFF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

def autoload(ch):
    ch.add_command({
        'trigger': ['!rot13', '🕜'],
        'function': rot13_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Send contents of message rot13 flipped (deprecated)'
        })

    ch.add_command({
        'trigger': ['!memfrob', '!spoiler', '🕦'],
        'function': memfrob_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Send contents of message to memfrob flipped'
        })
