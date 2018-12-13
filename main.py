# bot.py
import asyncio
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


config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)

client = discord.Client()

# token from https://discordapp.com/developers
token = config['discord']['botToken']

# globals for database handle and CommandHandler
conn = None
ch = None

# Submodules, loaded in reload_function so no initialization is done here
import commandhandler
import sentinel
import janissary
import mathemagical
import messagefuncs
import text_manipulators
import swag

sid = SentimentIntensityAnalyzer()

webhook_sync_registry = {
        'FromGuild:FromChannelName': {
            'fromChannelObject': None,
            'fromWebhook': None,
            'toChannelObject': None,
            'toWebhook': None
            }
        }

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

canticum_message = None
doissetep_omega =  None

def autoload(module):
    importlib.reload(module)
    moduel.ch = ch
    module.config = config
    module.conn = conn
    module.sid = sid
    try:
        module.autoload(ch)
    except AttributeError:
        # Ignore missing autoload
        print('[Info] '+module.__name__+' missing autoload(ch), continuing.')
        pass

async def animate_startup(emote, message=None):
    if message:
        await message.add_reaction(emote)
    else:
        print(emote)

async def reload_function(message=None, client=client, args=[]):
    global ch
    global conn
    global doissetep_omega
    try:
        config.read(FLETCHER_CONFIG)
        await animate_startup('📝', message)
        await load_webhooks()
        if message:
            await message.add_reaction('↔')
        conn = psycopg2.connect(host=config['database']['host'],database=config['database']['tablespace'], user=config['database']['user'], password=config['database']['password'])
        await animate_startup('💾', message)
        # Command Handler (loaded twice to bootstrap)
        importlib.reload(commandhandler)
        await animate_startup('⌨', message)
        ch = commandhandler.CommandHandler(client)
        autoload(commandhandler)
        ch.add_command({
            'trigger': ['!reload <@'+str(ch.client.user.id)+'>'],
            'function': reload_function,
            'async': True,
            'admin': True,
            'args_num': 0,
            'args_name': [],
            'description': 'Reload config (admin only)'
            })
        # Utility text manipulators Module
        autoload(text_manipulators)
        await animate_startup('🔧', message)
        # Sentinel Module
        importlib.reload(sentinel)
        sentinel.conn = conn
        sentinel.autoload(ch)
        await animate_startup('🎏', message)
        # Messages Module
        importlib.reload(messagefuncs)
        messagefuncs.config = config
        messagefuncs.autoload(ch)
        await animate_startup('🔭', message)
        # Math modules
        importlib.reload(mathemagical)
        mathemagical.autoload(ch)
        await animate_startup('➕', message)
        importlib.reload(janissary)
        janissary.config = config
        janissary.autoload(ch)
        # Super Waifu Animated Girlfriend (SWAG)
        importlib.reload(swag)
        swag.autoload(ch)
        await animate_startup('🙉', message)
        # Play it again, Sam
        if not doissetep_omega.is_playing():
            doissetep_omega.play(discord.FFmpegPCMAudio(config['audio']['instreamurl']))
        await animate_startup('✅', message)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("RM[{}]: {}".format(exc_tb.tb_lineno, e))
        await animate_startup('🚫', message)

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
    # TODO refactor to CommandHandler
    print('Vox update in '+str(member.guild))
    # Notify only if: 
    # Doissetep
    # New joins only, no transfers
    # Not me
    if member.guild.id == int(config['audio']['guild']) and \
       after.channel is not None and before.channel is None and \
       member.id != client.user.id and \
       str(after.channel.id) not in config['audio']['channel-ban'].split(','):
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
