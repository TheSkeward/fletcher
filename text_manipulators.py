from datetime import datetime, timedelta
from PIL import Image
from sys import exc_info
import asyncio
import aiohttp
import codecs
import discord
import hashlib
import io
import logging
import math
import messagefuncs
import netcode
import random
import shortuuid
import textwrap
import ujson
import zalgo.zalgo as zalgo

logger = logging.getLogger("fletcher")


def smoltext(text=False):
    if text:
        return text.translate(
            str.maketrans(
                {
                    "a": "ᵃ",
                    "b": "ᵇ",
                    "c": "ᶜ",
                    "d": "ᵈ",
                    "e": "ᵉ",
                    "f": "ᶠ",
                    "g": "ᵍ",
                    "h": "ʰ",
                    "i": "ᶦ",
                    "j": "ʲ",
                    "k": "ᵏ",
                    "l": "ˡ",
                    "m": "ᵐ",
                    "n": "ⁿ",
                    "o": "ᵒ",
                    "p": "ᵖ",
                    "q": "ᑫ",
                    "r": "ʳ",
                    "s": "ˢ",
                    "t": "ᵗ",
                    "u": "ᵘ",
                    "v": "ᵛ",
                    "w": "ʷ",
                    "x": "ˣ",
                    "y": "ʸ",
                    "z": "ᶻ",
                }
            )
        )
    return None


def smallcaps(text=False):
    if text:
        return text.translate(
            str.maketrans(
                {
                    "a": "ᴀ",
                    "b": "ʙ",
                    "c": "ᴄ",
                    "d": "ᴅ",
                    "e": "ᴇ",
                    "f": "ғ",
                    "g": "ɢ",
                    "h": "ʜ",
                    "i": "ɪ",
                    "j": "ᴊ",
                    "k": "ᴋ",
                    "l": "ʟ",
                    "m": "ᴍ",
                    "n": "ɴ",
                    "o": "ᴏ",
                    "p": "ᴘ",
                    "q": "ǫ",
                    "r": "ʀ",
                    "s": "s",
                    "t": "ᴛ",
                    "u": "ᴜ",
                    "v": "ᴠ",
                    "w": "ᴡ",
                    "x": "x",
                    "y": "ʏ",
                    "z": "ᴢ",
                }
            )
        )
    return None


def swapcasealpha(text=False):
    if text:
        return text.translate(
            str.maketrans(
                {
                    "a": "A",
                    "b": "B",
                    "c": "C",
                    "d": "D",
                    "e": "E",
                    "f": "F",
                    "g": "G",
                    "h": "H",
                    "i": "I",
                    "j": "J",
                    "k": "K",
                    "l": "L",
                    "m": "M",
                    "n": "N",
                    "o": "O",
                    "p": "P",
                    "q": "Q",
                    "r": "R",
                    "s": "S",
                    "t": "T",
                    "u": "U",
                    "v": "V",
                    "w": "W",
                    "x": "X",
                    "y": "Y",
                    "z": "Z",
                    "A": "a",
                    "B": "b",
                    "C": "c",
                    "D": "d",
                    "E": "e",
                    "F": "f",
                    "G": "g",
                    "H": "h",
                    "I": "i",
                    "J": "j",
                    "K": "k",
                    "L": "l",
                    "M": "m",
                    "N": "n",
                    "O": "o",
                    "P": "p",
                    "Q": "q",
                    "R": "r",
                    "S": "s",
                    "T": "t",
                    "U": "u",
                    "V": "v",
                    "W": "w",
                    "X": "x",
                    "Y": "y",
                    "Z": "z",
                }
            )
        )
    return None


ordinal = lambda n: "%d%s" % (
    n,
    "tsnrhtdd"[(math.floor(n / 10) % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
)


def convert_hex_to_ascii(h):
    chars_in_reverse = []
    while h != 0x0:
        chars_in_reverse.append(chr(h & 0xFF))
        h = h >> 8

    chars_in_reverse.reverse()
    return "".join(chars_in_reverse)


async def ocr_function(message, client, args):
    try:
        url = None
        if len(message.attachments):
            url = message.attachments[0].url
        elif len(message.embeds) and message.embeds[0].image.url != discord.Embed.Empty:
            url = message.embeds[0].image.url
        elif (
            len(message.embeds)
            and message.embeds[0].thumbnail.url != discord.Embed.Empty
        ):
            url = message.embeds[0].thumbnail.url
        elif args[0]:
            url = args[0]
        logger.debug(url)
        input_image_blob = await netcode.simple_get_image(url)
        if not input_image_blob:
            return
        input_image_blob.seek(0)
        input_image = Image.open(input_image_blob)
        input_image_blob.seek(0)
        target_url = f'http://{config["ocr"]["host"]}:{config["ocr"]["port"]}/file'
        image_to_text = ujson.loads(
            await netcode.simple_post_image(
                target_url,
                input_image_blob,
                url.split("/")[-1],
                Image.MIME[input_image.format],
            )
        )["result"]
        output_message = f">>> {image_to_text}"
        if (
            len(args) == 3
            and type(args[1]) is discord.Member
            and args[1] == message.author
        ):
            await messagefuncs.sendWrappedMessage(output_message, message.channel)
        elif len(args) == 3 and type(args[1]) is discord.Member:
            await messagefuncs.sendWrappedMessage(output_message, args[1])
        else:
            await messagefuncs.sendWrappedMessage(output_message, message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("OCR[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def mobilespoil_function(message, client, args):
    try:
        input_image_blob = io.BytesIO()
        await message.attachments[0].save(input_image_blob)
        if (
            len(args) != 3
            or type(args[1]) is not discord.Member
            or (
                type(message.channel) == discord.DMChannel
                and message.author.id == client.user.id
            )
        ):
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
        if len(args) == 3 and type(args[1]) is discord.Member:
            channel = args[1]
            content = ""
        else:
            content = "\n" + (" ".join(args))
            channel = message.channel
        content = f"Spoilered for {message.author.display_name}{content}"
        input_image_blob.seek(0)
        output_message = await channel.send(
            content=content,
            files=[
                discord.File(
                    input_image_blob, "SPOILER_" + message.attachments[0].filename
                )
            ],
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def scramble_function(message, client, args):
    try:
        if len(message.attachments) == 0:
            return
        input_image_blob = io.BytesIO()
        await message.attachments[0].save(input_image_blob)
        if (
            len(args) != 3
            or type(args[1]) is not discord.Member
            or (
                type(message.channel) == discord.DMChannel
                and message.author.id == client.user.id
            )
        ):
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
        if len(args) == 3 and type(args[1]) is discord.Member:
            output_message = await args[1].send(
                content="Scrambling image... ("
                + str(input_image_blob.getbuffer().nbytes)
                + " bytes loaded)"
            )
        else:
            output_message = await message.channel.send(
                content="Scrambling image...("
                + str(input_image_blob.getbuffer().nbytes)
                + " bytes loaded)"
            )
        input_image_blob.seek(0)
        input_image = Image.open(input_image_blob)
        if input_image.size == (1, 1):
            raise ValueError("input image must contain more than 1 pixel")
        number_of_regions = 1  # number_of_colours(input_image)
        key_image = None
        region_lists = create_region_lists(input_image, key_image, number_of_regions)
        random.seed(input_image.size)
        logger.debug("Shuffling scramble blob")
        shuffle(region_lists)
        output_image = swap_pixels(input_image, region_lists)
        output_image_blob = io.BytesIO()
        logger.debug("Saving scramble blob")
        output_image.save(output_image_blob, format="PNG", optimize=True)
        output_image_blob.seek(0)
        await output_message.delete()
        output_message = await output_message.channel.send(
            content="Scrambled for " + message.author.display_name,
            files=[discord.File(output_image_blob, message.attachments[0].filename)],
        )
        await output_message.add_reaction("🔎")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SIF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def number_of_colours(image):
    return len(set(list(image.getdata())))


def create_region_lists(input_image, key_image, number_of_regions):
    template = create_template(input_image, key_image, number_of_regions)
    number_of_regions_created = len(set(template))
    region_lists = [[] for i in range(number_of_regions_created)]
    for i in range(len(template)):
        region = template[i]
        region_lists[region].append(i)
    odd_region_lists = [
        region_list for region_list in region_lists if len(region_list) % 2
    ]
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
    """Return a single value roughly measuring the brightness.

    Not intended as an accurate measure, simply uses primes to prevent two
    different colours from having the same measure, so that an image with
    different colours of similar brightness will still be divided into
    regions.
    """
    if type(pixel) is int:
        return pixel
    else:
        r, g, b = pixel[:3]
        return r * 2999 + g * 5869 + b * 1151


def swap_pixels(input_image, region_lists):
    pixels = list(input_image.getdata())
    for region in region_lists:
        for i in range(0, len(region) - 1, 2):
            pixels[region[i]], pixels[region[i + 1]] = (
                pixels[region[i + 1]],
                pixels[region[i]],
            )
    scrambled_image = Image.new(input_image.mode, input_image.size)
    scrambled_image.putdata(pixels)
    return scrambled_image


def memfrob(plain=""):
    plain = list(plain)
    xok = 0x2A
    length = len(plain)
    kek = []
    for x in range(0, length):
        kek.append(hex(ord(plain[x])))
    for x in range(0, length):
        kek[x] = hex(int(kek[x], 16) ^ int(hex(xok), 16))

    cipher = ""
    for x in range(0, length):
        cipher = cipher + convert_hex_to_ascii(int(kek[x], 16))
    return cipher


def rot32768(s):
    y = ""
    for x in s:
        y += chr(ord(x) ^ 0x8000)
    return y


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

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
    global config
    try:
        if len(args) == 3 and type(args[1]) in [discord.Member, discord.User]:
            if message.author.id == client.user.id:
                if message.content.startswith("Mod Report"):
                    return await args[1].send(
                        codecs.encode(message.content.split(" via reaction to ", 1)[1], "rot_13")
                    )
                else:
                    return await args[1].send(
                        "Spoiler from conversation in <#{}> ({}) <https://discordapp.com/channels/{}/{}/{}>\n{}: {}".format(
                            message.channel.id,
                            message.channel.guild.name,
                            message.channel.guild.id,
                            message.channel.id,
                            message.id,
                            message.content.split(": ", 1)[0],
                            codecs.encode(message.content.split(": ", 1)[1], "rot_13"),
                        )
                    )
            elif not args[1].bot:
                return await args[1].send(
                    "Spoiler from conversation in <#{}> ({}) <https://discordapp.com/channels/{}/{}/{}>\n{}: {}".format(
                        message.channel.id,
                        message.channel.guild.name,
                        message.channel.guild.id,
                        message.channel.id,
                        message.id,
                        message.author.display_name,
                        codecs.encode(message.content, "rot_13"),
                    )
                )
            else:
                return logger.debug("Ignoring bot trigger")
        elif len(args) == 2 and args[1] == "INTPROC":
            return codecs.encode(args[0], "rot_13")
        else:
            if len(args) == 3 and type(args[1]) in [discord.Member, discord.User] and args[1].bot:
                return logger.debug("Ignoring bot reaction")
            elif len(args) == 3 and type(args[1]) in [discord.Member, discord.User] and not args[1].bot:
                logger.debug(args[1])
            messageContent = (
                "**"
                + message.author.display_name
                + "**: "
                + codecs.encode(" ".join(args), "rot_13")
            )
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction(
                client.get_emoji(int(config["discord"]["rot13"]))
            )
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("R13F[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def spoiler_function(message, client, args):
    try:
        rotate_function = memfrob
        if message.author.id == 429368441577930753:
            if len(message.clean_content.split(": ", 1)[1]) != len(
                message.clean_content.split(": ", 1)[1].encode()
            ):
                rotate_function = rot32768
        else:
            if len(message.clean_content) != len(message.clean_content.encode()):
                rotate_function = rot32768
        if len(args) == 3 and type(args[1]) is discord.Member:
            if message.author.id == 429368441577930753:
                if type(message.channel) == discord.DMChannel:
                    return await args[1].send(
                        "Spoiler from DM {}**: {}".format(
                            message.clean_content.split("**: ", 1)[0],
                            rotate_function(
                                swapcasealpha(message.clean_content.split("**: ", 1)[1])
                            ).replace("\n", " "),
                        )
                    )
                else:
                    return await args[1].send(
                        "Spoiler from conversation in <#{}> ({}) <https://discordapp.com/channels/{}/{}/{}>\n{}**: {}".format(
                            message.channel.id,
                            message.channel.guild.name,
                            message.channel.guild.id,
                            message.channel.id,
                            message.id,
                            message.clean_content.split("**: ", 1)[0],
                            rotate_function(
                                swapcasealpha(message.clean_content.split("**: ", 1)[1])
                            ).replace("\n", " "),
                        )
                    )
            else:
                logger.debug("MFF: Backing out, not my message.")
        else:
            content_parts = message.clean_content.split(" ", 1)
            if not len(content_parts) == 2:
                return
            messageContent = (
                "**"
                + message.author.display_name
                + "**: "
                + swapcasealpha(
                    rotate_function(
                       content_parts[1].replace(" ", "\n")
                    )
                )
            )
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction("🙈")
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MFF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def reaction_request_function(message, client, args):
    try:
        if not message.channel.permissions_for(message.author).external_emojis:
            return False
        emoji_query = args[0].strip(":")
        target = None
        try:
            urlParts = messagefuncs.extract_identifiers_messagelink.search(
                message.content
            ).groups()
            if len(urlParts) == 3:
                guild_id = int(urlParts[0])
                channel_id = int(urlParts[1])
                message_id = int(urlParts[2])
                guild = client.get_guild(guild_id)
                if guild is None:
                    logger.warning("QAF: Fletcher is not in guild ID " + str(guild_id))
                    return
                channel = guild.get_channel(channel_id)
                target = await channel.fetch_message(message_id)
        except AttributeError:
            pass
        if len(args) >= 2 and args[1].isnumeric() and int(args[1]) < 1000000:
            emoji = list(filter(lambda m: m.name == emoji_query, client.emojis))
            emoji = emoji[int(args[1])]
        else:
            if ":" in emoji_query:
                emoji_query = emoji_query.split(":")
                emoji_query[0] = messagefuncs.expand_guild_name(emoji_query[0], suffix="")
                filter_query = lambda m: m.name == emoji_query[1] and m.guild.name == emoji_query[0]
            else:
                filter_query = lambda m: m.name == emoji_query
            emoji = list(filter(filter_query, client.emojis)).pop(0)
        if len(args) >= 2 and args[-1].isnumeric() and int(args[1]) >= 1000000:
            target = await message.channel.fetch_message(int(args[-1]))
        if emoji:
            if target is None:
                async for historical_message in message.channel.history(
                    before=message, oldest_first=False
                ):
                    if historical_message.author != message.author:
                        target = historical_message
                        break
            await target.add_reaction(emoji)
            await asyncio.sleep(1)
            try:
                reaction, user = await client.wait_for(
                    "reaction_add",
                    timeout=6000.0,
                    check=lambda reaction, user: str(reaction.emoji) == str(emoji),
                )
            except asyncio.TimeoutError:
                pass
            try:
                await target.remove_reaction(emoji, client.user)
            except discord.NotFound:
                # Message deleted before we could remove the reaction
                pass
        try:
            if config["discord"].get("snappy"):
                await message.delete()
        except discord.Forbidden:
            logger.warning("XRF: Couldn't delete message but snappy mode is on")
            pass
    except IndexError as e:
        await message.add_reaction("🚫")
        await message.author.send(
            f"XRF: Couldn't find reaction with name {emoji_query}, please check spelling or name {e}"
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("XRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def blockquote_embed_function(message, client, args):
    try:
        title = None
        rollup = None
        if len(args) >= 1 and args[0][0:2] == "<<":
            limit = int(args[0][2:])
            title = " ".join(args[1:])
        elif len(args) >= 1:
            urlParts = messagefuncs.extract_identifiers_messagelink.search(
                message.content
            )
            if urlParts and len(urlParts.groups()) == 3:
                guild_id = int(urlParts.group(1))
                channel_id = int(urlParts.group(2))
                message_id = int(urlParts.group(3))
                guild = client.get_guild(guild_id)
                if guild is None:
                    logger.info("PMF: Fletcher is not in guild ID " + str(guild_id))
                    await message.add_reaction("🚫")
                    return await message.author.send(
                        "I don't have permission to access that message, please check server configuration."
                    )
                channel = guild.get_channel(channel_id)
                target_message = await channel.fetch_message(message_id)
                # created_at is naîve, but specified as UTC by Discord API docs
                sent_at = target_message.created_at.strftime("%B %d, %Y %I:%M%p UTC")
                rollup = target_message.content
                if rollup == "":
                    rollup = "*No Text*"
                if (
                    message.guild
                    and message.guild.id == guild_id
                    and message.channel.id == channel_id
                ):
                    title = "Message from {} sent at {}".format(
                        target_message.author.name, sent_at
                    )
                elif message.guild and message.guild.id == guild_id:
                    title = "Message from {} sent in <#{}> at {}".format(
                        target_message.author.name, channel_id, sent_at
                    )
                else:
                    title = "Message from {} sent in #{} ({}) at {}".format(
                        target_message.author.name, channel.name, guild.name, sent_at
                    )
            limit = None
        else:
            limit = None
        if len(args) == 0 or (limit and limit <= 0):
            limit = 1
        if limit:
            historical_messages = []
            async for historical_message in message.channel.history(
                before=message, limit=None
            ):
                if historical_message.author == message.author:
                    historical_messages.append(historical_message)
                    limit -= 1
                if limit == 0:
                    break
            rollup = ""
            for message in historical_messages:
                rollup = f"{message.clean_content}\n{rollup}"
        else:
            if not rollup:
                if "\n" in message.content:
                    title = message.content.split("\n", 1)[0].split(" ", 1)[1]
                    rollup = message.content.split("\n", 1)[1]
                else:
                    rollup = message.content.split(" ", 1)[1]
        quoted_by = f"{message.author.name}#{message.author.discriminator}"
        if hasattr(message.author, "nick") and message.author.nick is not None:
            quoted_by = f"{message.author.nick} ({quoted_by})"
        else:
            quoted_by = f"On behalf of {quoted_by}"
        embed = discord.Embed().set_footer(
            icon_url=message.author.avatar_url, text=quoted_by
        )
        if title:
            embed.title = title
        if len(rollup) < 2048:
            embed.description = rollup
            rollup = None
        # 25 fields * 1024 characters
        # https://discordapp.com/developers/docs/resources/channel#embed-object-embed-field-structure
        elif len(rollup) <= 25 * 1024:
            msg_chunks = textwrap.wrap(rollup, 1024, replace_whitespace=False)
            for hunk in msg_chunks:
                embed.add_field(name="\u1160", value=hunk, inline=True)
            rollup = None
        else:
            # TODO send multiple embeds instead
            await message.author.send(
                "Message too long, maximum quotable character count is 25 * 1024"
            )
        if not rollup:
            await message.channel.send(embed=embed)
            try:
                if config["discord"].get("snappy"):
                    for message in historical_messages:
                        await message.delete()
                    await message.delete()
            except discord.Forbidden:
                logger.warning("BEF: Couldn't delete messages but snappy mode is on")
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("BEF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def zalgo_function(message, client, args):
    try:
        await message.channel.send(zalgo.zalgo(" ".join(args)))
        try:
            if config["discord"].get("snappy"):
                await message.delete()
        except discord.Forbidden:
            logger.warning("ZF: Couldn't delete messages but snappy mode is on")
            pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("ZF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def fiche_function(content, message_id):
    try:
        if len(content) > int(config["pastebin"]["max_size"]):
            raise Exception(
                f'Exceeds max file size in pastebin > max_size ({config["pastebin"]["max_size"]})'
            )
        link = config["pastebin"]["base_url"]
        uuid = shortuuid.uuid(name=link + "/" + str(message_id))
        link += f"/{uuid}.txt"
        with open(f'{config["pastebin"]["base_path"]}/{uuid}.txt', "w") as output:
            output.write(content)
        return link
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("FF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def autoload(ch):
    ch.add_command(
        {
            "trigger": [
                "!rot13",
                "🕜",
                "<:rot13:539568301861371905>",
                "<:rot13:527988322879012894>",
            ],
            "function": rot13_function,
            "async": True,
            "args_num": 1,
            "args_name": ['message'],
            "description": "Replaces the message with a [ROT13](https://en.wikipedia.org/wiki/ROT13) version. React with <:rot13:539568301861371905> or 🕜 to receive a DM with the original message.",
            "syntax": "!rot13 message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!spoiler", "🙈", "!memfrob", "🕦"],
            "function": spoiler_function,
            "async": True,
            "args_num": 1,
            "args_name": ['message'],
            "description": "Similar functionality to `!rot13`, but obfuscates the message more thoroughly and works with all characters (not just alphabetic ones). React with 🙈 to receive a DM with the original message.",
            "syntax": "!spoiler message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!scramble", "🔎", "🔞"],
            "function": scramble_function,
            "async": True,
            "args_num": 0,
            "args_name": ['Image attachment'],
            "description": "Replaces image with a deep fried version. React with 🔎 to receive a DM with the original image.",
            "syntax": "!scramble` as a comment on an uploaded image`",
        }
    )

    ch.add_command(
        {
            "trigger": ["!mobilespoil", "\u1F4F3"],
            "function": mobilespoil_function,
            "async": True,
            "args_num": 0,
            "args_name": ['Image attachment'],
            "description": "Replaces image with a Discord spoilered version.",
            "syntax": "!mobilespoil` as a comment on an uploaded image`",
        }
    )

    ch.add_command(
        {
            "trigger": ["!md5"],
            "function": lambda message, client, args: hashlib.md5(" ".join(args).encode('utf-8')).hexdigest(),
            "async": False,
            "args_num": 1,
            "args_name": [],
            "description": "Provides an [MD5](https://en.wikipedia.org/wiki/MD5) hash of the message text (does not work on images).",
            "syntax": "!md5 message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!blockquote"],
            "function": blockquote_embed_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Blockquote message(s) as a webhook embed (see syntax for details).",
            "syntax": "####Quote previous message\n**Syntax:** `!blockquote`\n\nCreates a blockquote of your previous message using a webhook embed. Webhooks have a higher character limit than messages, so this allows multiple messages to be combined into one.\n\n####Quote multiple previous messages\n**Syntax:** `!blockquote <<n (title)`\n\n**Example:** `!blockquote <<3 Hamlet's Soliloquy`\n\nCreates a blockquote from your past *n* messages, with optional title. The example would produce a quote from your past 3 messages, titled \"Hamlet's Soliloquy\".\n\n####Quote from message text\n**Syntax:** `!blockquote message`\n\n####Quote from message links\n**Syntax:** `!blockquote messagelink1 (messagelink2) (...)`\n\nCreates a blockquote from one or more linked messages.",
        }
    )

    ch.add_command(
        {
            "trigger": ["!smallcaps"],
            "function": lambda message, client, args: smallcaps(" ".join(args).lower()),
            "async": False,
            "args_num": 1,
            "args_name": [],
            "description": "Smallcaps text",
        }
    )

    ch.add_command(
        {
            "trigger": ["!smoltext"],
            "function": lambda message, client, args: smoltext(" ".join(args).lower()),
            "async": False,
            "args_num": 1,
            "args_name": [],
            "description": "Smol text (superscript)",
        }
    )

    ch.add_command(
        {
            "trigger": ["!zalgo"],
            "function": zalgo_function,
            "async": True,
            "args_num": 1,
            "args_name": [],
            "description": "HE COMES",
        }
    )

    ch.add_command(
        {
            "trigger": ["!xreact"],
            "function": reaction_request_function,
            "async": True,
            "args_num": 1,
            "args_name": ["Reaction name", "offset if ambiguous (optional)"],
            "description": "Request reaction (x-server)",
        }
    )

    ch.add_command(
        {
            "trigger": ["!ocr", "\U0001F50F"],
            "function": ocr_function,
            "long_run": "author",
            "async": True,
            "args_num": 0,
            "args_name": ["Image to be OCRed"],
            "description": "OCR",
        }
    )

async def autounload(ch):
    pass
