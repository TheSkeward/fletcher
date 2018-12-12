# bot.py
import asyncio
import codecs
import configparser
from datetime import datetime, timedelta
import discord
import importlib
import io
import math
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import psycopg2
import re
import signal
from sys import exc_info
import textwrap

"""fletcher=# \d parlay
                                      Table "public.parlay"
    Column    |            Type             | Collation | Nullable |           Default            
--------------+-----------------------------+-----------+----------+------------------------------
 id           | integer                     |           | not null | generated always as identity
 name         | character varying(255)      |           |          | 
 description  | text                        |           |          | 
 lastmodified | timestamp without time zone |           |          | 
 members      | bigint[]                    |           |          | 
 channel      | bigint                      |           |          | 
 guild        | bigint                      |           |          | 
 created      | timestamp without time zone |           |          | CURRENT_TIMESTAMP
 ttl          | interval                    |           |          | 
Indexes:
    "parlay_name_must_be_guild_unique" UNIQUE CONSTRAINT, btree (name, guild)

fletcher=# \d sentinel
                                     Table "public.sentinel"
    Column    |            Type             | Collation | Nullable |           Default            
--------------+-----------------------------+-----------+----------+------------------------------
 id           | integer                     |           | not null | generated always as identity
 name         | character varying(255)      |           |          | 
 description  | text                        |           |          | 
 lastmodified | timestamp without time zone |           |          | 
 subscribers  | bigint[]                    |           |          | 
 triggercount | integer                     |           |          | 
 created      | timestamp without time zone |           |          | CURRENT_TIMESTAMP
 triggered    | timestamp without time zone |           |          | 
Indexes:
    "sentinel_name_must_be_globally_unique" UNIQUE CONSTRAINT, btree (name)

fletcher=# \d messagemap
               Table "public.messagemap"
   Column    |  Type  | Collation | Nullable | Default 
-------------+--------+-----------+----------+---------
 fromguild   | bigint |           |          | 
 toguild     | bigint |           |          | 
 fromchannel | bigint |           |          | 
 tochannel   | bigint |           |          | 
 frommessage | bigint |           |          | 
 tomessage   | bigint |           |          | 
Indexes:
    "messagemap_idx" btree (fromguild, fromchannel, frommessage)

"""

FLETCHER_CONFIG = '/pub/lin/.fletcherrc'

# command handler class

class CommandHandler:

    # constructor
    def __init__(self, client):
        self.client = client
        self.commands = []

    def add_command(self, command):
        self.commands.append(command)

    async def reaction_handler(self, reaction):
        messageContent = str(reaction.emoji)
        for command in self.commands:
            if messageContent.startswith(tuple(command['trigger'])) and (('admin' in command and user.guild_permissions.manage_webhooks) or 'admin' not in command):
                if command['args_num'] == 0:
                    channel = self.client.get_channel(reaction.channel_id)
                    message = await channel.get_message(reaction.message_id)
                    user = await self.client.get_user_info(reaction.user_id)
                    if str(user.id) in config['moderation']['blacklist-user-usage'].split(','):
                        print('Blacklisted command attempt by user')
                        return
                    if command['async']:
                        return await command['function'](message, self.client, [reaction, user])
                        break
                    else:
                        return await message.channel.send(str(command['function'](message, self.client, [reaction, user])))
                        break

    async def command_handler(self, message):
        global sid
        try:
            if message.channel.category_id is None or message.guild.get_channel(message.channel.category_id).name not in config['moderation']['blacklist-category'].split(','):
                sent_com_score = sid.polarity_scores(message.content)['compound']
                print("["+str(sent_com_score)+"] "+message.content)
                if sent_com_score <= float(config['moderation']['sent-com-score-threshold']) and message.webhook_id is None and message.guild.name in config['moderation']['guilds'].split(','):
                    await modreport_function(message, self.client, ("\n[Sentiment Analysis Combined Score "+str(sent_com_score)+'] '+message.content).split(' '))
            else:
                print("[Nil] "+message.content)
        except AttributeError as e:
            print("[Nil] "+message.content)
            pass
        if messagefuncs.extract_identifiers_messagelink.search(message.content):
            if str(message.author.id) not in config['moderation']['blacklist-user-usage'].split(','):
                return await messagefuncs.preview_messagelink_function(message, self.client, None)
        for command in self.commands:
            if message.content.startswith(tuple(command['trigger'])) and (('admin' in command and message.author.guild_permissions.manage_webhooks) or 'admin' not in command):
                print(command)
                args = message.content.split(' ')
                args = [item for item in args if item]
                args.pop(0)
                if str(message.author.id) in config['moderation']['blacklist-user-usage'].split(','):
                    print('Blacklisted command attempt by user')
                    return
                if command['args_num'] == 0:
                    if command['async']:
                        return await command['function'](message, self.client, args)
                        break
                    else:
                        return await message.channel.send(str(command['function'](message, self.client, args)))
                        break
                else:
                    if len(args) >= command['args_num']:
                        if command['async']:
                            return await command['function'](message, self.client, args)
                            break
                        else:
                            return await message.channel.send(str(command['function'](message, self.client, args)))
                            break
                    else:
                        return await message.channel.send('command "{}" requires {} argument(s) "{}"'.format(command['trigger'][0], command['args_num'], ', '.join(command['args_name'])))
                        break

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

client = discord.Client()
conn = psycopg2.connect(host=config['database']['host'],database=config['database']['tablespace'], user=config['database']['user'], password=config['database']['password'])


# token from https://discordapp.com/developers
token = config['discord']['botToken']

ch = None

# Submodules, reloaded in reload_function so no initialization is done
import sentinel
import mathemagical
import messagefuncs
import text_manipulators

sid = SentimentIntensityAnalyzer()

webhook_sync_registry = {
        'FromGuild:FromChannelName': {
            'fromChannelObject': None,
            'fromWebhook': None,
            'toChannelObject': None,
            'toWebhook': None
            }
        }

canticum_message = None
doissetep_omega =  None

def help_function(message, client, args):
    if len(args) > 0 and args[0] == "verbose":
        helpMessageBody = "\n".join(["`{}`: {}\nArguments ({}): {}".format("` or `".join(command['trigger']), command['description'], command['args_num'], " ".join(command['args_name'])) for command in ch.commands])
    else:
        helpMessageBody = "\n".join(["`{}`: {}".format("` or `".join(command['trigger']), command['description']) for command in ch.commands])
    return helpMessageBody

async def lastactive_channel_function(message, client, args):
    try:
        lastMonth = None
        before = True
        try:
            if args[0]:
                try:
                    lastMonth = datetime.utcnow().date() - timedelta(days=int(args[0]))
                except ValueError:
                    if args[1]:
                        if args[0].startswith("a"):
                            before = False
                        lastMonth = datetime.utcnow().date() - timedelta(days=int(args[1]))
                    pass
        except IndexError:
                    pass
        msg = ""
        for channel in message.channel.guild.text_channels:
            try:
                category_pretty = ""
                if channel.category_id:
                    category_pretty = " [{}]".format(client.get_channel(channel.category_id).name)
                created_at = (await channel.history(limit=1).flatten())[0].created_at
                created_pretty = pretty_date(created_at)
                if created_pretty:
                    created_pretty = " ({})".format(created_pretty)
                if lastMonth:
                    if (before and lastMonth < created_at.date()) or (not before and lastMonth > created_at.date()):
                        msg = "{}\n<#{}>{}: {}{}".format(msg, channel.id, category_pretty, created_at.isoformat(timespec='minutes'), created_pretty)
                else:
                        msg = "{}\n<#{}>{}: {}{}".format(msg, channel.id, category_pretty, created_at.isoformat(timespec='minutes'), created_pretty)
            except discord.NotFound as e:
                pass
            except discord.Forbidden as e:
                msg = "{}\n<#{}>{}: Forbidden".format(msg, channel.id, category_pretty)
                pass
        msg = '**Channel Activity:**{}'.format(msg)
        msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
        for chunk in msg_chunks:
            await message.channel.send(chunk)
    except Exception as e:
        print(e)

async def lastactive_user_function(message, client, args):
    try:
        lastMonth = None
        before = True
        try:
            if args[0]:
                try:
                    lastMonth = datetime.utcnow().date() - timedelta(days=int(args[0]))
                except ValueError:
                    if args[1]:
                        if args[0].startswith("a"):
                            before = False
                        lastMonth = datetime.utcnow().date() - timedelta(days=int(args[1]))
                    pass
        except IndexError:
                    pass
        if message.guild.large:
            client.request_offline_members(message.guild)
        users = {}
        for m in message.guild.members:
            users[m.id] = datetime.today() + timedelta(days=1)
        for channel in message.channel.guild.text_channels:
            async for message in channel.history(limit=None):
                try:
                    print("[{} <#{}>] <@{}>: {}".format(message.created_at, channel.id, message.author.id, message.content))
                    if message.created_at < users[message.author.id]:
                        users[message.author.id] = message.created_at
                except discord.NotFound as e:
                    pass
                except discord.Forbidden as e:
                    pass
        msg = '**User Activity:**{}'.format(msg)
        for user_id, last_active in users:
            if last_active == datetime.today() + timedelta(days=1):
                last_active = "None"
            else:
                last_active = pretty_date(last_active)
            msg = "{}\n<@{}>{}: {}".format(msg, user_id, last_active)
        msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
        for chunk in msg_chunks:
            await message.channel.send(chunk)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LSU[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def modreport_function(message, client, args):
    try:
        report_content = None
        plaintext = None
        if len(args) == 2 and type(args[1]) is discord.User:
            plaintext = message.content
            report_content = "Mod Report: #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to ".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id)
            await message.remove_reaction('👁‍🗨', args[1])
        else:
            plaintext = " ".join(args)
            report_content = "Mod Report: #{} ({}) https://discordapp.com/channels/{}/{}/{} ".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id)
        if message.channel.is_nsfw():
            report_content = report_content + await rot13_function(message, client, [plaintext, 'INTPROC'])
        else:
            report_content = report_content + plaintext
        for user_id in config['moderation']['mod-users'].split(','):
            modmail = await client.get_user(int(user_id)).send(report_content)
            if message.channel.is_nsfw():
                await modmail.add_react('🕜')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("MRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def rot13_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            return await args[1].send(codecs.encode(message.content, 'rot_13'))
        elif len(args) == 2 and args[1] == 'INTPROC':
            return codecs.encode(args[0], 'rot_13')
        else:
            messageContent = codecs.encode(" ".join(args), 'rot_13')
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction('🕜')
            try: 
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
    except Exception as e:
        return e

async def uwu_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User and message.author.id == client.user.id:
            return await args[1].send("Stop it, you're making me blush </3")
        elif len(args) == 0:
            return await message.channel.send('*blush* For me?')
    except Exception as e:
        return e

async def memfrob_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            return await args[1].send(text_manipulators.memfrob(message.content))
        else:
            messageContent = text_manipulators.memfrob(" ".join(args))
            botMessage = await message.channel.send(messageContent)
            await botMessage.add_reaction('🕦')
            try: 
                await message.delete()
            except discord.Forbidden as e:
                print("Forbidden to delete message in "+str(message.channel))
    except Exception as e:
        return e

async def reload_function(message=None, client=client, args=[]):
    try:
        global ch
        global conn
        global doissetep_omega
        config.read(FLETCHER_CONFIG)
        if message:
            await message.add_reaction('📝')
        await load_webhooks()
        if message:
            await message.add_reaction('↔')
        conn = psycopg2.connect(host=config['database']['host'],database=config['database']['tablespace'], user=config['database']['user'], password=config['database']['password'])
        if message:
            await message.add_reaction('💾')
        # Utility text manipulators Module
        importlib.reload(text_manipulators)
        if message:
            await message.add_reaction('⌨')
        ch = CommandHandler(client)
        # Utility Commands
        ch.add_command({
            'trigger': ['!help'],
            'function': help_function,
            'async': False,
            'args_num': 0,
            'args_name': [],
            'description': 'List commands and arguments'
            })
        
        ch.add_command({
            'trigger': ['!reload <@'+str(client.user.id)+'>'],
            'function': reload_function,
            'async': True,
            'admin': True,
            'args_num': 0,
            'args_name': [],
            'description': 'Reload config (admin only)'
            })
        if message:
            await message.add_reaction('🔧')
        # Sentinel Module
        importlib.reload(sentinel)
        sentinel.conn = conn
        ch.add_command({
            'trigger': ['!assemble', '!canvas'],
            'function': sentinel.assemble_function,
            'async': True,
            'args_num': 2,
            'args_name': ['int', 'string'],
            'description': 'Create a sentinel for assembling groups'
            })
        ch.add_command({
            'trigger': ['!pledge', '!join'],
            'function': sentinel.pledge_function,
            'async': True,
            'args_num': 1,
            'args_name': ['int'],
            'description': 'Salute a sentinel'
            })
        ch.add_command({
            'trigger': ['!defect'],
            'function': sentinel.defect_function,
            'async': True,
            'args_num': 1,
            'args_name': ['int'],
            'description': 'Turn away from a sentinel'
            })
        ch.add_command({
            'trigger': ['!banners'],
            'function': sentinel.listbanners_function,
            'async': False,
            'args_num': 0,
            'args_name': [],
            'description': 'List sentinels'
            })
        if message:
            await message.add_reaction('🎏')
        # Messages Module
        importlib.reload(messagefuncs)
        messagefuncs.config = config
        ch.add_command({
            'trigger': ['!teleport', '!portal'],
            'function': messagefuncs.teleport_function,
            'async': True,
            'args_num': 1,
            'args_name': ['string'],
            'description': 'Create a link bridge to another channel'
            })
        ch.add_command({
            'trigger': ['!message'],
            'function': messagefuncs.messagelink_function,
            'async': True,
            'args_num': 1,
            'args_name': ['string'],
            'description': 'Create a link to the message with ID `!message XXXXXX`'
            })
        ch.add_command({
            'trigger': ['!preview'],
            'function': messagefuncs.preview_messagelink_function,
            'async': True,
            'args_num': 1,
            'args_name': ['string'],
            'description': 'Retrieve message body by link (used internally to unwrap message links in chat)'
            })
        ch.add_command({
            'trigger': ['!bookmark', '🔖', '🔗'],
            'function': messagefuncs.bookmark_function,
            'async': True,
            'args_num': 0,
            'args_name': [],
            'description': 'DM the user a bookmark to the current place in conversation',
            })
        if message:
            await message.add_reaction('🔭')
        ch.add_command({
            'trigger': ['!lastactive_channel', '!lastactivity_channel', '!lsc'],
            'function': lastactive_channel_function,
            'async': True,
            'admin': True,
            'args_num': 0,
            'args_name': [],
            'description': 'List all available channels and time of last message (Admin)'
            })
        ch.add_command({
            'trigger': ['!lastactive_user', '!lastactivity_user', '!lsu'],
            'function': lastactive_user_function,
            'async': True,
            'admin': True,
            'args_num': 0,
            'args_name': [],
            'description': 'List all available users and time of last message (Admin)'
            })
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
        # Math modules
        importlib.reload(mathemagical)
        ch.add_command({
            'trigger': ['!math', '!latex'],
            'function': mathemagical.latex_render_function,
            'async': True,
            'args_num': 0,
            'args_name': [],
            'description': 'Render arguments as LaTeX formula (does not require `$$`)'
            })
        if message:
            await message.add_reaction('➕')
        ch.add_command({
            'trigger': ['!modreport', '👁‍🗨'],
            'function': modreport_function,
            'async': True,
            'args_num': 0,
            'args_name': [],
            'description': 'Report message to mods. Removed immediately after.'
            })
        ch.add_command({
            'trigger': ['!uwu', '<:uwu:445116031204196352>'],
            'function': uwu_function,
            'async': True,
            'args_num': 0,
            'args_name': [],
            'description': 'uwu'
            })
        if message:
            await message.add_reaction('🙉')
        if not doissetep_omega.is_playing():
            doissetep_omega.play(discord.FFmpegPCMAudio(config['audio']['instreamurl']))
        if message:
            await message.add_reaction('✅')
    except Exception as e:
        print(e)

# bot is ready
@client.event
async def on_ready():
    try:
        global doissetep_omega
        # print bot information
        print(client.user.name)
        print(client.user.id)
        print('Discord.py Version: {}'.format(discord.__version__))
        await client.change_presence(activity=discord.Game(name='liberapay.com/novalinium'))
        doissetep_omega = await client.get_guild(int(config['audio']['guild'])).get_channel(int(config['audio']['channel'])).connect();
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGHUP, lambda: asyncio.ensure_future(reload_function()))
        await reload_function()
    except Exception as e:
        print(e)

async def load_webhooks():
    global webhook_sync_registry
    webhook_sync_registry = {}
    for guild in client.guilds:
        try:
            for webhook in await guild.webhooks():
                # discord.py/rewrite issue #1242, PR #1745 workaround
                if webhook.name.startswith(config['discord']['botNavel']+' ('):
                    fromChannelName = guild.name+':'+str(guild.get_channel(webhook.channel_id))
                    webhook_sync_registry[fromChannelName] = {
                            'fromChannelObject': guild.get_channel(webhook.channel_id),
                            'fromWebhook': webhook,
                            'toChannelObject': None,
                            'toWebhook': None
                            }
                    toTuple = webhook.name.split("(")[1].split(")")[0].split(":")
                    toTuple[0] = messagefuncs.expand_guild_name(toTuple[0])
                    toGuild = discord.utils.get(client.guilds, name=toTuple[0].replace("_", " "))
                    webhook_sync_registry[fromChannelName]['toChannelObject'] = discord.utils.get(toGuild.text_channels, name=toTuple[1])
                    webhook_sync_registry[fromChannelName]['toWebhook'] = discord.utils.get(await toGuild.webhooks(), channel__name=toTuple[1])
        except discord.Forbidden as e:
            print('Couldn\'t load webhooks for '+str(guild)+', ask an admin to grant additional permissions (https://novalinium.com/go/3/fletcher)')
    print("Webhooks loaded:")
    print("\n".join(list(webhook_sync_registry)))

# on new message
@client.event
async def on_message(message):
    global webhook_sync_registry
    global conn
    # if the message is from the bot itself or sent via webhook, which is usually done by a bot, ignore it other than sync processing
    if message.webhook_id:
        return
    try:
        if message.guild.name+':'+message.channel.name in webhook_sync_registry:
            attachments = []
            for attachment in message.attachments:
                print("Syncing "+attachment.filename)
                attachment_blob = io.BytesIO()
                await attachment.save(attachment_blob)
                attachments.append(discord.File(attachment_blob, attachment.filename))
            # wait=True: blocking call for messagemap insertions to work
            syncMessage = await webhook_sync_registry[message.guild.name+':'+message.channel.name]['toWebhook'].send(content=message.content, username=message.author.name+" ("+message.guild.name+")", avatar_url=message.author.avatar_url, embeds=message.embeds, tts=message.tts, files=attachments, wait=True)
            cur = conn.cursor()
            cur.execute("INSERT INTO messagemap (fromguild, fromchannel, frommessage, toguild, tochannel, tomessage) VALUES (%s, %s, %s, %s, %s, %s);", [message.guild.id, message.channel.id, message.id, syncMessage.guild.id, syncMessage.channel.id, syncMessage.id])
            conn.commit()
    except AttributeError as e:
        # Eat from PMs
        pass
    if message.author == client.user:
        return

    # try to evaluate with the command handler
    try:
        await ch.command_handler(message)

    # message doesn't contain a command trigger
    except TypeError as e:
        pass

# on message update (for webhooks only for now)
@client.event
async def on_raw_message_edit(payload):
    global webhook_sync_registry
    try:
        # This is tricky with self-modifying bot message synchronization, TODO
        message_id = payload.message_id
        message = payload.data
        fromGuild = client.get_guild(int(message['guild_id']))
        fromChannel = fromGuild.get_channel(int(message['channel_id']))
        if fromGuild.name+':'+fromChannel.name in webhook_sync_registry:
            cur = conn.cursor()
            cur.execute("SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s LIMIT 1;", [int(message['guild_id']), int(message['channel_id']), message_id])
            metuple = cur.fetchone()
            conn.commit()
            if metuple is not None:
                toGuild = client.get_guild(metuple[0])
                toChannel = toGuild.get_channel(metuple[1])
                toMessage = await toChannel.get_message(metuple[2])
                fromMessage = await fromChannel.get_message(message_id)
                await toMessage.delete()
                attachments = []
                for attachment in fromMessage.attachments:
                    print("Syncing "+attachment.filename)
                    attachment_blob = io.BytesIO()
                    await attachment.save(attachment_blob)
                    attachments.append(discord.File(attachment_blob, attachment.filename))
                syncMessage = await webhook_sync_registry[fromMessage.guild.name+':'+fromMessage.channel.name]['toWebhook'].send(content=fromMessage.content, username=fromMessage.author.name+" ("+message.guild.name+")", avatar_url=fromMessage.author.avatar_url, embeds=fromMessage.embeds, tts=fromMessage.tts, files=attachments, wait=True)
                cur = conn.cursor()
                cur.execute("UPDATE messagemap SET toguild = %s, tochannel = %s, tomessage = %s WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;", [syncMessage.guild.id, syncMessage.channel.id, syncMessage.id, int(message['guild_id']), int(message['channel_id']), message_id])
                conn.commit()
    except discord.Forbidden as e:
        print("Forbidden to edit synced message from "+str(fromGuild.name)+":"+str(fromChannel.name))
    # except KeyError as e:
    #     # Eat keyerrors from non-synced channels
    #     pass
    # except AttributeError as e:
    #     # Eat from PMs
    #     pass
    # generic python error
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("ORMU[{}]: {}".format(exc_tb.tb_lineno, e))

# on message deletion (for webhooks only for now)
@client.event
async def on_raw_message_delete(message):
    global webhook_sync_registry
    try:
        fromGuild = client.get_guild(message.guild_id)
        fromChannel = fromGuild.get_channel(message.channel_id)
        if fromGuild.name+':'+fromChannel.name in webhook_sync_registry:
            cur = conn.cursor()
            cur.execute("SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s LIMIT 1;", [message.guild_id, message.channel_id, message.message_id])
            metuple = cur.fetchone()
            if metuple is not None:
                cur.execute("DELETE FROM messageMap WHERE fromGuild = %s AND fromChannel = %s AND fromMessage = %s", [fromGuild.id, fromChannel.id, message.message_id])
            conn.commit()
            if metuple is not None:
                toGuild = client.get_guild(metuple[0])
                toChannel = toGuild.get_channel(metuple[1])
                toMessage = await toChannel.get_message(metuple[2])
                print("Deleting synced message {}:{}:{}".format(metuple[0], metuple[1], metuple[2]))
                await toMessage.delete()
    except discord.Forbidden as e:
        print("Forbidden to delete synced message from "+str(fromGuild.name)+":"+str(fromChannel.name))
    except KeyError as e:
        # Eat keyerrors from non-synced channels
        pass
    except AttributeError as e:
        # Eat from PMs
        pass
    # generic python error
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("ORMD[{}]: {}".format(exc_tb.tb_lineno, e))

# on new rxn
@client.event
async def on_raw_reaction_add(reaction):
    # if the reaction is from the bot itself ignore it
    if reaction.user_id == client.user.id:
        pass
    else:
        # try to evaluate with the command handler
        try:
            print(reaction.emoji)
            await ch.reaction_handler(reaction)

        # message doesn't contain a command trigger
        except TypeError as e:
            pass

        # generic python error
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            print("ORRA[{}]: {}".format(exc_tb.tb_lineno, e))

# on vox change
@client.event
async def on_voice_state_update(member, before, after):
    global canticum_message
    print('Vox update in '+str(member.guild))
    # Notify only if: 
    # Doissetep
    # New joins only, no transfers
    # Not me
    if member.guild.id == int(config['audio']['guild']) and \
       after.channel is not None and before.channel is None and \
       member.id != client.user.id and \
       str(after.channel.id) not in config['audio']['channel-ban'].split(','):
        # used to be #canticum, moved to #autochthonia due to spamminess
        canticum = client.get_channel(int(config['audio']['notificationchannel']))
        if canticum_message is not None:
            await canticum_message.delete()
        canticum_message = await canticum.send("<@&"+str(config['audio']['notificationrole'])+">: "+str(member.name)+" is in voice ("+str(after.channel.name)+") in "+str(member.guild.name))

## on new member
#@client.event
#async def on_member_join(member):
#    # if the message is from the bot itself ignore it
#    if member == client.user:
#        pass
#    else:
#        yield # check if the guild requires containment and contain if so

# start bot
client.run(token)
