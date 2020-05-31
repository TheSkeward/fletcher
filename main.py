# bot.py
from datetime import datetime
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sys import exc_info
from systemd import journal
import asyncio
import cProfile
import discord
import importlib
import io
import logging
import math
import os
import psycopg2
import re
from asyncache import cached
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

sentry_sdk.init(
        dsn="https://7654ff657b6447d78c3eee40151c9414@sentry.io/1842241",
        integrations=[AioHttpIntegration()],
        before_send=lambda event, hint: None if type(event) in [discord.ConnectionClosed] else event
        )
import signal
import traceback

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
   Column    |   Type   | Collation | Nullable | Default 
-------------+----------+-----------+----------+---------
 fromguild   | bigint   |           |          | 
 toguild     | bigint   |           |          | 
 fromchannel | bigint   |           |          | 
 tochannel   | bigint   |           |          | 
 frommessage | bigint   |           |          | 
 tomessage   | bigint   |           |          | 
 reactions   | bigint[] |           |          | 

Indexes:
    "messagemap_idx" btree (fromguild, fromchannel, frommessage)

fletcher=# \d permaRoles
                            Table "public.permaroles"
 Column  |            Type             | Collation | Nullable |      Default
---------+-----------------------------+-----------+----------+-------------------
 userid  | bigint                      |           | not null |
 guild   | bigint                      |           | not null |
 roles   | bigint[]                    |           |          |
 updated | timestamp without time zone |           |          | CURRENT_TIMESTAMP
Indexes:
    "permaroles_idx" btree (userid, guild)

fletcher=# \d reminders;
                                   Table "public.reminders"
  Column      |            Type             | Collation | Nullable |           Default           
--------------+-----------------------------+-----------+----------+-----------------------------
 userid       | bigint                      |           | not null | 
 guild        | bigint                      |           | not null | 
 channel      | bigint                      |           | not null | 
 message      | bigint                      |           | not null | 
 content      | text                        |           |          | 
 created      | timestamp without time zone |           |          | CURRENT_TIMESTAMP
 scheduled    | timestamp without time zone |           |          | (now() + '1 day'::interval)
 trigger_type | text                        |           |          | 'table'::text

fletcher=# \d qdb
                                Table "public.qdb"
  Column  |  Type   | Collation | Nullable |                Default                
----------+---------+-----------+----------+---------------------------------------
 user_id  | bigint  |           | not null | 
 guild_id | bigint  |           | not null | 
 quote_id | integer |           | not null | nextval('qdb_quote_id_seq'::regclass)
 key      | text    |           |          | 
 value    | text    |           | not null | 

"""

logger = logging.getLogger("fletcher")

import load_config
config = load_config.FletcherConfig()

# Enable logging to SystemD
logger.addHandler(
    journal.JournalHandler(
        SYSLOG_IDENTIFIER=config.get(section="discord", key="botLogName")
    )
)
logger.setLevel(logging.DEBUG)

client = discord.Client()

# token from https://discordapp.com/developers
token = config.get(section="discord", key="botToken")

# globals for database handle and CommandHandler
conn = None
ch = None
pr = None

# Submodules, loaded in reload_function so no initialization is done here
import commandhandler
import versionutils
import greeting
import sentinel
import janissary
import mathemagical
import messagefuncs
import text_manipulators
import schedule
import swag
import googlephotos
import danbooru
import github
import chronos

versioninfo = versionutils.VersionInfo()
sid = SentimentIntensityAnalyzer()

webhook_sync_registry = {
    "FromGuild:FromChannelName": {
        "fromChannelObject": None,
        "fromWebhook": None,
        "toChannelObject": None,
        "toWebhook": None,
    }
}


async def load_webhooks():
    global config
    webhook_sync_registry = {}
    for guild in client.guilds:
        try:
            if config.get(guild=guild, key="synchronize"):
                logger.debug(f"LWH: Querying {guild.name}")
                for webhook in await guild.webhooks():
                    if webhook.name.startswith(
                        config.get(section="discord", key="botNavel") + " ("
                    ):
                        logger.debug(f"LWH: * {webhook.name}")
                        toChannelName = (
                            guild.name
                            + ":"
                            + str(guild.get_channel(webhook.channel_id))
                        )
                        fromTuple = webhook.name.split("(")[1].split(")")[0].split(":")
                        fromTuple[0] = messagefuncs.expand_guild_name(
                            fromTuple[0]
                        ).replace(":", "")
                        fromGuild = discord.utils.get(
                            client.guilds, name=fromTuple[0].replace("_", " ")
                        )
                        fromChannelName = (
                            fromTuple[0].replace("_", " ") + ":" + fromTuple[1]
                        )
                        try:
                            webhook_sync_registry[
                                    f"{fromGuild.id}:{webhook.id}"
                                    ] = fromChannelName
                        except AttributeError:
                            logger.debug(f"LWH: fromGuild.id not defined")
                            continue
                        webhook_sync_registry[fromChannelName] = {
                            "toChannelObject": guild.get_channel(webhook.channel_id),
                            "toWebhook": webhook,
                            "toChannelName": toChannelName,
                            "fromChannelObject": None,
                            "fromWebhook": None,
                        }
                        webhook_sync_registry[fromChannelName][
                            "fromChannelObject"
                        ] = discord.utils.get(
                            fromGuild.text_channels, name=fromTuple[1]
                        )
                        try:
                            # webhook_sync_registry[fromChannelName]['fromWebhook'] = discord.utils.get(await fromGuild.webhooks(), channel__name=fromTuple[1])
                            if webhook_sync_registry[fromChannelName][
                                "fromChannelObject"
                            ]:
                                webhook_sync_registry[fromChannelName][
                                    "fromWebhook"
                                ] = await webhook_sync_registry[fromChannelName][
                                    "fromChannelObject"
                                ].webhooks()
                                webhook_sync_registry[fromChannelName][
                                    "fromWebhook"
                                ] = (
                                    webhook_sync_registry[fromChannelName][
                                        "fromWebhook"
                                    ][0]
                                    if len(
                                        webhook_sync_registry[fromChannelName][
                                            "fromWebhook"
                                        ]
                                    )
                                    else None
                                )
                            else:
                                logger.warning(
                                    f"LWH: Could not find fromChannel {fromTuple[1]} in {fromGuild}"
                                )
                        except discord.Forbidden as e:
                            logger.warning(
                                f'LWH: Error getting fromWebhook for {webhook_sync_registry[fromChannelName]["fromChannelObject"]}'
                            )
                            pass
            elif "Guild " + str(guild.id) not in config:
                logger.warning(
                    f"LWH: Failed to find config for {guild.name} ({guild.id})"
                )
        except discord.Forbidden as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.debug(f"LWH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
            logger.debug(traceback.format_exc())
            logger.warning(
                f"Couldn't load webhooks for {guild.name} ({guild.id}), ask an admin to grant additional permissions (https://novalinium.com/go/4/fletcher)"
            )
            pass
        except AttributeError as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.debug(f"LWH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
            pass
    globals()["webhook_sync_registry"] = webhook_sync_registry
    logger.debug("Webhooks loaded:")
    logger.debug(
        "\n".join(
            [
                f'{key} to {webhook_sync_registry[key]["toChannelName"]} (Guild {webhook_sync_registry[key]["toChannelObject"].guild.id})'
                for key in list(webhook_sync_registry)
                if type(webhook_sync_registry[key]) is not str
            ]
        )
    )


canticum_message = None
doissetep_omega = None


async def autoload(module, choverride, config=None):
    if choverride:
        ch = choverride
    else:
        ch = globals()["ch"]
    global client
    global conn
    global sid
    global versioninfo
    try:
        await module.autounload(ch)
    except AttributeError as e:
        # ignore missing autounload
        logger.info(f"{module.__name__} missing autounload(ch), continuing.")
        pass
    importlib.reload(module)
    module.ch = ch
    module.client = client
    if config is None:
        module.config = ch.config
    else:
        module.config = config
    module.conn = conn
    module.sid = sid
    module.versioninfo = versioninfo
    try:
        module.autoload(ch)
    except AttributeError as e:
        # ignore missing autoload
        logger.info(f"{module.__name__} missing autoload(ch), continuing.")
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug(f"al[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        logger.debug(traceback.format_exc())
        pass


async def animate_startup(emote, message=None):
    if message:
        await message.add_reaction(emote)
    logger.info(emote)


async def reload_function(message=None, client=client, args=[]):
    global config
    global conn
    global sid
    global versioninfo
    global doissetep_omega
    now = datetime.utcnow()
    try:
        await client.change_presence(activity=discord.Game(name="Reloading: The Game"))
        if config["discord"].get("profile"):
            global pr
            if pr:
                pr.disable()
                pr.print_stats()
        importlib.reload(load_config)
        config = load_config.FletcherConfig()
        await animate_startup("📝", message)
        conn = psycopg2.connect(
            host=config["database"]["host"],
            database=config["database"]["tablespace"],
            user=config["database"]["user"],
            password=config["database"]["password"],
        )
        await animate_startup("💾", message)
        # Command Handler (loaded twice to bootstrap)
        await autoload(commandhandler, None, config)
        await animate_startup("⌨", message)
        ch = commandhandler.CommandHandler(client)
        commandhandler.ch = ch
        await autoload(versionutils, ch)
        versioninfo = versionutils.VersionInfo()
        ch.add_command(
            {
                "trigger": [f"!reload <@!{ch.client.user.id}>"],
                "function": reload_function,
                "async": True,
                "admin": "global",
                "args_num": 0,
                "args_name": [],
                "description": "Reload config (admin only)",
            }
        )
        ch.webhook_sync_registry = webhook_sync_registry
        # Utility text manipulators Module
        await autoload(text_manipulators, ch)
        await animate_startup("🔧", message)
        # Schedule Module
        await autoload(schedule, ch)
        await animate_startup("📅", message)
        # Greeting module
        await autoload(greeting, ch)
        await animate_startup("👋", message)
        # Sentinel Module
        await autoload(sentinel, ch)
        await animate_startup("🎏", message)
        # Messages Module
        await autoload(messagefuncs, ch)
        await animate_startup("🔭", message)
        # Math Module
        await autoload(mathemagical, ch)
        await animate_startup("➕", message)
        await autoload(janissary, ch)
        # Super Waifu Animated Girlfriend (SWAG)
        await autoload(swag, ch)
        await animate_startup("🙉", message)
        # Photos Connectors (for !twilestia et al)
        await autoload(googlephotos, ch)
        await autoload(danbooru, ch)
        await animate_startup("📷", message)
        # GitHub Connector
        await autoload(github, ch)
        await animate_startup("🐙", message)
        # Time Module
        await autoload(chronos, ch)
        await animate_startup("🕰️", message)
        # Play it again, Sam
        await doissetep_omega_autoconnect()
        # Trigger reload handlers
        await ch.reload_handler()
        # FIXME there should be some way to defer this, or maybe autoload another time
        await autoload(commandhandler, ch)
        await animate_startup("🔁", message)
        globals()["ch"] = ch
        await load_webhooks()
        ch.webhook_sync_registry = webhook_sync_registry
        if message:
            await message.add_reaction("↔")
        await animate_startup("✅", message)
        await client.change_presence(
            activity=discord.Game(name="fletcher.fun | !help", start=now)
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.critical(f"RM[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        logger.debug(traceback.format_exc())
        await animate_startup("🚫", message)
        await client.change_presence(
            activity=discord.Game(
                name=f"Error Reloading: RM[{exc_tb.tb_lineno}]: {e}", start=now
            )
        )


# bot is ready
@client.event
async def on_ready():
    try:
        global doissetep_omega
        global client
        global ch
        # print bot information
        await client.change_presence(activity=discord.Game(name="Reloading: The Game"))
        logger.info(
            f"Discord.py Version {discord.__version__}, connected as {client.user.name} ({client.user.id})"
        )
        loop = asyncio.get_running_loop()
        loop.remove_signal_handler(signal.SIGHUP)
        await reload_function()
        loop.add_signal_handler(
            signal.SIGHUP, lambda: asyncio.ensure_future(reload_function())
        )
        loop.add_signal_handler(
            signal.SIGINT, lambda: asyncio.ensure_future(shutdown_function())
        )
    except Exception as e:
        logger.exception(e)


async def shutdown_function():
    global client
    await client.change_presence(
        activity=discord.Game(name="Shutting Down", start=now),
        status=discord.Status.do_not_disturb,
    )
    sys.exit(0)


# on new message
@client.event
async def on_message(message):
    global config
    with sentry_sdk.configure_scope() as scope:
        user = message.author
        scope.user = {"id": user.id, "username": str(user)}
        scope.set_tag("message", str(message.id))
        try:
            # try to evaluate with the command handler
            while ch is None:
                await asyncio.sleep(1)
            await ch.command_handler(message)
 
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"OM[{exc_tb.tb_lineno}]: {type(e).__name__} {e}", extra={"MESSAGE_ID": str(message.id)})
            logger.debug(traceback.format_exc())


# on message update (for webhooks only for now)
@client.event
async def on_raw_message_edit(payload):
    global webhook_sync_registry
    try:
        # This is tricky with self-modifying bot message synchronization, TODO
        message_id = payload.message_id
        message = payload.data
        if "guild_id" in message:
            fromGuild = client.get_guild(int(message["guild_id"]))
            fromChannel = fromGuild.get_channel(int(message["channel_id"]))
        else:
            fromChannel = client.get_channel(int(message["channel_id"]))
        try:
            fromMessage = await fromChannel.fetch_message(message_id)
        except discord.NotFound as e:
            exc_type, exc_obj, exc_tb = exc_info()
            extra = {"MESSAGE_ID": str(message_id), "payload": str(payload)}
            if type(fromChannel) is discord.DMChannel:
                extra["CHANNEL_IDENTIFIER"] = fromChannel.recipient
            else:
                extra["CHANNEL_IDENTIFIER"] = fromChannel.name
            if fromGuild:
                extra["GUILD_IDENTIFIER"] = fromGuild.name
            logger.warning(
                f"ORMU[{exc_tb.tb_lineno}]: {type(e).__name__} {e}", extra=extra
            )
            return
        while ch is None:
            await asyncio.sleep(1)
        with sentry_sdk.configure_scope() as scope:
            user = fromMessage.author
            scope.user = {"id": user.id, "username": str(user)}
            await ch.edit_handler(fromMessage)

    except discord.Forbidden as e:
        logger.error(
            "Forbidden to edit synced message from "
            + str(fromGuild.name)
            + ":"
            + str(fromChannel.name)
        )
    # except KeyError as e:
    #     # Eat keyerrors from non-synced channels
    #     pass
    # except AttributeError as e:
    #     # Eat from PMs
    #     pass
    # generic python error
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ORMU[{exc_tb.tb_lineno}]: {type(e).__name__} {e}", extra={"MESSAGE_ID": str(message_id)})


# on message deletion (for webhooks only for now)
@client.event
async def on_raw_message_delete(message):
    global webhook_sync_registry
    try:
        while ch is None:
            await asyncio.sleep(1)
        fromGuild = client.get_guild(message.guild_id)
        fromChannel = fromGuild.get_channel(message.channel_id)
        if type(fromChannel) is discord.TextChannel:
            logger.info(
                str(message.message_id)
                + " #"
                + fromGuild.name
                + ":"
                + fromChannel.name
                + " [Deleted]",
                extra={
                    "GUILD_IDENTIFIER": fromGuild.name,
                    "CHANNEL_IDENTIFIER": fromChannel.name,
                    "MESSAGE_ID": str(message.message_id),
                },
            )
        elif type(fromChannel) is discord.DMChannel:
            logger.info(
                str(message.message_id)
                + " @"
                + fromChannel.recipient.name
                + " [Deleted]",
                extra={
                    "GUILD_IDENTIFIER": "@",
                    "CHANNEL_IDENTIFIER": fromChannel.name,
                    "MESSAGE_ID": str(message.message_id),
                },
            )
        else:
            # Group Channels don't support bots so neither will we
            pass
        guild_config = ch.scope_config(guild=message.guild)
        if type(fromChannel) is discord.TextChannel and (
            fromGuild.name + ":" + fromChannel.name in webhook_sync_registry.keys()
        ):
            # Give messages time to be added to the database
            await asyncio.sleep(1)
            cur = conn.cursor()
            cur.execute(
                "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s LIMIT 1;",
                [message.guild_id, message.channel_id, message.message_id],
            )
            metuple = cur.fetchone()
            if metuple is not None:
                cur.execute(
                    "DELETE FROM messageMap WHERE fromGuild = %s AND fromChannel = %s AND fromMessage = %s",
                    [fromGuild.id, fromChannel.id, message.message_id],
                )
            conn.commit()
            if metuple is not None:
                toGuild = client.get_guild(metuple[0])
                to_guild_config = ch.scope_config(guild=toGuild)
                if to_guild_config.get("sync-deletions", "on") != "on":
                    logger.debug(
                        f"ORMD: Demurring to delete message at client guild request"
                    )
                    return
                toChannel = toGuild.get_channel(metuple[1])
                toMessage = None
                while not toMessage:
                    try:
                        toMessage = await toChannel.fetch_message(metuple[2])
                    except discord.NotFound as e:
                        exc_type, exc_obj, exc_tb = exc_info()
                        logger.error(
                            f"ORMD[{exc_tb.tb_lineno}]: {type(e).__name__} {e}"
                        )
                        logger.error(
                            f"ORMD[{exc_tb.tb_lineno}]: {metuple[0]}:{metuple[1]}:{metuple[2]}"
                        )
                        toMessage = None
                        await asyncio.sleep(1)
                        pass
                logger.debug(
                    f"ORMD: Deleting synced message {metuple[0]}:{metuple[1]}:{metuple[2]}"
                )
                await toMessage.delete()
    except discord.Forbidden as e:
        logger.error(
            f"Forbidden to delete synced message from {fromGuild.name}:{fromChannel.name}"
        )
    except KeyError as e:
        # Eat keyerrors from non-synced channels
        pass
    except AttributeError as e:
        # Eat from PMs
        pass
    # generic python error
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ORMD[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


# on new rxn
@client.event
async def on_raw_reaction_add(reaction):
    # if the reaction is from the bot itself ignore it
    if reaction.user_id == client.user.id:
        pass
    else:
        # try to evaluate with the command handler
        try:
            while ch is None:
                await asyncio.sleep(1)
            await ch.reaction_handler(reaction)

        # generic python error
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"ORRA[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


# on new rxn
@client.event
async def on_raw_reaction_remove(reaction):
    # if the reaction is from the bot itself ignore it
    if reaction.user_id == client.user.id:
        pass
    else:
        # try to evaluate with the command handler
        try:
            while ch is None:
                await asyncio.sleep(1)
            await ch.reaction_remove_handler(reaction)

        # generic python error
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"ORRR[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


# on vox change
@client.event
async def on_voice_state_update(member, before, after):
    global canticum_message
    # TODO refactor to CommandHandler
    logger.debug(
        f"Vox update in {member.guild}, {member} {before.channel} -> {after.channel}"
    )
    # Notify only if:
    # Doissetep
    # New joins only, no transfers
    # Not me
    if (
        member.guild.id == int(config["audio"]["guild"])
        and after.channel is not None
        and before.channel is None
        and member.id != client.user.id
        and str(after.channel.id) not in config["audio"]["channel-ban"].split(",")
    ):
        canticum = client.get_channel(int(config["audio"]["notificationchannel"]))
        if canticum_message is not None:
            await canticum_message.delete()
        canticum_message = await canticum.send(
            "<@&"
            + str(config["audio"]["notificationrole"])
            + ">: "
            + str(member.name)
            + " is in voice ("
            + str(after.channel.name)
            + ") in "
            + str(member.guild.name)
        )


# on new member
@client.event
async def on_member_join(member):
    while ch is None:
        await asyncio.sleep(1)
    await ch.join_handler(member)


# on departing member
@client.event
async def on_member_remove(member):
    while ch is None:
        await asyncio.sleep(1)
    await ch.remove_handler(member)


# on channel change
@client.event
async def on_guild_channel_update(before, after):
    while ch is None:
        await asyncio.sleep(1)
    await ch.channel_update_handler(before, after)


async def doissetep_omega_autoconnect():
    global doissetep_omega
    global config
    if doissetep_omega and doissetep_omega.is_connected():
        if not doissetep_omega.is_playing():
            doissetep_omega.play(discord.FFmpegPCMAudio(config["audio"]["instreamurl"]))
        # Reset canticum_message when reloaded [workaround for https://todo.sr.ht/~nova/fletcher/6]
        canticum_message = None
        return doissetep_omega
    else:
        try:
            doissetep_omega = (
                await client.get_guild(int(config["audio"]["guild"]))
                .get_channel(int(config["audio"]["channel"]))
                .connect()
            )
            if not doissetep_omega.is_playing():
                doissetep_omega.play(
                    discord.FFmpegPCMAudio(config["audio"]["instreamurl"])
                )
            # Reset canticum_message when reloaded [workaround for https://todo.sr.ht/~nova/fletcher/6]
            canticum_message = None
            return doissetep_omega
        except asyncio.exceptions.TimeoutError as e:
            logger.debug('Omega timeout')
            pass
        except AttributeError as e:
            logger.exception(e)

loop = asyncio.get_event_loop()

# start bot
loop.run_until_complete(client.start(token))
