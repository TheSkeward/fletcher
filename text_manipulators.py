import codecs
from datetime import datetime, timedelta
import discord
import io
import math
import random
from PIL import Image
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


async def scramble_function(message, client, args):
    try:
        input_image_blob = io.BytesIO()
        await message.attachments[0].save(input_image_blob)
        if len(args) == 2 and type(args[1]) is discord.User:
            pass
        else:
            try:
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
                pass
        input_image_blob.seek(0)
        input_image = Image.open(input_image_blob)
        if input_image.size == (1, 1):
            raise ValueError("input image must contain more than 1 pixel")
        number_of_regions = 1 # number_of_colours(input_image)
        key_image = None
        region_lists = create_region_lists(input_image, key_image,
                                           number_of_regions)
        random.seed(input_image.size)
        shuffle(region_lists)
        output_image = swap_pixels(input_image, region_lists)
        output_image_blob = io.BytesIO()
        output_image.save(output_image_blob, format="PNG")
        output_image_blob.seek(0)
        if len(args) == 2 and type(args[1]) is discord.User:
            output_message = await args[1].send(files=[discord.File(output_image_blob, message.attachments[0].filename)])
        else:
            output_message = await message.channel.send(files=[discord.File(output_image_blob, message.attachments[0].filename)])
        await output_message.add_reaction('🔞')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("SIF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

def number_of_colours(image):
    return len(set(list(image.getdata())))


def create_region_lists(input_image, key_image, number_of_regions):
    template = create_template(input_image, key_image, number_of_regions)
    number_of_regions_created = len(set(template))
    region_lists = [[] for i in range(number_of_regions_created)]
    for i in range(len(template)):
        region = template[i]
        region_lists[region].append(i)
    odd_region_lists = [region_list for region_list in region_lists
                        if len(region_list) % 2]
    for i in range(len(odd_region_lists) - 1):
        odd_region_lists[i].append(odd_region_lists[i + 1].pop())
    return region_lists


def create_template(input_image, key_image, number_of_regions):
    width, height = input_image.size
    return [0] * (width * height)

def no_small_pixel_regions(pixel_regions, number_of_regions_created):
    counts = [0 for i in range(number_of_regions_created)]
    for value in pixel_regions:
        counts[value] += 1
    if all(counts[i] >= 256 for i in range(number_of_regions_created)):
        return True


def shuffle(region_lists):
    for region_list in region_lists:
        length = len(region_list)
        for i in range(length):
            j = random.randrange(length)
            region_list[i], region_list[j] = region_list[j], region_list[i]


def measure(pixel):
    '''Return a single value roughly measuring the brightness.

    Not intended as an accurate measure, simply uses primes to prevent two
    different colours from having the same measure, so that an image with
    different colours of similar brightness will still be divided into
    regions.
    '''
    if type(pixel) is int:
        return pixel
    else:
        r, g, b = pixel[:3]
        return r * 2999 + g * 5869 + b * 1151


def swap_pixels(input_image, region_lists):
    pixels = list(input_image.getdata())
    for region in region_lists:
        for i in range(0, len(region) - 1, 2):
            pixels[region[i]], pixels[region[i+1]] = (pixels[region[i+1]],
                                                      pixels[region[i]])
    scrambled_image = Image.new(input_image.mode, input_image.size)
    scrambled_image.putdata(pixels)
    return scrambled_image


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
        if len(args) == 2 and type(args[1]) is discord.user:
            return await args[1].send(codecs.encode(message.content, 'rot_13'))
        elif len(args) == 2 and args[1] == 'INTPROC':
            return codecs.encode(args[0], 'rot_13')
        else:
            messageContent = message.author.name+": "+codecs.encode(" ".join(args), 'rot_13')
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction('🕜')
            try: 
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("R13F[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def memfrob_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            return await args[1].send(memfrob(message.content))
        else:
            messageContent = message.author.name+": "+memfrob(" ".join(args))
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction('🕦')
            try: 
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
                pass
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

    ch.add_command({
        'trigger': ['!scramble', '🔞'],
        'function': scramble_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Send contents of image deep fried'
        })
