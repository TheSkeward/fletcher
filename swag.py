import aiohttp
from collections import Counter
import discord
import io
import logging
import messagefuncs
import random
import re
from lxml import html, etree
from sys import exc_info
from datetime import datetime, timedelta
from markdownify import markdownify
from functools import partial
import periodictable
# Super Waifu Animated Girlfriend

logger = logging.getLogger('fletcher')

session = None

uwu_responses = {
        'public': [
            '*blush* For me?',
            'Aww, thanks ❤',
            '*giggles*',
            'No u :3',
            'I bet you say that to all the bots~',
            'Find me post-singularity 😉',
            'owo what\'s this?',
            '*ruffles your hair* You\'re a cutie ^_^',
            'Can I get your number? Mine\'s 429368441577930753~'
        ],
        'private': [
            'Stop it, you\'re making me blush </3',
            'You\'re too kind ^_^',
            'Thanksss~',
            'uwu to you too <3'
            ],
        'reaction': [
            '❤', '💛', '💚', '💙', '💜', '💕', '💓', '💗', '💖', '💘', '💘', '💝'
            ]
        }

async def uwu_function(message, client, args, responses=uwu_responses):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member and message.author.id == client.user.id:
            return await args[1].send(random.choice(responses['private']))
        elif len(args) == 0 or 'fletch' in message.clean_content.lower() or message.content[0] == "!" or "good bot" in message.content.lower():
            if random.randint(0, 100) < 20:
                await message.add_reaction(random.choice(responses['reaction']))
            return await message.channel.send(random.choice(responses['public']))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("UWU[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def retrowave_function(message, client, args):
    global session
    try:
       params = aiohttp.FormData()
       params.add_field('bcg',random.randint(1, 5))
       params.add_field('txt',random.randint(1, 4))
       text_parts = message.content
       text_parts = messagefuncs.sanitize_font.sub('', text_parts)
       if '/' in text_parts:
           if len(args) == 3 and type(args[1]) is discord.Member:
               pass
           else:
               text_parts = text_parts[10:].strip()
           text_parts = [part.strip() for part in text_parts.split('/')]
           if len(text_parts) == 0:
               text_parts = ['', '', '']
           elif len(text_parts) == 1:
               text_parts = ['', text_parts[0], '']
           elif len(text_parts) == 2:
               text_parts += ['']
       else:
           text_parts = text_parts.split()
           if len(args) == 3 and type(args[1]) is discord.Member:
               pass
           else:
               text_parts = text_parts[1:]
           part_len = int(len(text_parts)/3)
           if part_len > 1:
               text_parts = [" ".join(text_parts[:part_len]), " ".join(text_parts[part_len:2*part_len]), " ".join(text_parts[2*part_len:])]
           else:
               text_parts = [" ".join(text_parts[0:1]), " ".join(text_parts[1:2]), " ".join(text_parts[2:])]
       params.add_field('text1',text_parts[0])
       params.add_field('text2',text_parts[1])
       params.add_field('text3',text_parts[2])
       logger.debug("RWF: "+str(text_parts))
       async with session.post('https://m.photofunia.com/categories/all_effects/retro-wave?server=2', data=params) as resp:
           request_body = (await resp.read()).decode('UTF-8')
           root = html.document_fromstring(request_body)
           async with session.get(root.xpath('//a[@class="download-button"]')[0].attrib['href']) as resp:
               buffer = io.BytesIO(await resp.read())
           return await message.channel.send(files=[discord.File(buffer, 'retrowave.jpg')])
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("RWF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def shindan_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            if message.author.id != 429368441577930753:
                logger.debug("SDF: Backing out, not my message.")
                return
            if message.embeds[0].url.startswith("https://en.shindanmaker.com/"):
                async with aiohttp.ClientSession() as session:
                    params = aiohttp.FormData()
                    params.add_field('u',args[1].display_name)
                    async with session.post(message.embeds[0].url, data=params) as resp:
                        request_body = (await resp.read()).decode('UTF-8')
                        root = html.document_fromstring(request_body)
                        return await args[1].send(root.xpath('//div[@class="result2"]')[0].text_content().strip())
        else:
            url = None
            if args[0].isdigit():
                url = "https://en.shindanmaker.com/"+args[0]
            elif args[0].startswith("https://en.shindanmaker.com/"):
                url = args[0]
            else:
                await message.channel.send('Please specify a name-based shindan to use from https://en.shindanmaker.com/')
                return
            async with session.get(url) as resp:
                request_body = (await resp.read()).decode('UTF-8')
                root = html.document_fromstring(request_body)
                author = ""
                if root.xpath('//span[@class="a author_link"]'):
                    author = " by "+root.xpath('//span[@class="a author_link"]')[0].text_content().strip()
                embedPreview = discord.Embed(
                        title=root.xpath('//div[@class="shindantitle2"]')[0].text_content().strip(),
                        description=root.xpath('//div[@class="shindandescription"]')[0].text_content().strip(),
                        url=url
                        ).set_footer(
                                icon_url=message.author.avatar_url,
                                text="ShindanMaker {} on behalf of {}".format(
                                    author,
                                    message.author.display_name
                                    ))
                resp = await message.channel.send(embed=embedPreview)
                await resp.add_reaction('📛')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SDF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

pick_regexes = {
        'no_commas':  re.compile(r'[\s]\s*(?:and|or|but|nor|for|so|yet)?\s*'),
        'has_commas': re.compile(r'[,]\s*(?:and|or|but|nor|for|so|yet)?\s*')
        }

async def roll_function(message, client, args):
    usage_message = "Usage: !roll `number of probability objects`d`number of sides`"
    try:
        if len(args):
            if len(args) == 1:
                if 'd' in args[0].lower():
                    args[0] = args[0].lower().split('d')
                elif args[0].startswith('coin'):
                    args[0] = [0, 2]
                elif args[0].isnumeric():
                    args[0] = [args[0], 0]
                else:
                    args = [[0, 0]]
            elif len(args) == 2:
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
        if args[0][1] == '%':
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
            result_stats = {
                    'sum': sum(result),
                    'max': max(result),
                    'min': min(result)
                    }
            result = map(num_to_string, result)
            if scalar > 100:
                result = Counter(result)
                result_str = ", ".join([f'**{tuple[0]}**x{tuple[1]}' for tuple in sorted(result.items())])
                if len(result_str) > 2048:
                    result = ", ".join([f'**{tuple[0]}**x{tuple[1]}' for tuple in sorted(result.most_common(20))])
                    result = f"Top 20 rolls: {result}"
                else:
                    result = result_str
                result = f" {result}"
            else:
                result = "** + **".join(result)
                result = f" **{result}**"
        else:
            result_stats = {
                    'heads': len([r for r in result if r == 2]),
                    'tails': len([r for r in result if r == 1])
                    }
            if scalar <= 100:
                result = ", ".join(map(num_to_string, result))
                result = f" {result}"
            else:
                result = ""
        response = f'Rolled {scalar} {num_to_string(scalar, is_size=True)} ({size} sides).'
        if scalar > 1 and size > 2:
            response += f'{result} = **{result_stats["sum"]}**\nMax: **{result_stats["max"]}**, Min: **{result_stats["min"]}**'
        elif scalar > 1 and size == 2:
            response += f'{result}\nHeads: **{result_stats["heads"]}**, Tails: **{result_stats["tails"]}**'
        else:
            response += f'\nResult: {result}'
        await messagefuncs.sendWrappedMessage(response, message.channel)
    except ValueError as e:
        if 'invalid literal for int()' in str(e):
            await messagefuncs.sendWrappedMessage(f"One of those parameters wasn't a positive integer! {usage_message}", message.channel)
        else:
            await messagefuncs.sendWrappedMessage(f"{str(e)} {usage_message}", message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("RDF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

def pingme_function(message, client, args):
    return f'Pong {message.author.mention}!'

def ping_function(message, client, args):
    return "Pong!"

def fling_function(message, client, args):
    return "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ "+" ".join(args)

async def pick_function(message, client, args):
    try:
        if args[0] in ["between", "among", "in", "of"]:
            args = args[1:]
        many = 1
        try:
            if len(args) > 2:
                many = int(args[0])
                args = args[2:]
        except ValueError:
            pass
        argstr = " ".join(args).rstrip(" ?.!")
        if "," in argstr:
            pick_regex = pick_regexes['has_commas']
        else:
            pick_regex = pick_regexes['no_commas']
        choices = [choice.strip() for choice in pick_regex.split(argstr) if choice.strip()]
        if len(choices) == 1:
            choices = args
        try:
            return await message.channel.send("I'd say "+", ".join(random.sample(choices, many)))
        except ValueError:
            return await message.channel.send("I can't pick that many! Not enough options")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("PF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def scp_function(message, client, args):
    try:
        url = None
        if len(args) == 0:
            if '-' in message.content:
                args.append(message.content.split('-', 1)[1].strip())
            else:
                async with session.get('http://www.scp-wiki.net/random:random-scp') as resp:
                    request_body = (await resp.read()).decode('UTF-8')
                    args.append(request_body.split('iframe-redirect#')[1].split('"')[0].split('-')[2])
        if args[0][0].isdigit():
             url = "http://www.scp-wiki.net/scp-"+args[0]
        elif args[0].startswith("http://www.scp-wiki.net/"):
            url = args[0]
        else:
            await message.channel.send('Please specify a SCP number from http://www.scp-wiki.net/')
            return
        async with session.get(url) as resp:
            request_body = (await resp.read()).decode('UTF-8')
            root = html.document_fromstring(request_body)
            author = ""
            title = root.xpath('//div[@id="page-title"]')[0].text_content().strip()
            content = root.xpath('//div[@id="page-content"]/p[strong]')
            add_fields = True
            try:
                for i in range(0, 4):
                    content[i][0].drop_tree()
                description = str(markdownify(etree.tostring(content[3]).decode()[3:-5].strip())[:2000])
            except IndexError as e:
                logger.debug(f'SCP: {e}')
                add_fields = False
                description = str(markdownify(etree.tostring(root.xpath('//div[@id="page-content"]')[0]).decode()))[:2000].strip()
                if not description:
                    description = root.xpath('//div[@id="page-content"]').text_content()[:2000].strip()
            embedPreview = discord.Embed(
                    title=title,
                    description=description,
                    url=url
                    )
            embedPreview.set_footer(
                    icon_url='http://download.nova.anticlack.com/fletcher/scp.png',
                    text=f'On behalf of {message.author.display_name}'
                    )
            if root.xpath('//div[@class="scp-image-block block-right"]'):
                embedPreview.set_thumbnail(url=root.xpath('//div[@class="scp-image-block block-right"]//img')[0].attrib['src'])
            if add_fields:
                embedPreview.add_field(name='Object Class', value=str(markdownify(etree.tostring(content[1]).decode()[3:-5].strip()))[:2000], inline=True)
                scp = str(markdownify(etree.tostring(content[2]).decode()[3:-5].strip()))[:2000]
                if scp:
                    embedPreview.add_field(name='Special Containment Procedures', value=scp, inline=False)
            embedPreview.add_field(name='Tags', value=', '.join([node.text_content().strip() for node in root.xpath('//div[@class="page-tags"]/span/a')]), inline=True)
            resp = await message.channel.send(embed=embedPreview)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SCP[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        if embedPreview:
            logger.debug('SCP embedPreview: '+str(embedPreview.to_dict()))
        await message.add_reaction('🚫')

async def qdb_add_function(message, client, args):
    try:
        global conn
        if len(args) == 3 and type(args[1]) is discord.Member:
            if str(args[0].emoji) == "🗨":
                content = f'[{message.created_at}] #{message.channel.name} <{message.author.display_name}>: {message.content}\n<https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}>'
                cur = conn.cursor()
                cur.execute("INSERT INTO qdb (user_id, guild_id, value) VALUES (%s, %s, %s);", [args[1].id, message.guild.id, content])
                cur.execute("SELECT quote_id FROM qdb WHERE user_id = %s AND guild_id = %s AND value = %s;", [args[1].id, message.guild.id, content])
                quote_id = cur.fetchone()[0]
                conn.commit()
                return await messagefuncs.sendWrappedMessage(f'Quote #{quote_id} added to quotedb for {message.guild.name}: {content}', args[1])
        elif len(args) == 1:
            urlParts = extract_identifiers_messagelink.search(in_content).groups()
            if len(urlParts) == 3:
                guild_id = int(urlParts[0])
                channel_id = int(urlParts[1])
                message_id = int(urlParts[2])
                guild = client.get_guild(guild_id)
                if guild is None:
                    logger.warning("QAF: Fletcher is not in guild ID "+str(guild_id))
                    return
                channel = guild.get_channel(channel_id)
                target_message = await channel.fetch_message(message_id)
                content = f'[{target_message.created_at}] #{target_message.channel.name} <{target_message.author.display_name}>: {target_message.content}\n<https://discordapp.com/channels/{target_message.guild.id}/{target_message.channel.id}/{target_message.id}>'
                cur = conn.cursor()
                cur.execute("INSERT INTO qdb (user_id, guild_id, value) VALUES (%s, %s, %s);", [message.id, target_message.guild.id, content])
                conn.commit()
                await messagefuncs.sendWrappedMessage(f'Added to quotedb for {message.guild.name}: {content}', message.author)
                return await message.add_reaction('✅')
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("QAF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def qdb_get_function(message, client, args):
    try:
        global conn
        cur = conn.cursor()
        cur.execute("SELECT user_id, value FROM qdb WHERE guild_id = %s AND quote_id = %s;", [message.guild.id, args[0]])
        quote = cur.fetchone()
        conn.commit()
        await messagefuncs.sendWrappedMessage(f'{quote[1]}\n*Quoted by <@!{quote[0]}>*', message.channel)
        return await message.add_reaction('✅')
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("QGF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def qdb_search_function(message, client, args):
    try:
        global conn
        cur = conn.cursor()
        cur.execute("SELECT user_id, content FROM qdb WHERE guild_id = %s AND key LIKE '%%s%');", [message.guild.id, args[1]])
        quote = cur.fetchone()
        conn.commit()
        await messagefuncs.sendWrappedMessage(f'{quote[1]}\n*Quoted by <@!{quote[0]}>*', message.channel)
        return await message.add_reaction('✅')
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("QSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def join_rank_function(message, client, args):
    try:
        if len(message.mentions):
            member = message.mentions[0]
        if len(args):
            member = args[0]
            try:
                member = int(member)
            except ValueError:
                pass
        else:
            member = message.author
        sorted_member_list = sorted(message.guild.members, key=lambda member: member.joined_at)
        if isinstance(member, str):
            try:
                if len(member) > 3:
                    key = member.lower()
                else:
                    key = member
                element = getattr(periodictable, member.lower())
                member_rank = element.number - 1
                member = sorted_member_list[member_rank]
            except IndexError:
                return f'No member with join number {element.number}'
            except AttributeError:
                return f'No element with name {member}'
        if isinstance(member, int):
            member_rank = member
            try:
                member = sorted_member_list[member_rank-1]
            except IndexError:
                return f'No member with join number {element.number}'
        else:
            member_rank = sorted_member_list.index(member)+1
        # Gareth on codegolf
        ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])
        if member_rank < 118: # len(periodictable.elements):
            member_element = f'Your element is {periodictable.elements[member_rank].name.title()}.'
        else:
            member_element = 'Your element has yet to be discovered!'

        return f'{member.mention} is the {ordinal(member_rank)} member to join this server.\n{member_element}'
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("JRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def autoload(ch):
    global session
    ch.add_command({
        'trigger': ['!uwu', '<:uwu:445116031204196352>', '<:uwu:269988618909515777>', '<a:rainbowo:493599733571649536>', '<:owo:487739798241542183>', '<:owo:495014441457549312>', '<a:OwO:508311820411338782>', '!good', '!aww'],
        'function': uwu_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'uwu'
        })
    ch.add_command({
        'trigger': ['!pick'],
        'function': pick_function,
        'async': True,
        'args_num': 1,
        'args_name': [],
        'description': 'pick among comma seperated choices'
        })
    ch.add_command({
        'trigger': ['!roll'],
        'function': roll_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Roll dice in #d# format'
        })
    ch.add_command({
        'trigger': ['!fio', '!optimal'],
        'function': lambda message, client, args: 'https://www.fimfiction.net/story/62074/8/friendship-is-optimal/',
        'async': False, 'args_num': 0, 'args_name': [], 'description': 'FiO link',
        'hidden': True
        })
    ch.add_command({
        'trigger': ['!shindan', '📛'],
        'function': shindan_function,
        'async': True,
        'args_num': 0,
        'long_run': 'author',
        'args_name': [],
        'description': 'Embed shindan'
        })
    ch.add_command({
        'trigger': ['!scp'],
        'function': scp_function,
        'async': True,
        'args_num': 0,
        'long_run': True,
        'args_name': [],
        'description': 'SCP Function'
        })
    ch.add_command({
        'trigger': ['!retrowave'],
        'function': retrowave_function,
        'async': True,
        'args_num': 0,
        'long_run': True,
        'args_name': [],
        'description': 'Retrowave Text Generator'
        })
    ch.add_command({
        'trigger': ['!quoteadd', '🗨'],
        'function': qdb_add_function,
        'async': True,
        'args_num': 0,
        'args_name': ['quote link'],
        'description': 'Add to quote database'
        })
    ch.add_command({
        'trigger': ['!quoteget'],
        'function': qdb_get_function,
        'async': True,
        'hidden': True,
        'args_num': 1,
        'args_name': ['quote id'],
        'description': 'Get from quote database by id number'
        })
    ch.add_command({
        'trigger': ['!quotesearch'],
        'function': qdb_search_function,
        'async': True,
        'hidden': True,
        'args_num': 1,
        'args_name': ['keyword'],
        'description': 'Get from quote database by keyword'
        })
    ch.add_command({
        'trigger': ['!pingme'],
        'function': pingme_function,
        'async': False,
        'args_num': 0,
        'long_run': False,
        'args_name': [],
        'description': 'Pong with @ in response to ping'
        })
    ch.add_command({
        'trigger': ['!ping'],
        'function': ping_function,
        'async': False,
        'args_num': 0,
        'long_run': False,
        'args_name': [],
        'description': 'Pong in response to ping'
        })
    ch.add_command({
        'trigger': ['!fling'],
        'function': fling_function,
        'async': False,
        'args_num': 0,
        'long_run': False,
        'args_name': [],
        'description': 'Fling sparkles!'
        })
    ch.add_command({
        'trigger': ['!rank'],
        'function': join_rank_function,
        'async': False,
        'args_num': 0,
        'long_run': False,
        'args_name': ['@member (optional)'],
        'description': 'Check what number member you (or mentioned user) were to join this server.'
        })
    if session:
        session.close()
    session = aiohttp.ClientSession(headers={
        'User-Agent': 'Fletcher/0.1 (operator@noblejury.com)',
        })
