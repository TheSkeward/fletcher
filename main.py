# bot.py
from datetime import datetime
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sys import exc_info
from systemd import journal
import asyncio
import uvloop
import perpetuo

uvloop.install()
perpetuo.dwim()
import cProfile
import discord
import importlib
import io
import logging
import math
import os
import psycopg
import psycopg2
import re
from nio import MatrixRoom, AsyncClient as MatrixAsyncClient, RoomMessageText
from asyncache import cached
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

sentry_sdk.init(
    dsn="https://7654ff657b6447d78c3eee40151c9414@sentry.io/1842241",
    integrations=[AioHttpIntegration()],
    before_send=lambda event, hint: None
    if type(event) in [discord.ConnectionClosed]
    else event,
)
import signal
import traceback

"""
fletcher=# \d attributions
                              Table "public.attributions"
    Column    |            Type             | Collation | Nullable |      Default
--------------+-----------------------------+-----------+----------+-------------------
 added        | timestamp without time zone |           |          | CURRENT_TIMESTAMP
 author_id    | bigint                      |           |          |
 from_message | bigint                      |           |          |
 from_channel | bigint                      |           |          |
 from_guild   | bigint                      |           |          |
 message      | bigint                      |           |          |
 channel      | bigint                      |           |          |
 guild        | bigint                      |           |          |

fletcher=# \d parlay
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

fletcher=# \d threads
               Table "public.threads"
 Column |   Type   | Collation | Nullable | Default
--------+----------+-----------+----------+---------
 source | bigint   |           |          |
 target | bigint[] |           |          |


"""

logger = logging.getLogger("fletcher")

import load_config

config = load_config.FletcherConfig()

# Enable logging to SystemD
# TODO(nova): handler -> root logger, not fletcher
logger.addHandler(
    journal.JournalHandler(
        SYSLOG_IDENTIFIER=config.get(section="discord", key="botLogName")
    )
)
logger.setLevel(logging.DEBUG)

logging.getLogger("discord").addHandler(
    journal.JournalHandler(
        SYSLOG_IDENTIFIER=config.get(section="discord", key="botLogName")
    )
)

logging.getLogger("discord").setLevel(logging.INFO)

intents = discord.Intents.all()
intents.presences = False
client = discord.AutoShardedClient(
    intents=intents,
    chunk_guilds_at_startup=False,
    member_cache_flags=discord.MemberCacheFlags.all(),
    assume_unsync_clock=True,
)

# token from https://discordapp.com/developers
token = config.get(section="discord", key="botToken")

# globals for database handle and CommandHandler
global conn
global aconn
global ch
global pr
conn = None
aconn = None
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
import minedcraft
import text_manipulators
import schedule
import swag
import googlephotos
import pinterest
import danbooru
import github
import chronos

versioninfo = versionutils.VersionInfo()
sid = SentimentIntensityAnalyzer()

canticum_message = None
doissetep_omega = None


async def autoload(module, choverride, config=None):
    now = datetime.utcnow()
    if choverride:
        ch = choverride
    else:
        ch = globals()["ch"]
    global client
    global conn
    global sid
    global versioninfo
    # await client.change_presence(
    #     activity=discord.Game(name=f"Reloading: [{module.__name__}]")
    # )
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
        module.config = globals()["config"]
    else:
        module.config = config
    module.conn = conn
    module.aconn = aconn
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
    logger.info(f"{module.__name__} autoloaded in {datetime.utcnow() - now}")


async def animate_startup(emote, message=None):
    if message:
        await message.add_reaction(emote)
    logger.info(emote)


async def reload_function(message=None, client=client, args=[]):
    global config
    global conn
    global aconn
    global sid
    global versioninfo
    global doissetep_omega
    global matrix_client
    now = datetime.utcnow()
    try:
        # await client.change_presence(activity=discord.Game(name="Reloading: The Game"))
        if config["discord"].get("profile"):
            global pr
            if pr:
                pr.disable()
                pr.print_stats()
        importlib.reload(load_config)
        config = load_config.FletcherConfig()
        load_config.client = client
        config.client = client
        await animate_startup("📝", message)
        conn = psycopg2.connect(
            host=config["database"]["host"],
            database=config["database"]["tablespace"],
            user=config["database"]["user"],
            password=config["database"]["password"],
        )
        if aconn:
            try:
                aconn.close()
            except:
                # well at least we tried
                pass
        aconn = await psycopg.AsyncConnection.connect(
            host=config["database"]["host"],
            dbname=config["database"]["tablespace"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            autocommit=True,
        )
        await animate_startup("💾", message)
        # Command Handler (loaded twice to bootstrap)
        await autoload(commandhandler, None, config)
        await animate_startup("⌨", message)
        try:
            wsr = commandhandler.ch.webhook_sync_registry
        except (NameError, AttributeError) as e:
            logger.debug(f"[RELOAD]: {e}")
        ch = commandhandler.CommandHandler(client, config=config)
        commandhandler.ch = ch
        ch.config = config
        try:
            commandhandler.matrix_client = matrix_client
        except (NameError, AttributeError) as e:
            logger.debug(f"[RELOAD]: {e}")
        try:
            ch.webhook_sync_registry = wsr
            commandhandler.ch.webhook_sync_registry = wsr
            commandhandler.webhook_sync_registry = wsr
        except NameError:
            pass
        await autoload(versionutils, ch)
        versioninfo = versionutils.VersionInfo()
        ch.add_command(
            {
                "trigger": ["!reload_f"],
                "function": reload_function,
                "async": True,
                "admin": "global",
                "args_num": 0,
                "args_name": [],
                "description": "Reload config (admin only)",
            }
        )
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
        await autoload(minedcraft, ch)
        await autoload(swag, ch)
        await animate_startup("🙉", message)
        # Photos Connectors (for !twilestia et al)
        await autoload(pinterest, ch)
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
        # asyncio.create_task(doissetep_omega_autoconnect())
        # Trigger reload handlers
        await ch.reload_handler()
        # FIXME there should be some way to defer this, or maybe autoload another time
        await autoload(commandhandler, ch)
        if not hasattr(ch, "webhook_sync_registry") or not len(
            ch.webhook_sync_registry
        ):
            await ch.load_webhooks()
            commandhandler.webhooks_loaded = True
            commandhandler.ch.webhooks_loaded = True
            ch.webhooks_loaded = True
        else:
            commandhandler.webhooks_loaded = True
            commandhandler.ch.webhooks_loaded = True
            ch.webhooks_loaded = True
        await animate_startup("🔁", message)
        globals()["ch"] = ch
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


HAS_READIED_UP = False
# bot is ready
@client.event
async def on_ready():
    try:
        global doissetep_omega
        global client
        global matrix_client
        global ch
        global config
        global HAS_READIED_UP
        if HAS_READIED_UP:
            return
        # print bot information
        # await client.change_presence(activity=discord.Game(name="Reloading: The Game"))
        logger.info(
            f"Discord.py Version {discord.__version__}, connected as {client.user.name} ({client.user.id})"
        )
        loop = asyncio.get_event_loop()
        loop.remove_signal_handler(signal.SIGHUP)
        loop.add_signal_handler(signal.SIGHUP, lambda: print("Ignoring excess SIGHUP"))
        await reload_function()
        loop.remove_signal_handler(signal.SIGHUP)
        loop.add_signal_handler(
            signal.SIGHUP, lambda: asyncio.ensure_future(reload_function())
        )
        loop.add_signal_handler(
            signal.SIGINT, lambda: asyncio.ensure_future(shutdown_function())
        )

        matrix_client = MatrixAsyncClient(
            config["matrix"]["url"], config["matrix"]["user"]
        )
        matrix_client.add_event_callback(on_matrix_message, RoomMessageText)
        await matrix_client.login(config["matrix"]["password"])

        for guild in client.guilds:
            await guild.chunk()
        await reload_function()
        await matrix_client.sync_forever(timeout=30000)
        HAS_READIED_UP = True
    except Exception as e:
        logger.exception(e)


async def shutdown_function():
    global client
    await client.change_presence(
        activity=discord.Game(name="Shutting Down", start=now),
        status=discord.Status.do_not_disturb,
    )
    sys.exit(0)


async def on_matrix_message(room: MatrixRoom, message: RoomMessageText):
    global config
    with sentry_sdk.configure_scope() as scope:
        scope.user = {"id": message.sender_key, "username": message.sender}
        scope.set_tag("message", message.event_id)
        scope.set_tag("room", room.canonical_alias)
        try:
            # try to evaluate with the command handler
            while ch is None:
                await asyncio.sleep(1)
            while 1:
                try:
                    ch.config
                    break
                except AttributeError:
                    await asyncio.sleep(1)
            await ch.matrix_command_handler(room, message)

        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.debug(traceback.format_exc())
            logger.error(
                f"OM[{exc_tb.tb_lineno}]: {type(e).__name__} {e}",
                extra={"MESSAGE_ID": message.event_id},
            )


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
            while 1:
                try:
                    ch.config
                    break
                except AttributeError:
                    await asyncio.sleep(1)
            await ch.command_handler(message)

        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.debug(traceback.format_exc())
            logger.error(
                f"OM[{exc_tb.tb_lineno}]: {type(e).__name__} {e}",
                extra={"MESSAGE_ID": str(message.id)},
            )


# on message update (for webhooks only for now)
@client.event
async def on_raw_message_edit(payload):
    try:
        # This is tricky with self-modifying bot message synchronization, TODO
        message_id = payload.message_id
        message = payload.data
        fromGuild = None
        if "guild_id" in message:
            fromGuild = client.get_guild(int(message["guild_id"]))
            fromChannel = fromGuild.get_channel(
                int(message["channel_id"])
            ) or fromGuild.get_thread(int(message["channel_id"]))
        else:
            fromChannel = client.get_channel(int(message["channel_id"]))
        if (
            isinstance(fromGuild, discord.Guild)
            and fromGuild is not None
            and not fromChannel.permissions_for(
                fromGuild.get_member(client.user.id)
                or await fromGuild.fetch_member(client.user.id)
            ).read_message_history
        ):
            return
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
            logger.debug(traceback.format_exc())
            logger.warning(
                f"ORMU[{exc_tb.tb_lineno}]: {type(e).__name__} {e}", extra=extra
            )
            return
        while ch is None:
            await asyncio.sleep(1)
        while 1:
            try:
                ch.config
                break
            except AttributeError:
                await asyncio.sleep(1)
        with sentry_sdk.configure_scope() as scope:
            user = fromMessage.author
            scope.user = {"id": user.id, "username": str(user)}
            await ch.edit_handler(fromMessage)

    except discord.Forbidden as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug(traceback.format_exc())
        logger.error(
            f"ORMU[{exc_tb.tb_lineno}]: {type(e).__name__} {e} Forbidden to edit synced message from {fromGuild.name}:{fromChannel.name}"
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
        logger.debug(traceback.format_exc())
        logger.error(
            f"ORMU[{exc_tb.tb_lineno}]: {type(e).__name__} {e}",
            extra={"MESSAGE_ID": str(message_id)},
        )


@client.event
async def on_typing(channel, user, when):
    global ch
    while ch is None:
        await asyncio.sleep(1)
    return await ch.typing_handler(channel, user)


# on message deletion (for webhooks only for now)
@client.event
async def on_raw_message_delete(message):
    try:
        while ch is None:
            await asyncio.sleep(1)
        while 1:
            try:
                ch.config
                break
            except AttributeError:
                await asyncio.sleep(1)
        return await ch.deletion_handler(message)
    # generic python error
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ORMD[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


# on new rxn
@client.event
async def on_raw_reaction_add(reaction):
    # if the reaction is from the bot itself ignore it
    if reaction.user_id == client.user.id:
        return
    # try to evaluate with the command handler
    try:
        while ch is None:
            await asyncio.sleep(1)
        while 1:
            try:
                ch.config
                break
            except AttributeError:
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
        return
    # try to evaluate with the command handler
    try:
        while ch is None:
            await asyncio.sleep(1)
        while 1:
            try:
                ch.config
                break
            except AttributeError:
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
    logger.debug(
        f"Vox update in {member.guild}, {member} {before.channel} -> {after.channel}"
    )
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not commandhandler.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
            await asyncio.sleep(1)
    await ch.on_voice_state_update(member, before, after)
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
            f"<@&{config['audio']['notificationrole']}>: {member.name} is in voice ({after.channel.name}) in member.guild.name"
        )


# on new member
@client.event
async def on_member_join(member):
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not commandhandler.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
            await asyncio.sleep(1)
    await ch.join_handler(member)


# on departing member
@client.event
async def on_member_remove(member):
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not commandhandler.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
            await asyncio.sleep(1)
    await ch.remove_handler(member)


# on channel change
@client.event
async def on_guild_channel_update(before, after):
    global ch
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not ch.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
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
        except discord.ClientException as e:
            logger.debug("Omega connected already")
            pass
        except asyncio.exceptions.TimeoutError as e:
            logger.debug("Omega timeout")
            pass
        except AttributeError as e:
            logger.exception(e)


@client.event
async def on_invite_create(invite):
    global ch
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not ch.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
            await asyncio.sleep(1)
    if not ch.guild_invites.get(invite.guild.id):
        ch.guild_invites[invite.guild.id] = {invite.code: invite}
    ch.guild_invites[invite.guild.id][invite.code] = invite


@client.event
async def on_invite_delete(invite):
    global ch
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not ch.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
            await asyncio.sleep(1)
    if not ch.guild_invites.get(invite.guild.id):
        ch.guild_invites[invite.guild.id] = {invite.code: invite}
    del ch.guild_invites[invite.guild.id][invite.code]


@client.event
async def on_guild_join(guild):
    global ch
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            if not ch.webhooks_loaded:
                await asyncio.sleep(1)
                continue
            break
        except AttributeError:
            await asyncio.sleep(1)
    await ch.guild_add(guild)


@client.event
async def on_thread_create(thread):
    global ch
    times_through_loop = 0
    while ch is None:
        times_through_loop += 1
        if times_through_loop > 300:
            logger.error("What the fuck. nothing should take this long. Exiting")
            return
        await asyncio.sleep(1)
    times_through_loop = 0
    while 1:
        try:
            ch.config
            if not ch.webhooks_loaded:
                await asyncio.sleep(1)
                times_through_loop += 1
                if times_through_loop > 30:
                    logger.error(
                        "stalled in on_thread_create waiting for ch.webhooks_loaded, going for it anyways"
                    )
                    break
                continue
            break
        except AttributeError:
            times_through_loop += 1
            if times_through_loop > 30:
                logger.error(
                    "stalled in on_thread_create waiting for ch.config, going for it anyways"
                )
                break
            await asyncio.sleep(1)
    await ch.thread_add(thread)


@client.event
async def on_thread_join(thread):
    global ch
    times_through_loop = 0
    while ch is None:
        times_through_loop += 1
        if times_through_loop > 300:
            logger.error("What the fuck. nothing should take this long. Exiting")
            return
        await asyncio.sleep(1)
    times_through_loop = 0
    while 1:
        try:
            ch.config
            if not ch.webhooks_loaded:
                await asyncio.sleep(1)
                times_through_loop += 1
                if times_through_loop > 30:
                    logger.error(
                        "stalled in on_thread_create waiting for ch.webhooks_loaded, going for it anyways"
                    )
                    break
                continue
            break
        except AttributeError:
            times_through_loop += 1
            if times_through_loop > 30:
                logger.error(
                    "stalled in on_thread_create waiting for ch.config, going for it anyways"
                )
                break
            await asyncio.sleep(1)
    await ch.thread_add(thread)


@client.event
async def on_interaction(ctx):
    while ch is None:
        await asyncio.sleep(1)
    while 1:
        try:
            ch.config
            break
        except AttributeError:
            await asyncio.sleep(1)
    await ch.on_interaction(ctx)


# start bot
asyncio.get_event_loop().run_until_complete(client.start(token))
