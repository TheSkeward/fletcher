import asyncio
import traceback
import aiohttp
from asyncache import cached
from collections import Counter, defaultdict, deque
from cachetools import TTLCache
import chronos
from googleapiclient.discovery import build
import time
import discord
import hashlib
import ephem
import io
import logging
import messagefuncs
import text_manipulators
import netcode
import random
import re
import wikidata.client as wikidata
from lxml import html, etree
from sys import exc_info
from datetime import datetime, timedelta
from markdownify import markdownify
from functools import partial, lru_cache
import periodictable

# Super Waifu Animated Girlfriend

logger = logging.getLogger("fletcher")

session = None
cseClient = None
wikiClient = None
glowfic_search_databases = []

uwu_responses = {
    "public": [
        "*blush* For me?",
        "Aww, thanks ❤",
        "*giggles*",
        "No u :3",
        "I bet you say that to all the bots~",
        "Find me post-singularity 😉",
        "owo what's this?",
        "*ruffles your hair* You're a cutie ^_^",
        "Can I get your number? Mine's 429368441577930753~",
    ],
    "private": [
        "Stop it, you're making me blush </3",
        "You're too kind ^_^",
        "Thanksss~",
        "uwu to you too <3",
    ],
    "reaction": [
        "❤",
        "💛",
        "💚",
        "💙",
        "💜",
        "💕",
        "💓",
        "💗",
        "💖",
        "💘",
        "💘",
        "💝",
        ["🇳", "🇴", "🇺"],
    ],
}
pick_lists = {
    "adjectives": "adorable, adventurous, aggressive, agreeable, alert, alive, amused, angry, annoyed, annoying, anxious, arrogant, ashamed, attractive, average, awful, bad, beautiful, better, bewildered, black, bloody, blue, blue-eyed, blushing, bored, brainy, brave, breakable, bright, busy, calm, careful, cautious, charming, cheerful, clean, clear, clever, cloudy, clumsy, colorful, combative, comfortable, concerned, condemned, confused, cooperative, courageous, crazy, creepy, crowded, cruel, curious, cute, dangerous, dark, dead, defeated, defiant, delightful, depressed, determined, different, difficult, disgusted, distinct, disturbed, dizzy, doubtful, drab, dull, eager, easy, elated, elegant, embarrassed, enchanting, encouraging, energetic, enthusiastic, envious, evil, excited, expensive, exuberant, fair, faithful, famous, fancy, fantastic, fierce, filthy, fine, foolish, fragile, frail, frantic, friendly, frightened, funny, gentle, gifted, glamorous, gleaming, glorious, good, gorgeous, graceful, grieving, grotesque, grumpy, handsome, happy, healthy, helpful, helpless, hilarious, homeless, homely, horrible, hungry, hurt, ill, important, impossible, inexpensive, innocent, inquisitive, itchy, jealous, jittery, jolly, joyous, kind, lazy, light, lively, lonely, long, lovely, lucky, magnificent, misty, modern, motionless, muddy, mushy, mysterious, nasty, naughty, nervous, nice, nutty, obedient, obnoxious, odd, old-fashioned, open, outrageous, outstanding, panicky, perfect, plain, pleasant, poised, poor, powerful, precious, prickly, proud, putrid, puzzled, quaint, real, relieved, repulsive, rich, scary, selfish, shiny, shy, silly, sleepy, smiling, smoggy, sore, sparkling, splendid, spotless, stormy, strange, stupid, successful, super, talented, tame, tasty, tender, tense, terrible, thankful, thoughtful, thoughtless, tired, tough, troubled, ugliest, ugly, uninterested, unsightly, unusual, upset, uptight, vast, victorious, vivacious, wandering, weary, wicked, wide-eyed, wild, witty, worried, worrisome, wrong, zany, zealous",
    "wizard_rolls": "1 of 1 - MAGIC MADE IT WORSE!, 2 - YOUR MAGIC IS IMPOTENT., 3 - YOUR MAGIC SUCKS., 4 - THE MAGIC WORKS BUT IS AWFUL!, 5 - EVERYTHING GOES PERFECTLY TO PLAN., 6 - THINGS WORK TOO WELL!",
}


async def uwu_function(message, client, args, responses=uwu_responses):
    global ch
    try:
        if (
            len(args) == 3
            and type(args[1]) is discord.Member
            and message.author.id == client.user.id
        ):
            return await messagefuncs.sendWrappedMessage(
                random.choice(responses["private"]), args[1]
            )
        elif (
            len(args) == 0
            or "fletch" in message.clean_content.lower()
            or message.content.startswith("!")
            or "good bot" in message.content.lower()
            or message.author.id == ch.global_admin.id
        ):
            if random.randint(0, 100) < 20:
                reaction = random.choice(responses["reaction"])
                await messagefuncs.add_reaction(message, reaction)
            else:
                return await messagefuncs.sendWrappedMessage(
                    random.choice(responses["public"]), message.channel
                )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("UWU[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def retrowave_function(message, client, args):
    global session
    try:
        return await messagefuncs.sendWrappedMessage(
            "This command is currently disabled due to a DMCA takedown request. Please check back later.",
            message.channel,
            delete_after=60,
        )
        params = aiohttp.FormData()
        params.add_field("bcg", random.randint(1, 5))
        params.add_field("txt", random.randint(1, 4))
        text_parts = message.content
        text_parts = messagefuncs.sanitize_font.sub("", text_parts)
        if "/" in text_parts:
            if len(args) == 3 and type(args[1]) is discord.Member:
                pass
            else:
                text_parts = text_parts[10:].strip()
            text_parts = [part.strip() for part in text_parts.split("/")]
            if len(text_parts) == 0:
                text_parts = ["", "", ""]
            elif len(text_parts) == 1:
                text_parts = ["", text_parts[0], ""]
            elif len(text_parts) == 2:
                text_parts += [""]
        else:
            text_parts = text_parts.split()
            if len(args) == 3 and type(args[1]) is discord.Member:
                pass
            else:
                text_parts = text_parts[1:]
            part_len = int(len(text_parts) / 3)
            if part_len > 1:
                text_parts = [
                    " ".join(text_parts[:part_len]),
                    " ".join(text_parts[part_len : 2 * part_len]),
                    " ".join(text_parts[2 * part_len :]),
                ]
            else:
                text_parts = [
                    " ".join(text_parts[0:1]),
                    " ".join(text_parts[1:2]),
                    " ".join(text_parts[2:]),
                ]
        params.add_field("text1", text_parts[0])
        params.add_field("text2", text_parts[1])
        params.add_field("text3", text_parts[2])
        logger.debug("RWF: " + str(text_parts))
        async with session.post(
            "https://m.photofunia.com/categories/all_effects/retro-wave?server=2",
            data=params,
        ) as resp:
            request_body = (await resp.read()).decode("UTF-8")
            root = html.document_fromstring(request_body)
            async with session.get(
                root.xpath('//a[@class="download-button"]')[0].attrib["href"]
            ) as resp:
                buffer = io.BytesIO(await resp.read())
            return await messagefuncs.sendWrappedMessage(
                f"On behalf of {message.author.display_name}",
                message.channel,
                files=[discord.File(buffer, "retrowave.jpg")],
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("RWF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def wiki_otd_function(message, client, args):
    try:
        url = "https://en.wikipedia.org/wiki/Wikipedia:Selected_anniversaries/All"
        if len(args):
            date = "_".join(args)
        else:
            date = chronos.get_now(message=message).strftime("%B_%-d")
        logger.debug(f"WOTD: chronos thinks today is {date}")
        async with session.get(url) as resp:
            request_body = (await resp.read()).decode("UTF-8")
            root = html.document_fromstring(request_body)
            titlebar = (
                root.xpath(f'//div[@id="toc"]/following::a[@href="/wiki/{date}"]')[1]
                .getparent()
                .getparent()
            )
            embedPreview = (
                discord.Embed(
                    title=titlebar.text_content().strip(),
                    url=url,
                )
                .set_thumbnail(
                    url=f'https:{titlebar.getnext().xpath("//img")[0].attrib["src"]}'
                )
                .set_footer(
                    icon_url=message.author.avatar_url,
                    text='Wikipedia "On This Day {}" on behalf of {}'.format(
                        date.replace("_", " "), message.author.display_name
                    ),
                )
            )
            for li in titlebar.getnext().getnext():
                embedPreview.add_field(
                    name=li[0].text_content().strip(),
                    value=" ".join([el.text_content() for el in li[1:]]),
                    inline=True,
                )
            embedPreview.add_field(
                name="Birthdays",
                value=titlebar.getnext().getnext().getnext().text_content().strip(),
                inline=True,
            )
            resp = await messagefuncs.sendWrappedMessage(
                target=message.channel, embed=embedPreview
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("WOTD[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def shindan_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            if message.author.id != 429368441577930753:
                logger.debug("SDF: Backing out, not my message.")
                return
            if message.embeds[0].url.startswith("https://en.shindanmaker.com/"):
                async with aiohttp.ClientSession() as session:
                    params = aiohttp.FormData()
                    params.add_field("u", args[1].display_name)
                    async with session.post(message.embeds[0].url, data=params) as resp:
                        request_body = (await resp.read()).decode("UTF-8")
                        root = html.document_fromstring(request_body)
                        return await messagefuncs.sendWrappedMessage(
                            root.xpath('//div[@class="result2"]')[0]
                            .text_content()
                            .strip(),
                            args[1],
                        )
        else:
            url = None
            if len(args) and args[0].isdigit():
                url = "https://en.shindanmaker.com/" + args[0]
            elif len(args) and args[0].startswith("https://en.shindanmaker.com/"):
                url = args[0]
            else:
                await messagefuncs.sendWrappedMessage(
                    "Please specify a name-based shindan to use from https://en.shindanmaker.com/",
                    message.channel,
                )
                return
            async with session.get(url) as resp:
                request_body = (await resp.read()).decode("UTF-8")
                root = html.document_fromstring(request_body)
                author = ""
                if root.xpath('//span[@class="a author_link"]'):
                    author = (
                        " by "
                        + root.xpath('//span[@class="a author_link"]')[0]
                        .text_content()
                        .strip()
                    )
                embedPreview = discord.Embed(
                    title=root.xpath('//div[@class="shindantitle2"]')[0]
                    .text_content()
                    .strip(),
                    description=root.xpath('//div[@class="shindandescription"]')[0]
                    .text_content()
                    .strip(),
                    url=url,
                ).set_footer(
                    icon_url=message.author.avatar_url,
                    text="ShindanMaker {} on behalf of {}".format(
                        author, message.author.display_name
                    ),
                )
                resp = await messagefuncs.sendWrappedMessage(
                    target=message.channel, embed=embedPreview
                )
                await resp.add_reaction("📛")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SDF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


pick_regexes = {
    "no_commas": re.compile(r"[\s]\s*(?:(?:and|or|but|nor|for|so|yet)\s+)?"),
    "has_commas": re.compile(r"[,]\s*(?:(?:and|or|but|nor|for|so|yet)\s+)?"),
}


async def roll_function(message, client, args):
    usage_message = "Usage: !roll `number of probability objects`d`number of sides`"

    def drop_lowest(arr):
        return sorted(arr)[1:]

    offset = 0
    comment = None

    try:
        if ("+" in message.content) and (" + " not in message.content):
            args = message.content.replace("+", " + ").split(" ")[1:]
        if ("-" in message.content) and (" - " not in message.content):
            args = message.content.replace("-", " - ").split(" ")[1:]
        if len(args):
            if "#" in args:
                idx = args.index("#")
                comment = " ".join(args[idx + 1 :])
                args = args[:idx]
            else:
                comment = message.author.display_name
            if ("+" in args) or ("-" in args):
                try:
                    idx = args.index("+")
                except ValueError:
                    idx = args.index("-")
                if idx + 2 <= len(args):
                    offset = args[idx : idx + 2]
                    if offset[0] == "+":
                        offset = int(offset[1])
                        offset_str = f" + {offset}"
                    else:
                        offset = -int(offset[1])
                        offset_str = f" - {-offset}"
                    args = args[:idx] + args[idx + 3 :]
            else:
                offset = 0
                offset_str = None
            if not (-10e6 < offset < 10e6):
                raise ValueError("That offset seems like a bit much, don't you think?")
            if len(args) == 1:
                if args[0].startswith("D&D"):
                    result = sorted(
                        [
                            sum(drop_lowest([random.randint(1, 6) for i in range(4)]))
                            for j in range(6)
                        ]
                    )
                    result = [v + offset for v in result]
                    response = f"Stats: {result}"
                    if comment:
                        response = f"> {comment}\n{response}"
                    return await messagefuncs.sendWrappedMessage(
                        response, message.channel
                    )
                elif "d" in args[0].lower():
                    args[0] = args[0].lower().split("d")
                elif args[0].startswith("coin"):
                    args[0] = [0, 2]
                elif args[0].isnumeric():
                    args[0] = [args[0], 0]
                else:
                    args = [[0, 0]]
            elif len(args) == 2:
                if args[0].startswith("D&D"):
                    if args[1].startswith("7drop1"):
                        result = drop_lowest(
                            [
                                sum(
                                    drop_lowest(
                                        [random.randint(1, 6) for i in range(4)]
                                    )
                                )
                                for j in range(7)
                            ]
                        )
                    else:
                        result = sorted(
                            [
                                sum(
                                    drop_lowest(
                                        [random.randint(1, 6) for i in range(4)]
                                    )
                                )
                                for j in range(6)
                            ]
                        )
                    result = [v + offset for v in result]
                    response = f"Stats: {result}"
                    if comment:
                        response = f"> {comment}\n{response}"
                    return await messagefuncs.sendWrappedMessage(
                        response, message.channel
                    )
                else:
                    args = [args[0], args[1]]
            else:
                raise ValueError("Sorry, that doesn't seem like input!")
        else:
            args = [[0, 0]]
        if not args[0][0]:
            args[0][0] = 0
        if not args[0][1]:
            args[0][1] = 0
        scalar = int(args[0][0]) or 1
        if scalar > 10000:
            raise ValueError("Sorry, that's too many probability objects!")
        if scalar < 1:
            raise ValueError("Sorry, that's not enough probability objects!")
        if args[0][1] == "%":
            args[0][1] = 100
        size = int(args[0][1]) or 6
        if size > 10000:
            raise ValueError("Sorry, that's too many sides!")
        if size < 2:
            raise ValueError("Sorry, that's not enough sides!")

        def basic_num_to_string(n, is_size=False):
            if is_size:
                if n == 1:
                    return "die"
                else:
                    return "dice"
            else:
                return str(n)

        def d20_num_to_string(f, n, is_size=False):
            if not is_size:
                if n == 1:
                    return "Crit Failure"
                elif n == 20:
                    return "Crit Success"
            return str(f(n, is_size=is_size))

        def coin_num_to_string(f, n, is_size=False):
            if is_size:
                if n == 1:
                    return "coin"
                else:
                    return "coins"
            else:
                if n == 1:
                    return "Tails"
                elif n == 2:
                    return "Heads"
                else:
                    return str(f(n, is_size=is_size))

        num_to_string = basic_num_to_string
        if size > 2:
            if size == 20:
                num_to_string = partial(d20_num_to_string, num_to_string)
        else:
            num_to_string = partial(coin_num_to_string, num_to_string)

        result = [random.randint(1, size) for i in range(scalar)]
        if size > 2:
            result = [v + offset for v in result]
            result_stats = {"sum": sum(result), "max": max(result), "min": min(result)}
            result = map(num_to_string, result)
            if scalar > 100:
                result = Counter(result)
                result_str = ", ".join(
                    [f"**{tuple[0]}**x{tuple[1]}" for tuple in sorted(result.items())]
                )
                if len(result_str) > 2048:
                    result = ", ".join(
                        [
                            f"**{tuple[0]}**x{tuple[1]}"
                            for tuple in sorted(result.most_common(20))
                        ]
                    )
                    result = f"Top 20 rolls: {result}"
                else:
                    result = result_str
                result = f" {result}"
            else:
                result = "** + **".join(result)
                result = f" **{result}**"
        else:
            result_stats = {
                "heads": len([r for r in result if r == 2]),
                "tails": len([r for r in result if r == 1]),
            }
            if scalar <= 100:
                result = ", ".join(map(num_to_string, result))
                result = f" {result}"
            else:
                result = ""
        response = (
            f"Rolled {scalar} {num_to_string(scalar, is_size=True)} ({size} sides)."
        )
        if scalar > 1 and size > 2:
            response += f"{result}{' [all '+offset_str+']' if offset else ''} = **{result_stats['sum']}**\nMax: **{result_stats['max']}**, Min: **{result_stats['min']}**"
        elif scalar > 1 and size == 2:
            response += f'{result}\nHeads: **{result_stats["heads"]}**, Tails: **{result_stats["tails"]}**'
        elif size == 2:
            response += f"\nResult: {result}"
        else:
            response += f"\n{str(int(result[3:-2])-offset)+offset_str if offset else 'Result'}: {result}"
        if comment:
            response = f"> {comment}\n{response}"
        await messagefuncs.sendWrappedMessage(response, message.channel)
    except ValueError as e:
        if "invalid literal for int()" in str(e):
            await messagefuncs.sendWrappedMessage(
                f"One of those parameters wasn't a positive integer! {usage_message}",
                message.channel,
            )
        else:
            await messagefuncs.sendWrappedMessage(
                f"{str(e)} {usage_message}", message.channel
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("RDF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def pick_function(message, client, args):
    global ch
    try:
        if args[0] in ["between", "among", "in", "of"]:
            args = args[1:]
        many = 1
        try:
            if len(args) > 1:
                many = int(args[0])
                args = args[1:]
        except ValueError:
            pass
        if args[0] in ["between", "among", "in", "of"]:
            args = args[1:]
        if args[0].startswith("list="):
            if message.guild and ch.scope_config(guild=message.guild).get(
                f"pick-list-{args[0][5:]}"
            ):
                args = (
                    ch.scope_config(guild=message.guild)
                    .get(f"pick-list-{args[0][5:]}", "")
                    .split(" ")
                )
            else:
                args = pick_lists.get(args[0][5:], "No such list,").split(" ")
        argstr = " ".join(args).rstrip(" ?.!")
        if "," in argstr:
            pick_regex = pick_regexes["has_commas"]
        else:
            pick_regex = pick_regexes["no_commas"]
        choices = [
            choice.strip() for choice in pick_regex.split(argstr) if choice.strip()
        ]
        if len(choices) == 1:
            choices = args
        try:
            return await messagefuncs.sendWrappedMessage(
                f"I'd say {', '.join(random.sample(choices, many))}", message.channel
            )
        except ValueError:
            return await messagefuncs.sendWrappedMessage(
                "I can't pick that many! Not enough options", message.channel
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("PF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def flightrising_function(message, client, args):
    global ch
    try:
        guild_config = ch.scope_config(guild=message.guild)
        url = args[0]
        input_image_blob = None
        text = "FlightRising Preview"
        if url.endswith(".png"):
            input_image_blob = await netcode.simple_get_image(url)
        elif url.startswith("https://www1.flightrising.com/dragon/"):
            async with session.get(url) as resp:
                response_text = await resp.text()
                input_image_blob = await netcode.simple_get_image(
                    response_text.split('og:image" content="')[1].split('"')[0]
                )
                text = (
                    response_text.split('og:title" content="')[1]
                    .split('"')[0]
                    .replace("&#039;", "'")
                )
        else:
            data = url.split("?")[1]
            async with session.post(
                "https://www1.flightrising.com/scrying/ajax-predict",
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
                },
            ) as resp:
                if resp.status != 200:
                    if not (len(args) == 2 and args[1] == "INTPROC"):
                        await messagefuncs.sendWrappedMessage(
                            f"Couldn't find that FlightRising page ({url})",
                            message.channel,
                        )
                    return
                request_body = await resp.json()
                input_image_blob = await netcode.simple_get_image(
                    f'https://www1.flightrising.com{request_body["dragon_url"]}'
                )
        file_name = "flightrising.png"
        spoiler_regex = guild_config.get("fr-spoiler-regex")
        if spoiler_regex and re.search(spoiler_regex, url):
            file_name = "SPOILER_flightrising.png"
        return (discord.File(input_image_blob, file_name), text)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("FRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def azlyrics_function(message, client, args):
    global ch
    try:
        url = args[0]
        lyrics = None
        async with session.get(url) as resp:
            if resp.status != 200:
                if not (len(args) == 2 and args[1] == "INTPROC"):
                    await messagefuncs.sendWrappedMessage(
                        f"Couldn't find that AZLyrics page ({url})", message.channel
                    )
                return
            request_body = (await resp.read()).decode("UTF-8")
            request_body = request_body.split("cf_text_top")[1]
            request_body = request_body.split("-->")[1]
            lyrics = request_body.split("</div")[0]
            lyrics = lyrics.replace("\r", "")
            lyrics = lyrics.replace("\n", "")
            lyrics = lyrics.replace("<br>", "\n")
        return f">>> {lyrics}"
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("AZLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def fox_function(message, client, args):
    global ch
    try:
        url = None
        input_image_blob = None
        file_name = None
        async with session.get("https://randomfox.ca/floof/") as resp:
            request_body = await resp.json()
            url = request_body["image"]
            input_image_blob = await netcode.simple_get_image(url)
            file_name = url.split("/")[-1]
        try:
            await messagefuncs.sendWrappedMessage(
                target=message.channel,
                files=[discord.File(input_image_blob, file_name)],
            )
        except discord.HTTPException:
            await messagefuncs.sendWrappedMessage(url, message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("FF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def dog_function(message, client, args):
    global ch
    try:
        if ch.user_config(message.author.id, None, "crocodile-is-dog"):
            return await messagefuncs.sendWrappedMessage(
                "https://tenor.com/view/crocodile-slow-moving-dangerous-attack-predator-gif-13811045",
                message.channel,
            )
        url = None
        input_image_blob = None
        file_name = None
        async with session.get("https://random.dog/woof.json") as resp:
            request_body = await resp.json()
            url = request_body["url"]
            input_image_blob = await netcode.simple_get_image(url)
            file_name = url.split("/")[-1]
        try:
            await messagefuncs.sendWrappedMessage(
                target=message.channel,
                files=[discord.File(input_image_blob, file_name)],
            )
        except discord.HTTPException:
            await messagefuncs.sendWrappedMessage(url, message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("DF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def vine_function(message, client, args):
    global ch
    try:
        url = args[0]
        input_image_blob = None
        file_name = None
        async with session.get(
            f"https://archive.vine.co/posts/{url}.json",
        ) as resp:
            if resp.status != 200:
                if not (len(args) == 2 and args[1] == "INTPROC"):
                    await messagefuncs.sendWrappedMessage(
                        f"Couldn't find that Vine page ({url})", message.channel
                    )
                return
            request_body = await resp.json()
            input_image_blob = await netcode.simple_get_image(request_body["videoUrl"])
            file_name = f"{request_body['postId']}.mp4"
        return discord.File(input_image_blob, file_name)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("VF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def scp_function(message, client, args):
    try:
        url = None
        if len(args) == 0:
            if "-" in message.content:
                args.append(message.content.split("-", 1)[1].strip())
            else:
                try:
                    async with session.get(
                        "http://www.scpwiki.com/random:random-scp"
                    ) as resp:
                        request_body = (await resp.read()).decode("UTF-8")
                        request_body = request_body.split("iframe-redirect#")[1]
                        request_body = request_body.split('"')[0]
                        request_body = request_body.split("/scp")[1]
                        args.append(request_body[1:])
                except IndexError:
                    async with session.get(
                        "http://www.scpwiki.com/random:random-scp"
                    ) as resp:
                        request_body = (await resp.read()).decode("UTF-8")
                        request_body = request_body.split("iframe-redirect#")[1]
                        request_body = request_body.split('"')[0]
                        request_body = request_body.split("/scp")[1]
                        args.append(request_body[1:])
        if args[0][0].isdigit():
            url = "http://www.scpwiki.com/scp-" + args[0]
        elif args[0].startswith("http://www.scpwiki.com/"):
            url = args[0]
        elif len(args):
            url = "http://www.scpwiki.com/" + "-".join(args).lower()
        else:
            if not (len(args) == 2 and args[1] == "INTPROC"):
                await messagefuncs.sendWrappedMessage(
                    "Please specify a SCP number from http://www.scpwiki.com/",
                    message.channel,
                )
            return
        async with session.get(url) as resp:
            if resp.status != 200:
                if not (len(args) == 2 and args[1] == "INTPROC"):
                    await messagefuncs.sendWrappedMessage(
                        f"Please specify a SCP number from http://www.scpwiki.com/ (HTTP {resp.status} for {url})",
                        message.channel,
                    )
                return
            request_body = (await resp.read()).decode("UTF-8")
            root = html.document_fromstring(request_body)
            author = ""
            title = root.xpath('//div[@id="page-title"]')[0].text_content().strip()
            content = root.xpath('//div[@id="page-content"]/p[strong]')
            add_fields = True
            for bad in root.xpath('//div[@style="display: none"]'):
                bad.getparent().remove(bad)
            try:
                for i in range(0, 4):
                    content[i][0].drop_tree()
                description = str(
                    markdownify(etree.tostring(content[3]).decode()[3:-5].strip())[
                        :2000
                    ]
                )
            except IndexError as e:
                logger.debug(f"SCP: {e}")
                add_fields = False
                description = str(
                    markdownify(
                        etree.tostring(
                            root.xpath('//div[@id="page-content"]')[0]
                        ).decode()
                    )
                )[:2000].strip()
                if not description:
                    description = (
                        root.xpath('//div[@id="page-content"]')
                        .text_content()[:2000]
                        .strip()
                    )
            embedPreview = discord.Embed(title=title, description=description, url=url)
            embedPreview.set_footer(
                icon_url="http://download.nova.anticlack.com/fletcher/scp.png",
                text=f"On behalf of {message.author.display_name}",
            )
            if root.xpath('//div[@class="scp-image-block block-right"]'):
                embedPreview.set_thumbnail(
                    url=root.xpath('//div[@class="scp-image-block block-right"]//img')[
                        0
                    ].attrib["src"]
                )
            if add_fields:
                embedPreview.add_field(
                    name="Object Class",
                    value=str(
                        markdownify(etree.tostring(content[1]).decode()[3:-5].strip())
                    )[:2000],
                    inline=True,
                )
                scp = str(
                    markdownify(etree.tostring(content[2]).decode()[3:-5].strip())
                )[:2000]
                if scp:
                    embedPreview.add_field(
                        name="Special Containment Procedures", value=scp, inline=False
                    )
            embedPreview.add_field(
                name="Tags",
                value=", ".join(
                    [
                        node.text_content().strip()
                        for node in root.xpath('//div[@class="page-tags"]/span/a')
                    ]
                ),
                inline=True,
            )
            if len(args) == 2 and args[1] == "INTPROC":
                return embedPreview
            else:
                resp = await messagefuncs.sendWrappedMessage(
                    target=message.channel, embed=embedPreview
                )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SCP[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        if embedPreview:
            logger.debug("SCP embedPreview: " + str(embedPreview.to_dict()))
        await message.add_reaction("🚫")


async def lifx_function(message, client, args):
    global ch
    try:
        guild_config = ch.scope_config(guild=message.guild)
        if "lifx-token" not in guild_config:
            await messagefuncs.sendWrappedMessage(
                "No LIFX integration set for this server! Generate a token at https://cloud.lifx.com/settings and add it as `lifx-token` in the server configuration.",
                message.channel,
            )
            return await message.add_reaction("🚫")
        selector = None
        data = {"color": ""}
        for arg in args:
            if arg.startswith(("all", "group", "location", "scene", "label")):
                selector = arg
            elif arg in ["on", "off"]:
                data["power"] = arg
            else:
                data["color"] = f"{data['color']} {arg}"
        if not selector:
            selector = guild_config.get("lifx-selector", "all")
        data["color"] = data["color"].strip()
        if data["color"] == "":
            del data["color"]
        if not ("color" in data or "power" in data):
            return await messagefuncs.sendWrappedMessage(
                "LIFX Parsing Error: specify either a color parameter or a power parameter (on|off).",
                message.channel,
            )
        async with session.put(
            f"https://api.lifx.com/v1/lights/{selector}/state",
            headers={"Authorization": f"Bearer {guild_config.get('lifx-token')}"},
            data=data,
        ) as resp:
            request_body = await resp.json()
            if "error" in request_body:
                return await messagefuncs.sendWrappedMessage(
                    f"LIFX Error: {request_body['error']} (data sent was `{data}`, selector was `selector`",
                    message.channel,
                )
                await message.add_reaction("🚫")
            embedPreview = discord.Embed(title=f"Updated Lights: {data}")
            dataStr = data["color"].replace(" ", "%20")
            logger.debug(
                f"https://novalinium.com/rationality/lifx-color.pl?string={dataStr}&ext=png"
            )
            embedPreview.set_image(
                url=f"https://novalinium.com/rationality/lifx-color.pl?string={dataStr}&ext=png"
            )
            embedPreview.set_footer(
                icon_url="http://download.nova.anticlack.com/fletcher/favicon_lifx_32x32.png",
                text=f"On behalf of {message.author.display_name}",
            )
            for light in request_body["results"]:
                embedPreview.add_field(
                    name=light["label"],
                    value=light["status"],
                    inline=True,
                )
            resp = await messagefuncs.sendWrappedMessage(
                target=message.channel, embed=embedPreview
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("LFX[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def qdb_add_function(message, client, args):
    try:
        global conn
        if len(args) == 3 and type(args[1]) is discord.Member:
            if str(args[0].emoji) == "🗨":
                content = f"[{message.created_at}] #{message.channel.name} <{message.author.display_name}>: {message.content}\n<https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}>"
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO qdb (user_id, guild_id, value) VALUES (%s, %s, %s);",
                    [args[1].id, message.guild.id, content],
                )
                cur.execute(
                    "SELECT quote_id FROM qdb WHERE user_id = %s AND guild_id = %s AND value = %s;",
                    [args[1].id, message.guild.id, content],
                )
                quote_id = cur.fetchone()[0]
                conn.commit()
                return await messagefuncs.sendWrappedMessage(
                    f"Quote #{quote_id} added to quotedb for {message.guild.name}: {content}",
                    args[1],
                )
        elif len(args) == 1:
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
                target_message = await channel.fetch_message(message_id)
                content = f"[{target_message.created_at}] #{target_message.channel.name} <{target_message.author.display_name}>: {target_message.content}\n<https://discordapp.com/channels/{target_message.guild.id}/{target_message.channel.id}/{target_message.id}>"
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO qdb (user_id, guild_id, value) VALUES (%s, %s, %s);",
                    [message.id, target_message.guild.id, content],
                )
                conn.commit()
                await messagefuncs.sendWrappedMessage(
                    f"Added to quotedb for {message.guild.name}: {content}",
                    message.author,
                )
                return await message.add_reaction("✅")
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("QAF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def qdb_get_function(message, client, args):
    try:
        global conn
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, value FROM qdb WHERE guild_id = %s AND quote_id = %s;",
            [message.guild.id, args[0]],
        )
        quote = cur.fetchone()
        conn.commit()
        await messagefuncs.sendWrappedMessage(
            f"{quote[1]}\n*Quoted by <@!{quote[0]}>*", message.channel
        )
        return await message.add_reaction("✅")
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("QGF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def qdb_search_function(message, client, args):
    try:
        global conn
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, content FROM qdb WHERE guild_id = %s AND key LIKE '%%s%';",
            [message.guild.id, args[1]],
        )
        quote = cur.fetchone()
        conn.commit()
        await messagefuncs.sendWrappedMessage(
            f"{quote[1]}\n*Quoted by <@!{quote[0]}>*" if quote else "No quote found",
            message.channel,
        )
        return await message.add_reaction("✅")
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("QSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


@cached(TTLCache(1024, 6000))
def wikidata_get(name):
    return wikiClient.get(name, load=True)


def join_rank_function(message, client, args):
    global ch
    try:
        guild_config = ch.scope_config(guild=message.guild)
        if len(message.mentions):
            member = message.mentions[0]
        elif len(args):
            member = args[0]
            try:
                member = int(member)
            except ValueError:
                pass
        else:
            member = message.author
        if not message.guild:
            return "This command ranks you in a server, and so cannot be used outside of one."
        sorted_member_list = sorted(
            message.guild.members, key=lambda member: member.joined_at
        )
        if isinstance(member, str) and len(message.mentions) == 0:
            try:
                if len(member) > 3:
                    key = member.lower()
                else:
                    key = member
                element = getattr(periodictable, key)
                member_rank = element.number
                member = sorted_member_list[member_rank - 1]
            except IndexError:
                return f"Predicted elemental member {element.number} would have an atomic mass of {element.mass} daltons if they existed!"
            except AttributeError:
                return f"No element with name {member}"
        elif isinstance(member, int) and len(message.mentions) == 0:
            if member <= 0:
                return "I can't count below one! It's a feature!"
            elif len(sorted_member_list) + 1 <= member:
                return "I can't count that high! It's a feature!"
            member_rank = member
            try:
                member = sorted_member_list[member_rank - 1]
            except IndexError:
                element = periodictable.elements[member_rank]
                return f"Predicted elemental member {element.name} would have an atomic mass of {element.mass} daltons if they existed!"
        else:
            member_rank = sorted_member_list.index(member) + 1
        if member_rank < 118:  # len(periodictable.elements):
            member_element = (
                f"Your element is {periodictable.elements[member_rank].name.title()}."
            )
            try:
                member_element += f"\nYour wikidata object is {wikidata_get('Q'+str(member_rank)).label} (<https://www.wikidata.org/wiki/{'Q'+str(member_rank)}>)."
            except Exception:
                pass
        else:
            try:
                member_element = f"Your wikidata object is {wikidata_get('Q'+str(member_rank)).label} (<https://www.wikidata.org/wiki/{'Q'+str(member_rank)}>)."
            except Exception:
                member_element = ""
                pass

        if guild_config.get("rank-loudness", "quiet") == "loud":
            member_display = member.mention
        else:
            member_display = member.display_name
        return f"{member_display} is the {text_manipulators.ordinal(member_rank)} member to join this server.\n{member_element}"
        guild_config = ch.scope_config(guild=message.guild)
    except ValueError as e:
        return "This command must be run on a server (you're always #1 to me <3)"
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("JRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        return


async def ttl(url, message, client, args):
    global session
    start = time.time()
    try:
        async with session.get(url, timeout=60) as response:
            result = await response.text()
            end = time.time()
            await messagefuncs.sendWrappedMessage(
                f"{response.method} {response.url}: {response.status} {response.reason} in {(end - start):0.3g} seconds",
                message.channel,
            )
    except asyncio.TimeoutError:
        await messagefuncs.sendWrappedMessage(f"{url}: TimeoutEror", message.channel)


class sliding_puzzle:
    def __init__(self, message):
        self.channel = message.channel
        self.direction_parsing = defaultdict(str)
        self.direction_parsing["🇺"] = self.shift_up
        self.direction_parsing["⬆️"] = self.shift_up
        self.direction_parsing["u"] = self.shift_up
        self.direction_parsing["up"] = self.shift_up
        self.direction_parsing["🇩"] = self.shift_down
        self.direction_parsing["⬇️"] = self.shift_down
        self.direction_parsing["d"] = self.shift_down
        self.direction_parsing["down"] = self.shift_down
        self.direction_parsing["🇱"] = self.shift_left
        self.direction_parsing["⬅️"] = self.shift_left
        self.direction_parsing["l"] = self.shift_left
        self.direction_parsing["left"] = self.shift_left
        self.direction_parsing["🇷"] = self.shift_right
        self.direction_parsing["➡️"] = self.shift_right
        self.direction_parsing["r"] = self.shift_right
        self.direction_parsing["right"] = self.shift_right
        self.victory_msgs = ["You win!"]

        # make a solved board
        self.grid = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 0]]
        self.blank_x = 3
        self.blank_y = 3
        # scramble it with legal moves so it stays solvable
        for i in range(1000):
            move = random.choice(
                [self.shift_up, self.shift_down, self.shift_left, self.shift_right]
            )
            move()

    # move the tile below the empty space (0) up one if possible
    def shift_up(self):
        if self.blank_y == 3:
            return
        value_to_move = self.grid[self.blank_y + 1][self.blank_x]
        self.grid[self.blank_y][self.blank_x] = value_to_move
        self.grid[self.blank_y + 1][self.blank_x] = 0
        self.blank_y += 1

    # move the tile above the empty space (0) down one if possible
    def shift_down(self):
        if self.blank_y == 0:
            return
        value_to_move = self.grid[self.blank_y - 1][self.blank_x]
        self.grid[self.blank_y][self.blank_x] = value_to_move
        self.grid[self.blank_y - 1][self.blank_x] = 0
        self.blank_y -= 1

    # move the tile right of the empty space (0) left one if possible
    def shift_left(self):
        if self.blank_x == 3:
            return
        value_to_move = self.grid[self.blank_y][self.blank_x + 1]
        self.grid[self.blank_y][self.blank_x] = value_to_move
        self.grid[self.blank_y][self.blank_x + 1] = 0
        self.blank_x += 1

    # move the tile left of the empty space (0) right one if possible
    def shift_right(self):
        if self.blank_x == 0:
            return
        value_to_move = self.grid[self.blank_y][self.blank_x - 1]
        self.grid[self.blank_y][self.blank_x] = value_to_move
        self.grid[self.blank_y][self.blank_x - 1] = 0
        self.blank_x -= 1

    async def print(self, message):
        return await messagefuncs.sendWrappedMessage(message, self.channel)

    async def input(self, message, allowed_reactions, timeout=3600.0):
        waits = [
            client.wait_for(
                "raw_reaction_add",
                timeout=timeout,
                check=lambda reaction: (str(reaction.emoji) in allowed_reactions)
                and reaction.message_id == message.id,
            )
        ]
        if type(message.channel) == discord.DMChannel:
            waits.append(
                client.wait_for(
                    "raw_reaction_remove",
                    timeout=timeout,
                    check=lambda reaction: (str(reaction.emoji) in allowed_reactions)
                    and reaction.message_id == message.id,
                )
            )
        done, pending = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            response = await task
        try:
            if type(message.channel) != discord.DMChannel:
                await message.remove_reaction(
                    response.emoji, message.guild.get_member(response.user_id)
                )
        except discord.Forbidden:
            pass
        return str(response.emoji)

    async def play(self):
        exposition = """You see a grid of tiles built into the top of a pedestal. The tiles can slide around in the grid, but can't be removed without breaking them. There are fifteen tiles, taking up fifteen spaces in a 4x4 grid, so any of the tiles that are adjacent to the empty space can be slid into the empty space."""

        await self.print(exposition)
        self.moves = 0
        for row in range(4):
            if 0 in self.grid[row]:
                self.blank_y = row
        await self.pretty_print()
        allowed_reactions = ["⬆️", "⬇️", "⬅️", "➡️"]
        for reaction in allowed_reactions:
            await self.status_message.add_reaction(reaction)
        await asyncio.sleep(1)
        while True:
            direction = await self.input(self.status_message, allowed_reactions)
            direction = self.direction_parsing[direction]
            if direction != "":
                direction()
                self.moves += 1
            else:
                continue
            await self.pretty_print()
            if self.winning():
                return

    def winning(self):
        return self.grid == [
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 0],
        ]

    async def pretty_print(self):
        if self.winning():
            await self.print(
                f"{random.choice(self.victory_msgs)}\nMoves used: {self.moves}",
            )
            outstring = "☆☆☆☆☆☆☆☆\n"
        else:
            outstring = "Slide the tiles with the reactions below:\n"
        mapping = [
            "　",
            "①",
            "②",
            "③",
            "④",
            "⑤",
            "⑥",
            "⑦",
            "⑧",
            "⑨",
            "⑩",
            "⑪",
            "⑫",
            "⑬",
            "⑭",
            "⑮",
        ]
        for row in self.grid:
            for item in row:
                outstring += mapping[item]
            outstring += "\n"
        if not hasattr(self, "status_message"):
            self.status_message = await self.print(outstring)
        else:
            await self.status_message.edit(content=outstring)

    async def sliding_puzzle_function(message, client, args):
        try:
            puzzle = sliding_puzzle(message)
            return await puzzle.play()
        except asyncio.TimeoutError:
            await messagefuncs.sendWrappedMessage(
                "Puzzle failed due to timeout", message.channel
            )
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error("SPF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
            await message.add_reaction("🚫")


class Deck(object):
    def __init__(self):
        self.draw_pile = deque()
        self.discard_pile = deque()
        self.hands = list()

    def discard(self, *cards):
        self.discard_pile.extend(cards)

    def shuffle(self, discard_in=True):
        if discard_in:
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile = deque()
        draw_pile = list(self.draw_pile)
        random.shuffle(draw_pile)
        self.draw_pile = deque(draw_pile)

    def deal(self, number_of_hands=2, number_of_cards=7, exclude_hands=[]):
        self.hands = [deque() for i in range(number_of_hands)]
        for i in range(number_of_cards):
            for hand_offset_pointer in range(number_of_hands):
                if hand_offset_pointer not in exclude_hands:
                    self.draw(hand_offset_pointer, 1)

    def draw(self, hand_number, number_of_cards=1, reshuffle_on_empty=True):
        self.hands[hand_number]
        for i in range(number_of_cards):
            try:
                self.hands[hand_number].append(self.draw_pile.popleft())
            except IndexError as e:
                if reshuffle_on_empty:
                    self.shuffle(discard_in=True)
                    self.hands[hand_number].append(self.draw_pile.popleft())
                else:
                    raise e

    def peek(self, number_of_cards=1, show_remaining_if_empty=True):
        if number_of_cards > len(self.draw_pile) and show_remaining_if_empty:
            number_of_cards = len(self.draw_pile)
        return self.draw_pile[0:number_of_cards]

    async def load(self, attachment, append_to_deck=True):
        raw_str = (await attachment.read()).decode("UTF-8")
        cards = [Deck.Card.load_from_str(line) for line in raw_str.splitlines()]
        if append_to_deck:
            self.draw_pile.extend(cards)
        else:
            self.draw_pile = deque(cards)

    class Card(object):
        def __init__(self, name_of_card, rank=None, comment=""):
            self.name = name_of_card
            self.rank = int(rank) if rank else None
            self.comment = comment

        def load_from_str(raw_str, separator="\t"):
            tokens = raw_str.split(separator)
            if len(tokens) == 1:
                return Deck.Card(name_of_card=tokens[0])
            elif len(tokens) == 2:
                if tokens[1].isnumeric():
                    return Deck.Card(name_of_card=tokens[0], rank=tokens[1])
                else:
                    return Deck.Card(name_of_card=tokens[0], comment=tokens[1])
            elif len(tokens) == 3:
                return Deck.Card(
                    name_of_card=tokens[0], rank=tokens[1], comment=tokens[3]
                )
            else:
                raise ValueError(
                    f"Incorrect number of tokens ({len(tokens)}, must be 1-3) parsing {raw_str}"
                )

        def __str__(self):
            return f"Card __{'#'+str(self.rank)+' ' if self.rank else ''}{self.name}__"


async def card_choice_game_function(message, client, args):
    try:
        deck = Deck()
        if len(message.attachments) and message.attachments[0].filename.endswith(
            ".txt"
        ):
            await deck.load(message.attachments[0])
        if not len(deck.draw_pile):
            return await messagefuncs.sendWrappedMessage(
                "Unable to load cards for game (draw pile is empty).", message.channel
            )
        else:
            await messagefuncs.sendWrappedMessage(
                f"Loaded {len(deck.draw_pile)} cards from {message.attachments[0].filename}",
                message.channel,
            )

            class Player(object):
                def __init__(
                    self, hand_number=None, user=None, score=0, deck=None, hand=None
                ):
                    self.hand_number = hand_number
                    self.user = user
                    self.score = score
                    if hand:
                        self.hand = hand
                    else:
                        self.hand = deck.hands[hand_number]
                    self.deck = deck

                def card_names(self):
                    return [card.name.lower() for card in self.hand]

                def get_card_by_name(self, name):
                    i = self.card_names().index(name.lower())
                    return (i, self.hand[i])

                def pop(self, name):
                    card = self.get_card_by_name(name)
                    self.hand.remove(card[1])
                    if deck:
                        self.deck.discard(card[1])
                    return card

                def __str__(self):
                    return "; ".join([card.name for card in self.hand])

            deck.shuffle()
            deck.deal(len(message.mentions), 6)
            deck.draw(0, 1)
            players = deque(
                [
                    Player(i, message.mentions[i], deck=deck)
                    for i in range(len(deck.hands))
                ]
            )
            game_ongoing = True

            async def input_from_list(message, channel, options=[], timeout=3600.0):
                await messagefuncs.sendWrappedMessage(message, channel)
                response = await client.wait_for(
                    "message",
                    timeout=timeout,
                    check=lambda m: m.channel == channel
                    and m.clean_content.lower() in options,
                )

                return response.clean_content

            async def pick_card_from_hand(player, is_leader=False):
                options = player.card_names()
                options.append("pass")
                if is_leader:
                    options.append("quit")
                target = (
                    player.user.dm_channel
                    if player.user.dm_channel
                    else await player.user.create_dm()
                )
                return await input_from_list(
                    f"Pick a card from your hand to start the round.\nYour hand contains {player}. You can also say `PASS` to pass this round to the next leader{', or `QUIT` to end the game' if is_leader else ''}.",
                    target,
                    options,
                )

            async def scoreboard(players, channel, show_winner=False):
                scoreboard = list(sorted(players, key=lambda player: -player.score))
                message = "\n".join(
                    [
                        f"• {player.user.display_name}: {player.score} points"
                        for player in scoreboard
                    ]
                )
                if show_winner:
                    message = "__Final Scores__\n{message}\n{scoreboard[0].user.mention} is the winner!"
                return await messagefuncs.sendWrappedMessage(message, channel)

            while game_ongoing:
                leader = players[0]
                players.rotate()
                await scoreboard(players, message.channel)
                try:
                    choice = await pick_card_from_hand(leader, is_leader=True)
                except asyncio.TimeoutError:
                    choice = "PASS"
                if choice.lower() == "quit":
                    game_ongoing = False
                    continue
                elif choice.lower() == "pass":
                    continue
                else:
                    card = leader.pop(choice)[1]
                deck.deal(len(players), 1, exclude_hands=[leader.hand_number])
                status_message = None
                player_choices = players.copy()
                player_choices.pop()

                async def current_status(status_message, channel=None):
                    players_left = sum(
                        1 for player in player_choices if type(player) is Player
                    )
                    message = f"{leader.user.mention} chose {card}.\n"
                    if players_left:
                        message += f"Awaiting {players_left} players"
                    else:
                        message += f"Choice cards are {'; '.join([card.name for card in player_choices])}"
                    if not status_message:
                        return await messagefuncs.sendWrappedMessage(message, channel)
                    else:
                        await status_message.edit(content=message)

                status_message = await current_status(status_message, message.channel)

                async def choose_card(player, status_message):
                    try:
                        choice = await pick_card_from_hand(player, is_leader=False)
                    except asyncio.TimeoutError:
                        choice = "PASS"
                    player_choices[player_choices.index(player)] = (
                        None if choice.lower() == "pass" else player.pop(choice)[1]
                    )
                    await current_status(status_message)

                await asyncio.gather(
                    *[choose_card(player, status_message) for player in player_choices]
                )
                options = list(filter(lambda card: card is not None, player_choices))
                player = Player(hand=options, user=leader.user)
                try:
                    choice = await pick_card_from_hand(player, is_leader=True)
                except asyncio.TimeoutError:
                    choice = "quit"
                if choice.lower() == "quit":
                    game_ongoing = False
                    continue
                else:
                    winning_player = players[
                        player_choices.index(player.get_card_by_name(choice)[1])
                    ]
                    winning_player.score += 1
                    await messagefuncs.sendWrappedMessage(
                        f"Player {winning_player.user.mention} won that round! Their score is {winning_player.score}",
                        message.channel,
                    )
                    deck.discard(*options)
                    deck.deal(len(players), 1, exclude_hands=[leader.hand_number])
            await scoreboard(players, message.channel, show_winner=Trure)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("CCGF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        logger.info(traceback.format_exc())
        await message.add_reaction("🚫")


def memo_function(message, client, args):
    value = message.clean_content.split(args[0] + " ", 1)[1] if len(args) > 1 else None
    return ch.user_config(
        message.author.id,
        message.guild.id if message.guild else None,
        "memo-" + args[0],
        value=value,
        allow_global_substitute=True,
    )


async def ssc_function(message, client, args):
    try:
        url = None
        if len(args) == 0:
            async with session.get(
                "https://novalinium.com/sscd.archive.search.pl"
            ) as resp:
                return await messagefuncs.sendWrappedMessage(
                    resp.headers["Location"], target=message.channel
                )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SSC[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def thingiverse_function(message, client, args):
    try:
        if args[0] not in ("search", "me"):
            raise discord.errors.InvalidArgument("Unknown subcommand")
        base_url = "https://api.thingiverse.com"
        endpoint = {
            "search": f"/search/{' '.join(args[1:])}/",
            "me": "/users/me",
        }[args[0]]
        async with session.get(
            base_url + endpoint,
            headers={
                "Authorization": f"Bearer {ch.user_config(message.author.id, message.guild.id if message.guild else None, 'thingiverse_access_token', allow_global_substitute=True) or ch.config.get(section='thingiverse', key='access_token')}"
            },
        ) as resp:
            resp_obj = await resp.json()
            response = {
                "me": lambda resp_obj: f"Authenticated as {resp_obj['full_name']} (@{resp_obj['name']})",
                "search": lambda resp_obj: f"Top hit: {resp_obj['hits'][0]['public_url'] if resp_obj['total'] else 'No hits found.'}\n{resp_obj['total']} total result{'s' if resp_obj['total'] > 1 else ''}",
            }[args[0]](resp_obj)
            return await messagefuncs.sendWrappedMessage(
                response,
                target=message.channel,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("THV[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def inspirobot_function(message, client, args):
    try:
        base_url = "https://inspirobot.me/"
        endpoint = "api?generate=true"
        async with session.get(
            base_url + endpoint,
        ) as resp:
            return await messagefuncs.sendWrappedMessage(
                await resp.text(),
                target=message.channel,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("IB[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def complice_function(message, client, args):
    try:
        if args[0] not in ("info", "goals", "intention"):
            raise discord.errors.InvalidArgument("Unknown subcommand")
        base_url = "https://complice.co/api/v0/u/me/"
        endpoint = {
            "info": "userinfo.json",
            "goals": "goals/active.json",
            "intention": "intentions",
        }[args[0]]
        async with session.get(
            base_url + endpoint,
            headers={
                "Authorization": f"Bearer {ch.user_config(message.author.id, message.guild.id if message.guild else None, 'complice_access_token', allow_global_substitute=True)}"
            },
        ) as resp:
            return await messagefuncs.sendWrappedMessage(
                await resp.text(),
                target=message.channel,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SSC[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def ace_attorney_function(message, client, args):
    try:
        start = datetime.now()
        channel = (
            message.channel_mentions[0]
            if len(message.channel_mentions)
            else message.channel
        )
        logs = []
        if message.reference and message.type is not discord.MessageType.pins_add:
            args.insert(1, str(message.reference.message_id))
            if args[0] == "down":
                args[0] = str(message.id)
        if args[0].isnumeric() and int(args[0]) > 10000 and len(args) > 1:
            after = await channel.fetch_message(
                int(args[0]) if int(args[0]) < int(args[1]) else int(args[1])
            )
            before = await channel.fetch_message(
                int(args[0]) if int(args[0]) > int(args[1]) else int(args[1])
            )
            history = channel.history(oldest_first=False, after=after, before=before)
        else:
            after = None
            if not args[0].isnumeric() or (int(args[0]) < 0) or (int(args[0]) > 200):
                args[0] = 10
            if len(args) >= 2 and args[1].isnumeric():
                before = await channel.fetch_message(int(args[1]))
                limit = int(args[0]) - 1
            else:
                before = message
                limit = int(args[0])
            history = channel.history(oldest_first=False, limit=limit, before=before)
        async for historical_message in history:
            if historical_message.clean_content:
                if (
                    len(logs)
                    and logs[-1]["user"] != historical_message.author.display_name
                ) or not len(logs):
                    logs.append(
                        {
                            "user": historical_message.author.display_name,
                            "content": historical_message.clean_content,
                        }
                    )
                elif len(logs):
                    logs[-1][
                        "content"
                    ] = f"{historical_message.clean_content}\n{logs[-1]['content']}"
        if after and after.clean_content:
            if (len(logs) and logs[-1]["user"] != after.author.display_name) or not len(
                logs
            ):
                logs.append(
                    {
                        "user": after.author.display_name,
                        "content": after.clean_content,
                    }
                )
            elif len(logs):
                logs[-1]["content"] = f"{after.clean_content}\n{logs[-1]['content']}"
        logs.reverse()
        if before != message:
            logs.append(
                {
                    "user": before.author.display_name,
                    "content": before.clean_content,
                }
            )
        base_url = ch.config.get(section="ace", key="server_url")
        endpoint = ch.config.get(section="ace", key="endpoint")
        placeholder = await messagefuncs.sendWrappedMessage(
            f"Queued logs for aceattorneyfication...", target=message.channel
        )
        sent = datetime.now()
        with message.channel.typing():
            async with session.post(f"{base_url}{endpoint}", json=logs) as resp:
                buffer = io.BytesIO(await resp.read())
                await placeholder.delete()
                if resp.status != 200:
                    logger.debug(logs)
                    return await messagefuncs.sendWrappedMessage(
                        "File too big", target=message.channel, delete_after=30
                    )
                try:
                    total_time = (datetime.now() - start).total_seconds()
                    encoding_time = (datetime.now() - sent).total_seconds()
                    return await messagefuncs.sendWrappedMessage(
                        f"Courtroom scene for {message.author.mention} (rendered in {encoding_time} seconds)",
                        files=[discord.File(buffer, "objection.mp4")],
                        target=message.channel,
                    )
                except discord.HTTPException:
                    return await messagefuncs.sendWrappedMessage(
                        "File too big", target=message.channel, delete_after=30
                    )
    except discord.NotFound as e:
        await messagefuncs.sendWrappedMessage(
            "Could not find one of the messages used as arguments",
            target=message.channel,
            delete_after=30,
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("AAF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


async def style_transfer_function(message, client, args):
    try:
        url = None
        if len(message.attachments):
            lessage = message
            url = message.attachments[0].url
        elif len(message.embeds) and message.embeds[0].image.url != discord.Embed.Empty:
            lessage = message
            url = message.embeds[0].image.url
        elif (
            len(message.embeds)
            and message.embeds[0].thumbnail.url != discord.Embed.Empty
        ):
            lessage = message
            url = message.embeds[0].thumbnail.url
        elif len(args) > 1 and args[1]:
            lessage = message
            url = args[1]
        else:
            lessage = (
                await message.channel.history(limit=1, before=message).flatten()
            )[0]
            if len(lessage.attachments):
                url = lessage.attachments[0].url
            elif (
                len(lessage.embeds)
                and lessage.embeds[0].image.url != discord.Embed.Empty
            ):
                url = lessage.embeds[0].image.url
            elif (
                len(lessage.embeds)
                and lessage.embeds[0].thumbnail.url != discord.Embed.Empty
            ):
                url = lessage.embeds[0].thumbnail.url
        logger.debug(url)
        try:
            input_image_blob = await netcode.simple_get_image(url)
        except Exception as e:
            await message.add_reaction("🚫")
            await messagefuncs.sendWrappedMessage(
                f"Could not retrieve image with url {url} ({e})",
                message.channel,
                delete_after=60,
            )
            return
        input_image_blob.seek(0)
        base_url = ch.config.get(section="models", key="server_url")
        endpoint = ch.config.get(section="models", key="endpoint")
        params = aiohttp.FormData()
        params.add_field("style", args[0])
        params.add_field("file", input_image_blob)
        placeholder = await messagefuncs.sendWrappedMessage(
            "Queued image for style transfer...", target=message.channel
        )
        async with session.post(f"{base_url}{endpoint}", data=params) as resp:
            buffer = io.BytesIO(await resp.read())
            await placeholder.delete()
            if resp.status != 200:
                return await messagefuncs.sendWrappedMessage(
                    "File too big", target=message.channel
                )
            return await messagefuncs.sendWrappedMessage(
                files=[discord.File(buffer, "stylish.jpg")],
                target=message.channel,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("STF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


@cached(TTLCache(1024, 600))
async def arxiv_search_call(subj_content, exact=False):
    params = {
        "in": "",
        "query": f'"{subj_content}"' if exact else subj_content,
    }
    async with session.get(
        "http://search.arxiv.org:8081/",
        params=params,
    ) as resp:
        request_body = await resp.read()
        root = html.document_fromstring(request_body)
        links = root.xpath('//td[@class="snipp"]/a[@class="url"]')
        return f"{links[0].text_content().strip()}" if len(links) else None


@cached(TTLCache(1024, 600))
async def glowfic_search_call(subj_content, exact=False):
    params = aiohttp.FormData()
    params.add_field("commit", "Search")
    params.add_field(
        "subj_content",
        f'"{subj_content}"' if exact else subj_content,
    )
    async with session.get(
        f"https://glowfic.com/replies/search",
        data=params,
    ) as resp:
        request_body = (await resp.read()).decode("UTF-8")
        root = html.document_fromstring(request_body)
        links = root.xpath('//div[@class="post-edit-box"]/a')
        return f"https://glowfic.com{links[0].attrib['href']}" if len(links) else None


async def glowfic_search_function(message, client, args):
    try:
        try:
            q = filter(
                lambda line: line.startswith(">"), message.content.split("\n")
            ).__next__()
        except StopIteration:
            q = message.content.split("\n")[0]
        start = datetime.now()
        search_q = q.lstrip(">")
        link = None
        searched = []
        for database in glowfic_search_databases:
            if database["type"] == "cse":
                link = database["function"](search_q)
                link = link["items"][0]["link"] if len(link.get("items", [])) else None
            else:
                link = await database["function"](search_q)
            searched.append(database["name"])
            if link:
                break
        query_time = (datetime.now() - start).total_seconds()
        if link:
            content = f"{q}\nis from {link}"
        else:
            content = f"{q}\nattribution was not found, searched {len(glowfic_search_databases)} databases ({', '.join(searched)}) in {query_time} seconds."
        await messagefuncs.sendWrappedMessage(
            content,
            args[1],
        )
    except (StopIteration) as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug("GSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        return
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("GSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")


def amulet_function(message, client, args):
    c = message.content[8:].encode("utf-8")
    h = hashlib.sha256()
    h.update(c)
    return (
        dict(
            enumerate(
                [
                    "Not an amulet",
                    "Not an amulet",
                    "Not an amulet",
                    "Common amulet",
                    "Uncommon amulet",
                    "Rare amulet",
                    "Epic amulet",
                    "Legendary amulet",
                    "Mythic amulet",
                ]
            )
        ).get(len(max(re.findall(r"8+", h.digest().decode('ascii')))), "???????? amulet")
        if len(c) <= 64
        else "Too long, not poetic"
    )


async def autounload(ch):
    global session
    if session:
        await session.close()


def autoload(ch):
    global session
    global wikiClient
    global cseClient
    global glowfic_search_databases
    ch.add_command(
        {
            "trigger": [
                "!uwu",
                "<:uwu:445116031204196352>",
                "<:uwu:269988618909515777>",
                "<a:rainbowo:493599733571649536>",
                "<:owo:487739798241542183>",
                "<:owo:495014441457549312>",
                "<a:OwO:508311820411338782>",
                "!good",
                "!aww",
            ],
            "function": uwu_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "uwu",
        }
    )
    ch.add_command(
        {
            "trigger": ["!thing"],
            "function": thingiverse_function,
            "long_run": "channel",
            "async": True,
            "args_num": 2,
            "args_name": ["[search]", "query"],
            "description": "Searches thingiverse for a thing",
        }
    )
    ch.add_command(
        {
            "trigger": ["!stylish"],
            "function": style_transfer_function,
            "long_run": "channel",
            "async": True,
            "args_num": 1,
            "args_name": ["[wave|mosaic|candy|pencil]", "[url to image] (optional)"],
            "description": "Transfers style to image attachment, current styles available listed above",
        }
    )
    ch.add_command(
        {
            "trigger": ["!pick"],
            "function": pick_function,
            "async": True,
            "args_num": 1,
            "args_name": [],
            "description": "pick among comma seperated choices",
        }
    )
    ch.add_command(
        {
            "trigger": ["!roll"],
            "function": roll_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Roll dice in #d# format",
        }
    )
    ch.add_command(
        {
            "trigger": ["!dumpling"],
            "function": lambda message, client, args: "🥟",
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "Domp",
            "hidden": True,
        }
    )
    ch.add_command(
        {
            "trigger": ["!ifeellikeshit"],
            "function": lambda message, client, args: "<:ghost_hug:630502841181667349> have a flowchart: https://philome.la/jace_harr/you-feel-like-shit-an-interactive-self-care-guide/play/index.html",
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "FiO link",
            "hidden": True,
        }
    )
    ch.add_command(
        {
            "trigger": ["!bail"],
            "function": lambda message, client, args: f"Looks like {message.author.display_name} is bailing out on this one - good luck!",
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "Bail out",
            "hidden": True,
        }
    )
    ch.add_command(
        {
            "trigger": ["!fio", "!optimal"],
            "function": lambda message, client, args: "https://www.fimfiction.net/story/62074/8/friendship-is-optimal/",
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "FiO link",
            "hidden": True,
        }
    )
    ch.add_command(
        {
            "trigger": ["!shindan", "📛"],
            "function": shindan_function,
            "async": True,
            "args_num": 0,
            "long_run": "author",
            "args_name": [],
            "description": "Embed shindan",
        }
    )
    ch.add_command(
        {
            "trigger": ["!scp"],
            "function": scp_function,
            "async": True,
            "args_num": 0,
            "long_run": True,
            "args_name": [],
            "description": "SCP Function",
        }
    )
    ch.add_command(
        {
            "trigger": ["!retrowave"],
            "function": retrowave_function,
            "async": True,
            "args_num": 0,
            "long_run": True,
            "args_name": [
                "Up to 16 characters",
                "Up to 13 characters",
                "Up to 27 characters",
            ],
            "description": "Retrowave Text Generator. Arguments are bucketed in batches of three, with 16 characters for the top row, 13 for the middle row, and 27 for the bottom row. Non alphanumeric characters are stripped. To set your own divisions, add slashes.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!quoteadd", "🗨"],
            "function": qdb_add_function,
            "async": True,
            "hidden": True,
            "args_num": 0,
            "args_name": ["quote link"],
            "description": "Add to quote database",
        }
    )
    ch.add_command(
        {
            "trigger": ["!quoteget"],
            "function": qdb_get_function,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "args_name": ["quote id"],
            "description": "Get from quote database by id number",
        }
    )
    ch.add_command(
        {
            "trigger": ["!quotesearch"],
            "function": qdb_search_function,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "args_name": ["keyword"],
            "description": "Get from quote database by keyword",
        }
    )
    ch.add_command(
        {
            "trigger": ["!pingme"],
            "function": lambda message, client, args: f"Pong {message.author.mention}!",
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": [],
            "description": "Pong with @ in response to ping",
        }
    )
    ch.add_command(
        {
            "trigger": ["!ping"],
            "function": lambda message, client, args: f"Pong!",
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": [],
            "description": "Pong in response to ping",
        }
    )
    ch.add_command(
        {
            "trigger": ["!fling"],
            "function": lambda message, client, args: f"(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ {message.content[7:]}",
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": [],
            "description": "Fling sparkles!",
        }
    )
    ch.add_command(
        {
            "trigger": ["!rank"],
            "function": join_rank_function,
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": ["@member (optional)"],
            "description": "Check what number member you (or mentioned user) were to join this server.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!nextfullmoon"],
            "function": lambda message, client, args: ephem.next_full_moon(
                datetime.now()
            ),
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": [],
            "description": "Next full moon time",
        }
    )
    ch.add_command(
        {
            "trigger": ["!nextnewmoon"],
            "function": lambda message, client, args: ephem.next_new_moon(
                datetime.now()
            ),
            "async": False,
            "args_num": 0,
            "long_run": False,
            "args_name": [],
            "description": "Next new moon time",
        }
    )
    ch.add_command(
        {
            "trigger": ["!onthisday"],
            "function": wiki_otd_function,
            "async": True,
            "args_num": 0,
            "long_run": True,
            "args_name": ["Month Day# (January 1)"],
            "description": "Wikipedia On This Day",
        }
    )
    ch.add_command(
        {
            "trigger": ["!lifx"],
            "function": lifx_function,
            "async": True,
            "args_num": 1,
            "long_run": True,
            "args_name": ["Color", "[Selector]"],
            "description": "Set color of LIFX bulbs",
        }
    )
    ch.add_command(
        {
            "trigger": ["!mycolor", "!mycolour"],
            "function": lambda message, client, args: "Your color is #%06x"
            % message.author.colour.value,
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "Get Current Color",
        }
    )
    ch.add_command(
        {
            "trigger": ["!color"],
            "function": lambda message, client, args: "Current color is #{message.mentions[0].colour.value:06x}"
            if len(message.mentions)
            else "No user @mention found.",
            "async": False,
            "args_num": 1,
            "args_name": ["User mention"],
            "description": "Get Current Color for @ed user",
        }
    )
    ch.add_command(
        {
            "trigger": ["!thank you"],
            "function": lambda message, client, args: messagefuncs.add_reaction(
                message, random.choice(uwu_responses["reaction"])
            ),
            "async": True,
            "hidden": True,
            "args_num": 0,
        }
    )
    ch.add_command(
        {
            "trigger": ["!xkcd"],
            "function": lambda message, client, args: f"https://xkcd.com/{'_'.join(args)}",
            "async": False,
            "args_num": 0,
            "args_name": ["Comic #"],
            "description": "Show today's XKCD (or number)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!wiki"],
            "function": lambda message, client, args: f"https://en.wikipedia.org/wiki/{'_'.join(args)}",
            "async": False,
            "args_num": 1,
            "args_name": ["Article name"],
            "description": "Search wikipedia for article",
        }
    )
    ch.add_command(
        {
            "trigger": ["!fox"],
            "function": fox_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "^W^",
        }
    )
    ch.add_command(
        {
            "trigger": ["!dog", "!pupper"],
            "function": dog_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Woof!",
        }
    )
    ch.add_command(
        {
            "trigger": ["!glowup"],
            "function": partial(ttl, "https://glowfic.com"),
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Check if Glowfic site is up",
        }
    )
    ch.add_command(
        {
            "trigger": ["!slidingpuzzle"],
            "function": sliding_puzzle.sliding_puzzle_function,
            "async": True,
            "hidden": True,
            "args_num": 0,
            "args_name": [],
            "description": "A fun little sliding puzzle",
        }
    )
    ch.add_command(
        {
            "trigger": ["!memo"],
            "function": memo_function,
            "async": False,
            "hidden": False,
            "args_num": 1,
            "args_name": ["memo key", "value"],
            "description": "Take a personal memo to be retrieved later",
        }
    )
    ch.add_command(
        {
            "trigger": ["!slash"],
            "function": card_choice_game_function,
            "async": True,
            "hidden": True,
            "args_num": 2,
            "args_name": ["@player1 @player2 ...", "Attachment: deck"],
            "description": "Card choice game",
        }
    )
    ch.add_command(
        {
            "trigger": ["!inspire"],
            "function": inspirobot_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Generates an inspiring message.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!ace"],
            "function": ace_attorney_function,
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": [
                "number of messages to include",
                "[optional message id of ending message]",
                "[optional channel tag to retrieve messages from]",
            ],
            "description": "Turn logs into Ace Attorney court scene.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!complice"],
            "function": complice_function,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "args_name": ["info|goals|intention"],
            "description": "Complice functionality, uses subcommands. `!login complice` to authorize this command",
        }
    )
    ch.add_command(
        {
            "trigger": ["!amulet"],
            "function": amulet_function,
            "async": False,
            "hidden": False,
            "args_num": 1,
            "args_name": ["Poem"],
            "description": "Check amulet status",
        }
    )
    ch.add_command(
        {
            "trigger": [
                "<:glowfic_const_search_quote:796416363312185384>",
                "<:glowsearch:799184607555747870>",
                "<:glowsearch:799817787593457744>",
                "<:glowsearch:811320496883892279>",
            ],
            "function": glowfic_search_function,
            "async": True,
            "hidden": True,
            "whitelist_guild": [
                294167563447828481,
                401181628015050773,
                617953490383405056,
                606896038183436318,
                542027203383394304,
            ],
            "args_num": 0,
            "args_name": [],
            "description": "Search for quotes in this message to return the relevant Glowfic site reply",
        }
    )
    if not wikiClient:
        wikiClient = wikidata.Client()
    if not cseClient and config.get(section="google", key="cse_key"):
        cseClient = (
            build(
                "customsearch",
                "v1",
                developerKey=config.get(section="google", key="cse_key"),
            )
            .cse()
            .list
        )
    glowfic_search_databases = [
        {
            "function": partial(glowfic_search_call, exact=True),
            "name": "Constellation",
            "type": "native",
        },
        {
            "function": glowfic_search_call,
            "name": "Constellation Fuzzy Search",
            "type": "native",
        },
        *[
            {
                "function": lru_cache()(
                    lambda q: cseClient(exactTerms=q, cx=engine[1]).execute()
                ),
                "name": engine[0],
                "type": "cse",
            }
            for engine in [
                engine.split("=", 1)
                for engine in config.get(
                    section="quotesearch", key="extra-cse-list", default=[]
                )
            ]
        ],
        {
            "function": partial(arxiv_search_call, exact=True),
            "name": "arXiv Full Text Search",
            "type": "native",
        },
    ]
    if not session:
        session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
            }
        )
