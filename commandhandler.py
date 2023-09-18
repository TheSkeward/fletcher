from datetime import datetime
from emoji.unicode_codes import UNICODE_EMOJI
import asyncio
from io import BytesIO
from aiohttp import web, ClientSession
from aiohttp.web import AppRunner, Application
from psycopg2._psycopg import connection
from psycopg2.errors import UniqueViolation
from dataclasses import dataclass, field

import discord, discord.utils
from aiolimiter import AsyncLimiter
from nio import MatrixRoom, AsyncClient as MatrixAsyncClient, RoomMessageText
import logging

import messagefuncs
import itertools
import netcode
import greeting
import inspect
import janissary
import random
import re
import pytz
from sys import exc_info
import traceback
import ujson
from functools import partial
import sentry_sdk
from asyncache import cached
from cachetools import TTLCache
from collections import defaultdict
import load_config
from typing import (
    cast,
    TYPE_CHECKING,
    Dict,
    List,
    Iterable,
    Union,
    Callable,
    Awaitable,
    Literal,
    Coroutine,
    Optional,
)

logger = logging.getLogger("fletcher")

regex_cache = {}
webhooks_cache = {}
webhooks_loaded: bool = False
remote_command_runner = None
Ans = None
config = cast(load_config.FletcherConfig, None)
conn = cast(connection, None)
client = cast(discord.Client, None)
matrix_client = cast(MatrixAsyncClient, None)
message_handler_rate_limit = AsyncLimiter(1, 1)


def list_append(lst: List, item) -> List:
    lst.append(item)
    return item


def str_to_arr(
    string: str,
    delim: str = ",",
    strip: bool = True,
    filter_function: Callable = None.__ne__,
) -> Iterable:
    array = string.split(delim)
    if strip:
        array = map(str.strip, array)
    if all(el.isnumeric for el in array):
        array = map(int, array)
    return filter(filter_function, array)


class Bridge:
    def __init__(self):
        self.channels: List[discord.TextChannel] = []
        self.webhooks: List[discord.Webhook] = []
        self.threads: List[Optional[discord.Thread]] = []
        self.rate_limit = AsyncLimiter(1, 10)

    def __name__(self):
        return f"Bridge to: {[c.name for c in self.channels]}"

    async def typing(self, except_for: Optional[discord.TextChannel] = None):
        if self.rate_limit.has_capacity():
            async with self.rate_limit:
                if len(self.channels) == 1:
                    await self.channels[0].trigger_typing()
                else:
                    await asyncio.gather(
                        *[
                            channel.trigger_typing()
                            for channel in self.channels
                            if not except_for or channel.id != except_for.id
                        ]
                    )

    def append(
        self,
        channel: discord.TextChannel,
        webhook: discord.Webhook,
        thread: Optional[discord.Thread] = None,
    ):
        self.channels.append(channel)
        self.webhooks.append(webhook)
        self.threads.append(thread)

    async def send(self, **kwargs) -> Awaitable:
        """
        Surprise! This isn't actually used by bridge_message. Maybe do that. Eventually.
        """
        tasks: List[Coroutine] = []
        for webhook, thread in zip(self.webhooks, self.threads):
            tasks.append(
                messagefuncs.sendWrappedMessage(target=webhook, thread=thread, **kwargs)
            )
        return asyncio.gather(*tasks)


class Command:
    def __init__(
        self,
        trigger=[""],
        function: Union[Callable, Awaitable] = lambda message: message.content,
        sync: bool = True,
        hidden: bool = None,
        admin: Union[bool, Literal["channel", "server", "global"]] = False,
        args_num: int = 0,
        args_min: Optional[int] = None,
        args_name: List[str] = [],
        description: str = None,
        exclusive: bool = False,
        scope: type = discord.Message,
        remove: bool = False,
        long_run: bool = False,
    ):
        self.trigger = trigger
        self.function = function
        self.sync = sync
        self.hidden = hidden
        self.admin = admin
        self.arguments = {
            "min_count": args_min if args_min else args_num,
            "names": args_name,
        }
        self.description = description
        self.exclusive = exclusive
        self.scope = scope
        self.remove = remove
        self.long_run = long_run

    def __str__(self) -> str:
        return f"{self.function}: {self.description}"


class CommandHandler:
    def __init__(self, client: discord.Client, config):
        self.client = client
        self.commands = []
        self.join_handlers = {}
        self.remove_handlers = {}
        self.reload_handlers = {}
        self.message_reply_handlers = {}
        self.message_reaction_handlers: Dict[int, Command] = {}
        self.message_reaction_remove_handlers = {}
        self._guild_payloads = {}
        assert client.user is not None
        self.user = client.user
        self.tag_id_as_command = re.compile(
            r"(?:^(?:Oh)?\s*(?:"
            + self.user.mention
            + r"|Fletch[er]*)[, .]*)|(?:[, .]*(?:"
            + self.user.mention
            + r"|Fletch[er]*)[, .]*$)",
            re.IGNORECASE,
        )
        self.bang_remover = re.compile("^!+")
        self.global_admin = client.get_user(
            cast(int, config.get(section="discord", key="globalAdmin", default=0))
        )

        self.webhook_sync_registry: Dict[str, Bridge]  # = {
        # "FromGuildId:FromChannelId": Bridge()
        # }
        self.guild_invites = {}
        self.config = config if config else cast(load_config.FletcherConfig, None)
        self.emote_server = self.client.guilds[0]
        if self.config:
            emote_server = self.client.get_guild(
                cast(
                    int,
                    self.config.get(section="discord", key="emoteServer", default=0),
                )
            )
            assert isinstance(emote_server, discord.Guild)
            self.emote_server = emote_server
            self.ch_enable_typing_handler = (
                self.config.get(
                    section="discord", key="enable_typing_handler", default=False
                ),
            )
        self.pinged_users: defaultdict[int, list[int]] = defaultdict(list)

    async def load_webhooks(self):
        logger.debug("Loading webhooks")
        global webhooks_loaded
        webhooks_loaded = False
        webhook_sync_registry: Dict[str, Bridge] = {}
        navel_filter = f"{self.config.get(section='discord', key='botNavel')} ("
        bridge_guilds = list(
            filter(
                lambda guild: self.config.get(guild=guild, key="synchronize"),
                self.client.guilds,
            )
        )
        self.add_command(
            {
                "trigger": ["!reaction_list"],
                "function": reaction_list_function,
                "async": True,
                "hidden": True,
                "args_num": 0,
                "args_name": [""],
                "description": "List reactions",
                "message_command": True,
                "whitelist_guild": [guild.id for guild in bridge_guilds],
            }
        )
        total = len(bridge_guilds)
        n = 0
        for webhooks in (
            guild
            for guild in bridge_guilds
            if (member := guild.get_member(self.user.id))
            and member.guild_permissions.manage_webhooks
        ):
            n += 1
            logger.debug(f"Loading guild {n}/{total}")
            try:
                webhooks_iter = await webhooks.webhooks()
            except discord.errors.DiscordServerError:
                await asyncio.sleep(1)
                webhooks_iter = []
                for channel in webhooks.text_channels:
                    try:
                        webhooks_iter.extend(await channel.webhooks())
                    except:
                        logger.warning(f"Might have missed webhooks in {channel}")
            for webhook in filter(
                lambda webhook: webhook.name.startswith(navel_filter),
                webhooks_iter,
            ):
                assert webhook
                fromTuple = webhook.name.split("(")[1].rsplit(")")[0].rsplit(":", 2)
                fromTuple[0] = messagefuncs.expand_guild_name(fromTuple[0]).replace(
                    ":", ""
                )
                fromGuild = discord.utils.get(
                    self.client.guilds, name=fromTuple[0].replace("_", " ")
                )
                if not fromGuild or not fromGuild.id or not webhook.guild:
                    continue
                toChannel = webhook.guild.get_channel(webhook.channel_id)
                fromChannel = discord.utils.find(
                    lambda channel: channel.name == fromTuple[1]
                    or str(channel.id) == fromTuple[1],
                    fromGuild.text_channels,
                )
                if not fromChannel:
                    continue
                assert isinstance(toChannel, discord.TextChannel)
                fromChannelName = f"{fromGuild.name}:{fromChannel.id}"
                # webhook_sync_registry[f"{fromGuild.id}:{webhook.id}"] = fromChannelName
                if not isinstance(webhook_sync_registry.get(fromChannelName), Bridge):
                    webhook_sync_registry[fromChannelName] = Bridge()
                bridge = cast(Bridge, webhook_sync_registry[fromChannelName])
                thread_id = self.config.get(
                    "bridge_target_thread",
                    channel=toChannel,
                    guild=toChannel.guild,
                    default=None,
                )
                if thread_id:
                    thread = toChannel.guild.get_channel_or_thread(thread_id)
                else:
                    thread = None
                bridge.append(
                    toChannel,
                    webhook,
                    thread,
                )
                await asyncio.sleep(0.1)
        self.webhook_sync_registry = webhook_sync_registry
        webhooks_loaded = True
        logger.debug("Webhooks loaded:")
        logger.debug(
            "\n".join(
                [
                    f'{key} to {", ".join([channel.guild.name+":"+channel.name for channel in webhook_sync_registry[key].channels])} (Guild {", ".join([str(channel.guild.id) for channel in webhook_sync_registry[key].channels])})'
                    for key in list(self.webhook_sync_registry)
                    if not isinstance(self.webhook_sync_registry[key], str)
                ]
            )
        )
        await self.client.change_presence(
            activity=discord.Game(name="fletcher.fun | !help", start=datetime.utcnow())
        )

    def add_command(self, command):
        command["module"] = inspect.stack()[1][1].split("/")[-1][:-3]
        if type(command["trigger"]) != tuple:
            command["trigger"] = tuple(command["trigger"])
        logger.debug(f"Loading command {command}")
        if command.get("slash_command", command.get("message_command")) and len(
            command.get("whitelist_guild", [])
        ):
            command["guild_command_ids"] = {}
        self.commands.append(command)
        if (
            command.get("message_command")
            and self.config.get(
                section="discord", key="enable_message_commands", default=False
            )
            and len(command.get("whitelist_guild", []))
        ):
            for guild_id in command.get("whitelist_guild"):
                asyncio.get_event_loop().create_task(
                    self._add_message_command(
                        guild_id,
                        {
                            "name": command.get("trigger")[0][1:],
                            "default_permission": True,
                        },
                        len(self.commands) - 1,
                    )
                )
        if (
            command.get("slash_command")
            and self.config.get(
                section="discord", key="enable_slash_commands", default=False
            )
            and len(command.get("whitelist_guild", []))
        ):
            for guild_id in command.get("whitelist_guild"):
                asyncio.get_event_loop().create_task(
                    self._add_slash_command(
                        guild_id,
                        {
                            "name": command.get("trigger")[0][1:],
                            "description": command.get("description", ""),
                            "options": [
                                {
                                    "name": command.get("args_name", [])[i].split(";")[
                                        0
                                    ]
                                    if i < len(command.get("args_name", []))
                                    else f"{i}",
                                    "description": command.get("args_name", [])[
                                        i
                                    ].split(";")[-1]
                                    or "Nil",
                                    "type": 3,
                                    "required": i
                                    < command.get(
                                        "args_min", command.get("args_num", 0)
                                    ),
                                    "choices": [],
                                    "autocomplete": False,
                                }
                                for i in range(
                                    max(
                                        command.get("args_num", 0),
                                        len(command.get("args_name", [])),
                                    )
                                )
                            ],
                            "default_permission": True,
                        },
                        len(self.commands) - 1,
                    )
                )

    async def _add_message_command(
        self, guild_id: int, payload: dict, command_internal_id: int
    ) -> Awaitable[None]:
        if self.config.get(guild=guild_id, key="commands_disabled", default=False):
            return
        payload["type"] = 3
        try:
            async with message_handler_rate_limit:
                response = await self.client.http.upsert_guild_command(
                    self.user.id, guild_id, payload
                )
        except discord.Forbidden:
            logger.info(
                f"Disable guild commands on {guild_id} ({client.get_guild(guild_id).name})"
            )
        logger.debug(f"Respayload {payload} {response}")
        logger.debug(f"Registered {payload['name']} as {response['id']} in {guild_id}")
        self.commands[command_internal_id]["guild_command_ids"][
            response["id"]
        ] = guild_id

    async def _add_slash_command(
        self, guild_id: int, payload: dict, command_internal_id: int
    ) -> Awaitable[None]:
        response = await self.client.http.upsert_guild_command(
            self.user.id, guild_id, payload
        )
        logger.debug(f"Respayload {payload} {response}")
        logger.debug(f"Registered {payload['name']} as {response['id']} in {guild_id}")
        self.commands[command_internal_id]["guild_command_ids"][
            response["id"]
        ] = guild_id

    def add_remove_handler(self, func_name, func):
        self.remove_handlers[func_name] = func

    def add_join_handler(self, func_name, func):
        self.join_handlers[func_name] = func

    def add_reload_handler(self, func_name, func):
        self.reload_handlers[func_name] = func

    def add_message_reaction_remove_handler(self, message_ids, func):
        for message_id in message_ids:
            self.message_reaction_remove_handlers[message_id] = func

    def add_message_reply_handler(self, message_ids, func):
        for message_id in message_ids:
            self.message_reply_handlers[message_id] = func

    def add_message_reaction_handler(self, message_ids, func):
        for message_id in message_ids:
            self.message_reaction_handlers[message_id] = func

    async def tupper_proc(self, message: discord.abc.Messageable):
        global config
        global webhooks_cache
        tupperId = 431544605209788416
        sync = cast(dict, config.get(section="sync"))
        user = message.author
        thread: Optional[discord.Thread]
        channel: discord.Channel
        if isinstance(message.channel, discord.TextChannel):
            channel = message.channel
            thread = None
        elif isinstance(message.channel, discord.Thread):
            channel = message.channel.parent
            thread = message.channel
        else:
            return
        if not (
            message.guild
            and sync.get(f"tupper-ignore-{message.guild.id}")
            or sync.get(f"tupper-ignore-m{user.id}")
        ):
            return
        tupper = discord.utils.get(channel.members, id=tupperId)
        if tupper is not None:
            tupper_status = tupper.status
        else:
            tupper_status = None
        if (
            (tupper is not None)
            and (
                self.user_config(
                    user.id, None, "prefer-tupper", allow_global_substitute=True
                )
                == "1"
            )
            or (
                self.user_config(
                    user.id,
                    message.guild.id,
                    "prefer-tupper",
                    allow_global_substitute=True,
                )
                == "0"
            )
            and (tupper_status == discord.Status.online)
        ):
            return
        for prefix in tuple(sync.get(f"tupper-ignore-{message.guild.id}", [])) + tuple(
            sync.get(f"tupper-ignore-m{user.id}", [])
        ):
            tupperreplace = None
            if prefix and message.content.startswith(prefix.lstrip()):
                if sync.get(
                    f"tupper-replace-{message.guild.id}-{user.id}-{prefix}-nick"
                ):
                    tupperreplace = (
                        f"tupper-replace-{message.guild.id}-{user.id}-{prefix}"
                    )
                elif sync.get(f"tupper-replace-None-{user.id}-{prefix}-nick"):
                    tupperreplace = f"tupper-replace-None-{user.id}-{prefix}"
            if not tupperreplace:
                continue
            content = message.content[len(prefix) :]
            attachments = []
            if message.attachments:
                for attachment in message.attachments:
                    logger.debug("Syncing " + attachment.filename)
                    attachment_blob = BytesIO()
                    await attachment.save(attachment_blob)
                    attachments.append(
                        discord.File(attachment_blob, attachment.filename)
                    )
            fromMessageName = sync.get(f"{tupperreplace}-nick", user.display_name)
            reply_embed = []
            if message.reference:
                refGuild = message.guild
                assert refGuild is not None
                refChannel = refGuild.get_channel(
                    message.reference.channel_id
                ) or refGuild.get_thread(message.reference.channel_id)
                try:
                    refMessage = await refChannel.fetch_message(
                        message.reference.message_id
                    )
                    reply_embed = [
                        discord.Embed(
                            description=f"Reply to [{refMessage.author}]({refMessage.jump_url})"
                        )
                    ]
                except:
                    pass
            webhook = webhooks_cache.get(f"{message.guild.id}:{channel.id}")
            if not webhook:
                try:
                    webhooks = await channel.webhooks()
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(
                        f"Unable to list webhooks to fulfill your nickmask in {channel}! I need the manage webhooks permission to do that.",
                        user,
                    )
                    continue
                if webhooks:
                    webhook = discord.utils.get(
                        webhooks, name=config.get(section="discord", key="botNavel")
                    )
                if not webhook:
                    webhook = await channel.create_webhook(
                        name=config.get(section="discord", key="botNavel"),
                        reason="Autocreating for nickmask",
                    )
                webhooks_cache[f"{message.guild.id}:{channel.id}"] = webhook

            sent_message = await webhook.send(
                content=content,
                username=fromMessageName,
                avatar_url=sync.get(
                    f"{tupperreplace}-avatar",
                    user.display_avatar,
                ),
                embeds=[*message.embeds, *reply_embed],
                tts=message.tts,
                files=attachments,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False
                ),
                wait=True,
                **({"thread": thread} if thread else {}),
            )
            await self.bridge_message(sent_message, allow_webhook_checks=False)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO attributions (author_id, from_message, from_channel, from_guild, message, channel, guild) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                [
                    user.id,
                    None,
                    None,
                    None,
                    sent_message.id,
                    sent_message.channel.id,
                    sent_message.guild.id
                    if type(sent_message.channel) is not discord.DMChannel
                    else None,
                ],
            )
            conn.commit()
            try:
                return await message.delete()
            except discord.NotFound:
                return
            except discord.Forbidden:
                return await messagefuncs.sendWrappedMessage(
                    f"Unable to remove original message for nickmask in {channel}! I need the Manage Messages permission to do that.",
                    user,
                )

    async def web_handler(self, request):
        global webhooks_cache
        json = await request.json()
        remote_ip = self.config.get(
            guild=json["guild_id"],
            channel=json["channel_id"],
            key="remote_ip",
            default=None,
        )
        if request.remote == remote_ip or json.get(
            "rcon-password", ""
        ) == self.config.get(
            guild=json["guild_id"],
            channel=json["channel_id"],
            key="minecraft_rcon-password",
            default=None,
        ):
            guild = self.client.get_guild(json["guild_id"])
            if not guild:
                return web.Response(status=400)
            channel = guild.get_channel(json["channel_id"])
            if not channel:
                return web.Response(status=400)
            try:
                assert isinstance(channel, discord.TextChannel)
            except:
                return web.Response(status=400)
            webhook = webhooks_cache.get(f"{guild.id}:{channel.id}")
            if not webhook:
                try:
                    webhooks = await channel.webhooks()
                    if len(webhooks) > 0:
                        webhook = discord.utils.get(
                            webhooks, name=config.get(section="discord", key="botNavel")
                        )
                    if not webhook:
                        webhook = await channel.create_webhook(
                            name=str(
                                self.config.get(section="discord", key="botNavel")
                            ),
                            reason="Autocreating for web_handler",
                        )
                    webhooks_cache[f"{guild.id}:{channel.id}"] = webhook
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(json["message"], channel)
                    return web.Response(status=200)
            try:
                messageParts = re.search(
                    r"> (?:\[Not Secure\] )?<([^>]*)> (.*)", json["message"]
                )
                member = None
                if messageParts:
                    display_name, content = messageParts.groups()
                    member = discord.utils.get(
                        channel.members, display_name=display_name
                    )
                    assert member is not None
                    sent_message = await webhook.send(
                        content=content,
                        username=member.display_name,
                        avatar_url=member.display_avatar,
                        wait=True,
                    )
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO attributions (author_id, from_message, from_channel, from_guild, message, channel, guild, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                        [
                            member.id,
                            None,
                            None,
                            None,
                            sent_message.id,
                            channel.id,
                            guild.id,
                            "Bridged",
                        ],
                    )
                    conn.commit()
                else:
                    await messagefuncs.sendWrappedMessage(json["message"], channel)
            except (AttributeError, AssertionError):
                await messagefuncs.sendWrappedMessage(json["message"], channel)
            return web.Response(status=200)
        return web.Response(status=400)

    async def deletion_handler(self, message: discord.RawReactionActionEvent):
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            if TYPE_CHECKING:
                assert hub is not None
            with hub.configure_scope() as scope, hub.start_transaction(op="deletion_handler", name=str(message.message_id)):  # type: ignore
                try:
                    fromGuild = client.get_guild(message.guild_id)
                    fromChannel = fromGuild.get_channel_or_thread(message.channel_id)
                    if isinstance(fromChannel, (discord.Thread, discord.TextChannel)):
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
                    if fromGuild:
                        if isinstance(fromChannel, discord.TextChannel):
                            thread_id = self.config.get(
                                "bridge_target_thread",
                                channel=fromChannel,
                                guild=fromChannel.guild,
                                default=None,
                            )
                            if not thread_id:
                                bridge_key = (
                                    f"{fromChannel.guild.name}:{fromChannel.id}"
                                )
                            else:
                                bridge_key = ""
                        elif isinstance(fromChannel, discord.Thread):
                            thread_id = self.config.get(
                                "bridge_target_thread",
                                channel=fromChannel.parent,
                                guild=fromChannel.guild,
                                default=None,
                            )
                            if thread_id == fromChannel.id:
                                bridge_key = (
                                    f"{fromChannel.guild.name}:{fromChannel.parent.id}"
                                )
                            else:
                                bridge_key = ""
                        else:
                            raise AttributeError(
                                f"Unregistered {type(fromChannel)=} in bridge_key"
                            )
                    else:
                        bridge_key = ""
                    if message.guild_id == 429373449803399169:
                        logger.debug(
                            f"{bridge_key=}",
                            extra={"GUILD_IDENTIFIER": fromChannel.guild.name},
                        )
                    if isinstance(
                        fromChannel, (discord.Thread, discord.TextChannel)
                    ) and ch.webhook_sync_registry.get(bridge_key):
                        # Give messages time to be added to the database
                        await asyncio.sleep(1)
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT ctid, toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
                            [message.guild_id, message.channel_id, message.message_id],
                        )
                        if message.guild_id == 429373449803399169:
                            logger.debug(
                                f"{[message.guild_id, message.channel_id, message.message_id]=}",
                                extra={"GUILD_IDENTIFIER": fromChannel.guild.name},
                            )
                        metuples = cur.fetchall()
                        if metuples:
                            for i in range(len(metuples)):
                                thread_id = self.config.get(
                                    "bridge_target_thread",
                                    channel=metuples[i][2],
                                    guild=metuples[i][1],
                                    default=None,
                                )
                                if thread_id:
                                    metuples[i] = (
                                        metuples[0],
                                        metuples[1],
                                        thread_id,
                                        metuples[3],
                                    )
                        if not metuples:
                            cur.execute(
                                "SELECT ctid, toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND frommessage = %s;",
                                [message.guild_id, message.message_id],
                            )
                            metuples = cur.fetchall()
                        for metuple in metuples:
                            cur.execute(
                                "DELETE FROM messageMap WHERE ctid = %s AND fromguild = %s AND frommessage = %s",
                                [metuple[0], message.guild_id, message.message_id],
                            )
                        conn.commit()
                        for metuple in metuples:
                            toGuild = client.get_guild(metuple[1])
                            toChannel = toGuild.get_channel_or_thread(metuple[2])
                            thread_id = self.config.get(
                                "bridge_target_thread",
                                channel=toChannel,
                                guild=toguild,
                                default=None,
                            )
                            if thread_id:
                                toChannel = toChannel.get_thread(thread_id)
                            if not toChannel:
                                logger.debug(
                                    "Lookup issue for toChannel in this metuple"
                                )
                                continue
                            if not self.config.get(
                                key="sync-deletions", guild=toGuild, channel=toChannel
                            ):
                                logger.debug(
                                    f"ORMD: Demurring to delete edited message ctid={metuple[0]} at client guild request"
                                )
                                return
                            toMessage = None
                            tries = 0
                            while not toMessage and tries < 10:
                                try:
                                    tries += 1
                                    toMessage = await toChannel.fetch_message(
                                        metuple[3]
                                    )
                                except discord.NotFound as e:
                                    exc_type, exc_obj, exc_tb = exc_info()
                                    logger.error(
                                        f"ORMD[{exc_tb.tb_lineno}]: {type(e).__name__} {e}"
                                    )
                                    logger.error(
                                        f"ORMD[{exc_tb.tb_lineno}]: {metuple[0]}:{metuple[1]}:{metuple[2]}"
                                    )
                                    toMessage = None
                                    await asyncio.sleep(2 * tries)
                                    if tries < 10:
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
                except Exception as e:
                    if "cur" in locals() and "conn" in locals():
                        conn.rollback()
                    raise e

    async def reaction_handler(self, reaction):
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            if TYPE_CHECKING:
                assert hub is not None
            with hub.configure_scope() as scope, hub.start_transaction(op="reaction_handler", name=str(reaction.emoji)):  # type: ignore
                try:
                    global config
                    messageContent = str(reaction.emoji)
                    if reaction.guild_id:
                        channel = self.client.get_guild(
                            reaction.guild_id
                        ).get_channel_or_thread(reaction.channel_id)
                    else:
                        channel = self.client.get_channel(reaction.channel_id)
                    if channel is None:
                        logger.info("Channel does not exist")
                        return
                    assert isinstance(
                        channel,
                        (discord.TextChannel, discord.Thread, discord.DMChannel),
                    )
                    scope.set_tag(
                        "channel",
                        channel.name
                        if isinstance(channel, (discord.TextChannel, discord.Thread))
                        else "DM",
                    )
                    try:
                        message = await channel.fetch_message(reaction.message_id)
                    except discord.NotFound:
                        return
                    if message.guild:
                        user = message.guild.get_member(reaction.user_id)
                        if not user:
                            user = await message.guild.fetch_member(reaction.user_id)
                        scope.set_tag("guild", message.guild.name)
                    else:
                        user = self.client.get_user(reaction.user_id)
                        if not user:
                            user = await self.client.fetch_user(reaction.user_id)
                    if channel and hasattr(channel, "guild"):
                        member = channel.guild.get_member(user.id)
                        if not member:
                            member = await channel.guild.fetch_member(user.id)
                        if member:
                            user = member
                    assert isinstance(
                        user, (discord.User, discord.Member)
                    ), f"Dropping reaction, user {user=} ({type(user)=} not found"
                    scope.user = {"id": reaction.user_id, "username": str(user)}
                    admin = self.is_admin(message, user)
                    args = [reaction, user, "add"]
                    channel_config: Dict = {}
                    try:
                        channel_config = cast(
                            dict,
                            self.scope_config(
                                guild=message.guild, channel=message.channel
                            ),
                        )
                    except (AttributeError, ValueError) as e:
                        pass
                    if isinstance(channel, (discord.TextChannel, discord.Thread)):
                        logger.info(
                            f"{message.id} #{channel.guild.name}:{channel.name} <{user.name if user else 'Unknown User'}:{reaction.user_id}> reacting with {messageContent}",
                            extra={
                                "GUILD_IDENTIFIER": channel.guild.name,
                                "CHANNEL_IDENTIFIER": channel.name,
                                "SENDER_NAME": user.name if user else "Unkown User",
                                "SENDER_ID": reaction.user_id,
                                "MESSAGE_ID": str(message.id),
                                "REACTION_IDENTIFIER": messageContent,
                            },
                        )
                    elif isinstance(channel, discord.DMChannel):
                        if channel.recipient is None:
                            channel = client.get_channel(channel.id)
                        logger.info(
                            f"{message.id} @{channel.recipient.name if channel.recipient else channel.id} <{user.name if user else 'Unknown User'}:{reaction.user_id}> reacting with {messageContent}",
                            extra={
                                "GUILD_IDENTIFIER": "@",
                                "CHANNEL_IDENTIFIER": channel.recipient.name
                                if channel.recipient
                                else channel.id,
                                "SENDER_NAME": user.name if user else "Unkown User",
                                "SENDER_ID": reaction.user_id,
                                "MESSAGE_ID": str(message.id),
                                "REACTION_IDENTIFIER": messageContent,
                            },
                        )
                    else:
                        # Group Channels don't support bots so neither will we
                        pass
                    assert isinstance(
                        user, (discord.User, discord.Member)
                    ), f"Dropping reaction, user {user=} ({type(user)=} not found"
                    if (
                        channel_config.get("blacklist-emoji")
                        and not admin["channel"]
                        and messageContent
                        in cast(Iterable, channel_config.get("blacklist-emoji"))
                    ):
                        logger.info("Emoji removed by blacklist")
                        return await message.remove_reaction(messageContent, user)
                    args = [reaction, user, "add"]
                    scoped_command = None
                    message_handler = self.message_reaction_handlers.get(message.id)
                    channel_handler = self.message_reaction_handlers.get(channel.id)
                    if (
                        message_handler is not None
                        and message_handler.scope == discord.Message
                    ):
                        scoped_command = message_handler
                    if (
                        channel_handler is not None
                        and channel_handler.scope == discord.TextChannel
                    ):
                        scoped_command = channel_handler
                    try:
                        if channel.guild:
                            if isinstance(channel, discord.TextChannel):
                                thread_id = self.config.get(
                                    "bridge_target_thread",
                                    channel=channel,
                                    guild=channel.guild,
                                    default=None,
                                )
                                if not thread_id:
                                    bridge_key = f"{channel.guild.name}:{channel.id}"
                                else:
                                    bridge_key = ""
                            elif isinstance(channel, discord.Thread):
                                thread_id = self.config.get(
                                    "bridge_target_thread",
                                    channel=channel.parent,
                                    guild=channel.guild,
                                    default=None,
                                )
                                if thread_id == channel.id:
                                    bridge_key = (
                                        f"{channel.guild.name}:{channel.parent.id}"
                                    )
                                else:
                                    bridge_key = ""
                            else:
                                raise AttributeError(
                                    f"Unregistered {type(channel)=} in bridge_key"
                                )
                        else:
                            bridge_key = ""
                        if isinstance(
                            channel, (discord.Thread, discord.TextChannel)
                        ) and await self.bridge_registry(bridge_key):
                            if reaction.emoji.is_custom_emoji():
                                processed_emoji = self.client.get_emoji(
                                    reaction.emoji.id
                                )
                            else:
                                processed_emoji = reaction.emoji.name
                            if processed_emoji is None:
                                image = (
                                    await netcode.simple_get_image(
                                        f"https://cdn.discordapp.com/emojis/{reaction.emoji.id}.png?v=1"
                                    )
                                ).read()
                                try:
                                    processed_emoji = (
                                        await self.emote_server.create_custom_emoji(
                                            name=reaction.emoji.name,
                                            image=image,
                                            reason=f"messagemap sync code",
                                        )
                                    )
                                except discord.Forbidden:
                                    logger.error("discord.emoteServer misconfigured!")
                                except discord.HTTPException:
                                    await random.choice(
                                        self.emote_server.emojis
                                    ).delete()
                                    processed_emoji = (
                                        await self.emote_server.create_custom_emoji(
                                            name=reaction.emoji.name,
                                            image=image,
                                            reason=f"messagemap sync code",
                                        )
                                    )
                            if not processed_emoji:
                                return
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT fromguild, fromchannel, frommessage FROM messagemap WHERE toguild = %s AND tochannel = %s AND tomessage = %s;",
                                [channel.guild.id, channel.id, message.id],
                            )
                            metuple = cur.fetchone()
                            while metuple is not None:
                                fromGuild = self.client.get_guild(metuple[0])
                                try:
                                    assert fromGuild is not None
                                except AssertionError:
                                    logger.error(
                                        f"RXH: {metuple} fromGuild not found",
                                        extra={"GUILD_IDENTIFIER": fromGuild.name},
                                    )
                                    cur.fetchone()
                                    conn.rollback()
                                    continue
                                fromChannel = fromGuild.get_channel_or_thread(
                                    metuple[1]
                                )
                                try:
                                    assert isinstance(
                                        fromChannel,
                                        (discord.TextChannel, discord.Thread),
                                    )
                                except AssertionError:
                                    logger.error(
                                        f"RXH: {metuple} tried to bridge {type(fromChannel)}",
                                        extra={"GUILD_IDENTIFIER": fromGuild.name},
                                    )
                                    metuple = cur.fetchone()
                                    continue
                                fromMessage = await fromChannel.fetch_message(
                                    metuple[2]
                                )
                                if fromMessage.author.id in cast(
                                    Iterable,
                                    config.get(
                                        section="moderation",
                                        key="blacklist-user-usage",
                                        default=[],
                                    ),
                                ):
                                    logger.debug(
                                        "Demurring to bridge reaction to message of users on the blacklist",
                                        extra={"GUILD_IDENTIFIER": fromGuild.name},
                                    )
                                    return
                                already_sent = next(
                                    filter(
                                        lambda emoji: emoji == reaction.emoji,
                                        fromMessage.reactions,
                                    ),
                                    None,
                                )
                                if (
                                    type(processed_emoji) is not str
                                    and processed_emoji.guild_id == self.emote_server.id
                                    and already_sent is not None
                                ):
                                    if already_sent.me:
                                        metuple = cur.fetchone()
                                        continue
                                logger.debug(
                                    f"RXH: {processed_emoji} -> {fromMessage.id} ({fromGuild.name})",
                                    extra={"GUILD_IDENTIFIER": fromGuild.name},
                                )
                                await fromMessage.add_reaction(processed_emoji)
                                metuple = cur.fetchone()
                                # cur = conn.cursor()
                                # cur.execute(
                                #     "UPDATE messagemap SET reactions = reactions || %s WHERE toguild = %s AND tochannel = %s AND tomessage = %s;",
                                #     [
                                #         str(processed_emoji),
                                #         message.guild.id,
                                #         message.channel.id,
                                #         message.id,
                                #     ],
                                # )
                                # conn.commit()
                            conn.commit()
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
                                [channel.guild.id, channel.id, message.id],
                            )
                            metuple = cur.fetchone()
                            while metuple is not None:
                                toGuild = self.client.get_guild(metuple[0])
                                assert toGuild is not None
                                toChannel = toGuild.get_channel_or_thread(metuple[1])
                                assert isinstance(
                                    toChannel, (discord.TextChannel, discord.Thread)
                                )
                                try:
                                    toMessage = await toChannel.fetch_message(
                                        metuple[2]
                                    )
                                except discord.Forbidden:
                                    return
                                except discord.NotFound:
                                    return
                                if not toMessage:
                                    return
                                if toMessage.author.id in cast(
                                    Iterable,
                                    config.get(
                                        section="moderation",
                                        key="blacklist-user-usage",
                                        default=[],
                                    ),
                                ):
                                    logger.debug(
                                        "Demurring to bridge reaction to message of users on the blacklist",
                                        extra={"GUILD_IDENTIFIER": message.guild.name},
                                    )
                                    return
                                logger.debug(
                                    f"RXH: {processed_emoji} -> {toMessage.id} ({toGuild.name})",
                                    extra={"GUILD_IDENTIFIER": message.guild.name},
                                )
                                await toMessage.add_reaction(processed_emoji)
                                metuple = cur.fetchone()
                                # cur = conn.cursor()
                                # cur.execute(
                                #     f'UPDATE messagemap SET reactions = reactions || %s WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;',
                                #     [
                                #         str(processed_emoji),
                                #         message.guild.id,
                                #         message.channel.id,
                                #         message.id,
                                #     ],
                                # )
                                # conn.commit()
                            conn.commit()
                    except discord.InvalidArgument as e:
                        if "cur" in locals() and "conn" in locals():
                            conn.rollback()
                            pass
                    if scoped_command:
                        logger.debug(scoped_command)
                        if (
                            messageContent.startswith(tuple(scoped_command.trigger))
                            and self.allowCommand(scoped_command, message, user=user)
                            and scoped_command.remove is False
                            and scoped_command.arguments.get("min_count", 0) == 0
                        ):
                            await self.run_command(scoped_command, message, args, user)
                            if not scoped_command.exclusive:
                                return
                    else:
                        if not self.config.get(
                            guild=message.guild, key="active-emoji", default=False
                        ):
                            return
                        for command in self.get_command(
                            messageContent, message, max_args=0
                        ):
                            if isinstance(command, dict) or not command.remove:
                                await self.run_command(command, message, args, user)
                except Exception as e:
                    if "cur" in locals() and "conn" in locals():
                        conn.rollback()
                    _, _, exc_tb = exc_info()
                    assert exc_tb is not None
                    logger.debug(traceback.format_exc())
                    logger.error(f"RXH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    async def reaction_remove_handler(self, reaction):
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            with hub.configure_scope() as scope, hub.start_transaction(op="reaction_remove_handler", name=str(reaction.emoji)):  # type: ignore
                try:
                    global config
                    messageContent = str(reaction.emoji)
                    channel = self.client.get_channel(reaction.channel_id)
                    user = None
                    user = self.client.get_user(reaction.user_id)
                    if not user:
                        user = await self.client.fetch_user(reaction.user_id)
                    if channel and hasattr(channel, "guild"):
                        member = channel.guild.get_member(user.id)
                        if not member:
                            member = await channel.guild.fetch_member(user.id)
                        if member:
                            user = member
                    assert user is not None
                    if channel is None:
                        channel = user.create_dm()
                    if channel is None:
                        logger.info("Channel does not exist")
                        return
                    assert isinstance(
                        user, (discord.User, discord.Member)
                    ), f"Dropping reaction, user {user=} ({type(user)=} not found"
                    assert isinstance(
                        channel,
                        (discord.TextChannel, discord.Thread, discord.DMChannel),
                    )
                    scope.set_tag(
                        "channel",
                        channel.name
                        if isinstance(channel, (discord.TextChannel, discord.Thread))
                        else "DM",
                    )
                    if isinstance(channel, (discord.TextChannel, discord.Thread)):
                        if not user:
                            user = channel.guild.get_member(reaction.user_id)
                        if not user:
                            user = await channel.guild.fetch_member(reaction.user_id)
                        scope.set_tag("guild", channel.guild.name)
                    assert isinstance(
                        user, (discord.User, discord.Member)
                    ), f"Dropping reaction, user {user=} ({type(user)=} not found"
                    scope.user = {"id": user.id if user else 0, "username": str(user)}
                    message = await channel.fetch_message(reaction.message_id)
                    assert isinstance(
                        user, (discord.User, discord.Member)
                    ), f"user is messed up, <{type(user)}> {user=}"
                    if isinstance(channel, (discord.TextChannel, discord.Thread)):
                        logger.info(
                            f"{message.id} #{channel.guild.name}:{channel.name} <{user.name}:{user.id}> unreacting with {messageContent}",
                            extra={
                                "GUILD_IDENTIFIER": channel.guild.name,
                                "CHANNEL_IDENTIFIER": channel.name,
                                "SENDER_NAME": user.name,
                                "SENDER_ID": user.id,
                                "MESSAGE_ID": str(message.id),
                                "REACTION_IDENTIFIER": messageContent,
                            },
                        )
                    elif type(channel) is discord.DMChannel:
                        if channel.recipient is None:
                            channel = client.get_channel(channel.id)
                        logger.info(
                            f"{message.id} @{channel.recipient.name if channel.recipient else channel.id} <{user.name}:{user.id}> unreacting with {messageContent}",
                            extra={
                                "GUILD_IDENTIFIER": "@",
                                "CHANNEL_IDENTIFIER": channel.recipient.name
                                if channel.recipient
                                else channel.id,
                                "SENDER_NAME": user.name,
                                "SENDER_ID": user.id,
                                "MESSAGE_ID": str(message.id),
                                "REACTION_IDENTIFIER": messageContent,
                            },
                        )
                    else:
                        # Group Channels don't support bots so neither will we
                        pass
                    args = [reaction, user, "remove"]
                    command = self.message_reaction_remove_handlers.get(message.id)
                    if command and self.allowCommand(command, message, user=user):
                        if not self.config.get(
                            guild=message.guild, key="active-emoji", default=False
                        ) and not command.get("exclusive", False):
                            return
                        await self.run_command(command, message, args, user)
                        if command.get("exclusive", False):
                            return
                    for command in self.get_command(
                        messageContent, message, max_args=0
                    ):
                        if self.allowCommand(
                            command, message, user=user
                        ) and command.get("remove"):
                            await self.run_command(command, message, args, user)
                except Exception as e:
                    _, _, exc_tb = exc_info()
                    assert exc_tb is not None
                    logger.error(f"RRH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    async def remove_handler(self, user):
        global config
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            with hub.configure_scope() as scope, hub.start_transaction(
                op="member_remove_handler", name=str(user)
            ):
                scope.user = {"id": user.id, "username": str(user)}
                scope.set_tag("guild", user.guild.name)
                member_remove_actions = config.get(
                    guild=user.guild, key="on_member_remove_list", default=[]
                )
                for member_remove_action in member_remove_actions:
                    if member_remove_action in self.remove_handlers.keys():
                        await self.remove_handlers[member_remove_action](
                            user, self.client, self.scope_config(guild=user.guild)
                        )
                    else:
                        logger.error(
                            f"Unknown member_remove_action [{member_remove_action}]"
                        )

    async def join_handler(self, user):
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            with hub.configure_scope() as scope, hub.start_transaction(op="member_join_handler", name=str(user)):  # type: ignore
                scope.user = {"id": user.id, "username": str(user)}
                scope.set_tag("guild", user.guild.name)
                member_join_actions = cast(
                    Iterable[str],
                    config.get(guild=user.guild, key="on_member_join_list", default=[]),
                )
                if (
                    user.guild.get_member(self.user)
                    and user.guild.get_member(self.user).manage_channels
                ):
                    guild_invites = self.guild_invites[user.guild.id]
                    self.guild_invites[user.guild.id] = {
                        invite.code: invite for invite in await user.guild.invites()
                    }
                    for code in guild_invites.keys():
                        if (
                            not self.guild_invites[user.guild.id].get(code)
                        ) or self.guild_invites[user.guild.id].uses < guild_invites[
                            user.guild.id
                        ].uses:
                            logger.info(
                                f"#{user.guild.name}:{user.name} <join> {user.name} joined via {code}",
                                extra={
                                    "SENDER_NAME": user.name,
                                    "SENDER_ID": user.id,
                                    "CODE": code,
                                    "GUILD_IDENTIFIER": user.guild.name,
                                },
                            )
                            break
                for member_join_action in filter(None, member_join_actions):
                    if member_join_action in self.join_handlers.keys():
                        await self.join_handlers[member_join_action](
                            user, self.client, self.scope_config(guild=user.guild)
                        )
                    else:
                        logger.error(
                            f"Unknown member_join_action [{member_join_action}]"
                        )

    async def channel_update_handler(self, before, after):
        if not before.guild:
            return
        if (
            isinstance(before, (discord.TextChannel, discord.Thread))
            and before.name != after.name
        ):
            logger.info(
                f"#{before.guild.name}:{before.name} <name> Name changed from {before.name} to {after.name}",
                extra={
                    "GUILD_IDENTIFIER": before.guild.name,
                    "CHANNEL_IDENTIFIER": before.name,
                },
            )
            if self.config.get(
                "name_change_notify", False, guild=before.guild.id, channel=before.id
            ):
                await messagefuncs.sendWrappedMessage(
                    cast(
                        str,
                        self.config.get(
                            "name_change_notify_message",
                            "Name changed from {before.name} to {after.name}",
                            guild=before.guild.id,
                            channel=before.id,
                        ),
                    ).format(before=before, after=after),
                    after,
                )
        if isinstance(before, discord.TextChannel) and before.topic != after.topic:
            logger.info(
                f"#{before.guild.name}:{before.name} <topic> Topic changed from {before.topic} to {after.topic}",
                extra={
                    "GUILD_IDENTIFIER": before.guild.name,
                    "CHANNEL_IDENTIFIER": before.name,
                },
            )
            if self.config.get(
                "topic_change_notify", False, guild=before.guild.id, channel=before.id
            ):
                await messagefuncs.sendWrappedMessage(
                    cast(
                        str,
                        self.config.get(
                            "topic_change_notify_message",
                            "Topic changed from {before.topic} to {after.topic}",
                            guild=before.guild.id,
                            channel=before.id,
                        ),
                    ).format(before=before, after=after),
                    after,
                )

    async def load_guild_invites(self, guild):
        self.guild_invites[guild.id] = {
            invite.code: invite for invite in await guild.invites()
        }

    async def reload_handler(self):
        try:
            loop = asyncio.get_event_loop()
            # Trigger reload handlers
            successful_events = []
            for guild in self.client.guilds:
                member = guild.get_member(self.user.id)
                assert member is not None
                if member.guild_permissions.manage_guild and self.config.get(
                    section="discord", key="load_guild_invites", default=False
                ):
                    loop.create_task(self.load_guild_invites(guild))
                reload_actions = cast(
                    Iterable,
                    self.config.get(guild=guild.id, key="on_reload_list", default=[]),
                )
                for reload_action in reload_actions:
                    if reload_action in self.reload_handlers.keys():
                        for t in asyncio.all_tasks(loop):
                            if t.get_name() == f"{reload_action}-{guild.id}":
                                t.cancel()
                        loop.create_task(
                            self.reload_handlers[reload_action](
                                guild, self.client, self.scope_config(guild=guild)
                            ),
                            name=f"{reload_action}-{guild.id}",
                        )
                        successful_events.append(f"{guild.name}: {reload_action}")
                    else:
                        logger.error(f"Unknown reload_action [{reload_action}]")
            return successful_events
        except Exception as e:
            _, _, exc_tb = exc_info()
            assert exc_tb is not None
            logger.error(f"RLH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    @cached(TTLCache(1024, 86400))
    async def fetch_webhook_cached(self, webhook_id):
        try:
            webhook = await self.client.fetch_webhook(webhook_id)
        except discord.Forbidden:
            logger.debug(
                f"Fetch webhook failed for {webhook_id} due to missing permissions"
            )
            webhook = discord.Webhook.partial(
                -1, "loading-forbidden", session=ClientSession()
            )
        return webhook

    async def bridge_message(self, message, allow_webhook_checks: bool = True):
        global conn
        try:
            if not message.guild:
                return
            if isinstance(message.channel, discord.TextChannel):
                thread_id = self.config.get(
                    "bridge_target_thread",
                    channel=message.channel,
                    guild=message.channel.guild,
                    default=None,
                )
                if not thread_id:
                    bridge_key = f"{message.guild.name}:{message.channel.id}"
                else:
                    bridge_key = ""
            elif isinstance(message.channel, discord.Thread):
                thread_id = self.config.get(
                    "bridge_target_thread",
                    channel=message.channel.parent,
                    guild=message.channel.guild,
                    default=None,
                )
                if thread_id == message.channel.id:
                    bridge_key = f"{message.guild.name}:{message.channel.parent.id}"
                else:
                    bridge_key = ""
            else:
                raise AttributeError(
                    f"Unregistered {type(message.channel)=} in bridge_key"
                )
            bridge = await self.bridge_registry(bridge_key)
        except AttributeError as e:
            _, _, exc_tb = exc_info()
            assert exc_tb is not None
            logger.info(f"BM[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
            return
        user = message.author
        # if the message is from the bot itself or sent via webhook, which is usually done by a bot, ignore it if not in whitelist
        if (
            message.webhook_id
            and allow_webhook_checks
            and self.config.get(section="sync", key="whitelist-webhooks")
        ):
            try:
                webhook = await self.fetch_webhook_cached(message.webhook_id)
            except discord.NotFound:
                return
            if webhook.name not in cast(
                Iterable, self.config.get(section="sync", key="whitelist-webhooks")
            ):
                if webhook.name and not webhook.name.startswith(
                    cast(str, self.config.get(section="discord", key="botNavel"))
                ):
                    # logger.debug("Webhook isn't whitelisted for bridging")
                    pass
                return
        elif (
            message.webhook_id
            and allow_webhook_checks
            and self.config.get(section="sync", key="denylist-webhooks")
        ):
            try:
                webhook = await self.fetch_webhook_cached(message.webhook_id)
            except discord.NotFound:
                return
            if any(
                (
                    webhook.name.startswith(hook)
                    for hook in cast(
                        Iterable,
                        self.config.get(section="sync", key="denylist-webhooks"),
                    )
                    if isinstance(webhook.name, str)
                )
            ):
                return
        spoilers = cast(
            list,
            self.config.get(section="sync", key=f"spoilerlist-{message.guild.id}")
            or [],
        ) + cast(
            list, self.config.get(guild=message.guild.id, key=f"spoilerlist") or []
        )
        ignores = list(
            filter(
                "".__ne__,
                cast(
                    list,
                    self.config.get(
                        section="sync", key=f"tupper-ignore-{message.guild.id}"
                    )
                    or [],
                )
                + cast(
                    list,
                    self.config.get(section="sync", key=f"tupper-ignore-m{user.id}")
                    or [],
                ),
            )
        )
        ignores.append("!mobilespoil")
        if (
            not message.webhook_id
            and len(ignores)
            and message.content.startswith(tuple(ignores))
        ):
            logger.info("Not bridging due to ignores")
            return
        if "Bridge" in str(type(bridge)):
            bridge = cast(Bridge, bridge)
            if "sync" in message.channel.name:
                logger.debug(f"ignores: {bridge=}")
            for i in range(len(bridge.webhooks)):
                attachments = []
                for attachment in message.attachments:
                    logger.debug(f"Syncing {attachment.filename}")
                    attachment_blob = BytesIO()
                    await attachment.save(attachment_blob)
                    attachments.append(
                        discord.File(attachment_blob, attachment.filename)
                    )
                content = message.content or " "
                if message.author.id in spoilers:
                    content = f"||{content}||"
                if len(message.attachments) > 0 and (
                    message.channel.is_nsfw() and not bridge.channels[i].is_nsfw()
                ):
                    content += f"\n {len(message.attachments)} file{'s' if len(message.attachments) > 1 else ''} attached from an R18 channel."
                    for attachment in message.attachments:
                        content += f"\n• <{attachment.url}>"

                user_mentions = []
                try:
                    content = re.sub(
                        r"@.*?#0000",
                        lambda member: list_append(
                            user_mentions,
                            bridge.channels[i].guild.get_member_named(member[0][1:-5]),
                        ).mention,
                        content,
                    )
                except AttributeError:
                    # Skipping substitution
                    pass
                # TODO support thread here maybe
                content = content.replace(
                    message.channel.mention, bridge.channels[i].mention
                )
                toMember = bridge.channels[i].guild.get_member(user.id)
                fromMessageName = (
                    toMember.display_name if toMember else user.display_name
                )
                # wait=True: blocking call for messagemap insertions to work
                syncMessage = None
                reply_embed = []
                if (
                    message.reference
                    and message.type is not discord.MessageType.pins_add
                ):
                    query_params = [
                        message.reference.guild_id,
                        message.reference.channel_id,
                        message.reference.message_id,
                        bridge.channels[i].guild.id,
                    ]
                    metuple = None
                    if query_params[0] == query_params[3]:
                        metuple = query_params[:3]
                    if metuple is None or len(metuple) != 3:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s AND toguild = %s LIMIT 1;",
                            query_params,
                        )
                        metuple = cur.fetchone()
                        conn.commit()
                    if metuple is None or len(metuple) != 3:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT fromguild, fromchannel, frommessage FROM messagemap WHERE toguild = %s AND tochannel = %s AND tomessage = %s LIMIT 1;",
                            query_params[:3],
                        )
                        metuple = cur.fetchone()
                        conn.commit()
                        if metuple and metuple[0] != bridge.channels[i].guild.id:
                            query_params = list(metuple)
                            query_params.append(bridge.channels[i].guild.id)
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s AND toguild = %s LIMIT 1;",
                                query_params,
                            )
                            metuple = cur.fetchone()
                            conn.commit()
                    if metuple is not None and len(metuple) == 3:
                        toGuild = self.client.get_guild(metuple[0])
                        toChannel = toGuild.get_channel(
                            metuple[1]
                        ) or toGuild.get_thread(metuple[1])
                        reference_message = await toChannel.fetch_message(metuple[2])
                        reply_embed = [
                            discord.Embed(
                                description=f"Reply to [{reference_message.author}]({reference_message.jump_url})"
                            )
                        ]
                if user.bot:
                    embeds = list(filter(None, message.embeds + reply_embed))
                else:
                    embeds = reply_embed
                try:
                    if "sync" in message.channel.name:
                        logger.debug(
                            f"sending to {bridge.webhooks[i]=} {bridge.webhooks[i].url}"
                        )
                    syncMessage = await messagefuncs.sendWrappedMessage(
                        target=bridge.webhooks[i],
                        msg=content,
                        username=fromMessageName,
                        avatar_url=user.display_avatar,
                        embeds=embeds,
                        tts=message.tts,
                        files=[]
                        if len(message.attachments) > 0
                        and (
                            message.channel.is_nsfw()
                            and not bridge.channels[i].is_nsfw()
                        )
                        else attachments,
                        wait=True,
                        allowed_mentions=discord.AllowedMentions(
                            users=user_mentions, roles=False, everyone=False
                        ),
                        **({"thread": bridge.threads[i]} if bridge.threads[i] else {}),
                    )
                    if "sync" in message.channel.name:
                        logger.debug(f"sent {syncMessage=} to {bridge.webhooks[i]=}")
                except discord.HTTPException as e:
                    if "sync" in message.channel.name:
                        exc_type, exc_obj, exc_tb = exc_info()
                        logger.error(f"B[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                    if attachments:
                        content += f"\n {len(message.attachments)} file{'s' if len(message.attachments) > 1 else ''} attached (too large to bridge)."
                        for attachment in message.attachments:
                            content += f"\n• <{attachment.url}>"
                        syncMessage = await messagefuncs.sendWrappedMessage(
                            target=bridge.webhooks[i],
                            msg=content,
                            username=fromMessageName,
                            avatar_url=user.display_avatar,
                            embeds=embeds,
                            tts=message.tts,
                            files=[],
                            wait=True,
                            allowed_mentions=discord.AllowedMentions(
                                users=user_mentions, roles=False, everyone=False
                            ),
                            thread=bridge.thread_ids[i],
                        )
                    else:
                        exc_type, exc_obj, exc_tb = exc_info()
                        logger.error(f"B[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                except Exception as e:
                    if "sync" in message.channel.name:
                        exc_type, exc_obj, exc_tb = exc_info()
                        logger.error(f"B[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                    raise e
                if syncMessage:
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO messagemap (fromguild, fromchannel, frommessage, toguild, tochannel, tomessage) VALUES (%s, %s, %s, %s, %s, %s);",
                            [
                                message.guild.id,
                                message.channel.id,
                                message.id,
                                syncMessage.guild.id,
                                syncMessage.channel.id,
                                syncMessage.id,
                            ],
                        )
                        conn.commit()
                    except Exception as e:
                        if "cur" in locals() and "conn" in locals():
                            conn.rollback()
                        exc_type, exc_obj, exc_tb = exc_info()
                        logger.error(f"B[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        if "sync" in message.channel.name:
            logger.debug(
                str(
                    self.config.get(
                        guild=message.guild.id,
                        channel=message.channel.id,
                        key="bridge_function",
                        use_category_as_channel_fallback=False,
                    )
                )
            )
        if (
            self.config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="bridge_function",
                use_category_as_channel_fallback=False,
            )
            and message.author.id != self.client.user.id
            and len(message.content)
            and len(
                self.get_command(
                    self.config.get(
                        guild=message.guild.id,
                        channel=message.channel.id,
                        key="bridge_function",
                    ),
                    message,
                    min_args=1,
                )
            )
        ):
            if message.webhook_id:
                await asyncio.sleep(1)
            cur = conn.cursor()
            cur.execute(
                "SELECT description FROM attributions WHERE message = %s AND channel = %s AND guild = %s",
                [message.id, message.channel.id, message.guild.id],
            )
            subtuple = cur.fetchone()
            if subtuple and subtuple[0] == "Bridged":
                conn.commit()
            else:
                conn.commit()
                await self.run_command(
                    self.get_command(
                        self.config.get(
                            guild=message.guild.id,
                            channel=message.channel.id,
                            key="bridge_function",
                        ),
                        message,
                        min_args=1,
                    )[0],
                    message,
                    message.content.split(" "),
                    user,
                    ignore_stranger_danger=True,
                )

    async def typing_handler(self, channel, user):
        if (
            user != self.client.user
            and type(channel) is discord.TextChannel
            and channel.guild
            and (
                bridge := self.webhook_sync_registry.get(
                    f"{channel.guild.name}:{channel.id}"
                )
            )
        ):
            await bridge.typing(except_for=channel)

    async def edit_handler(self, message):
        try:
            if (
                isinstance(message.channel, discord.DMChannel)
                and self.client.get_channel(message.channel.id) is None
            ):
                await message.author.create_dm()
            fromMessage = message
            fromChannel = message.channel
            if hasattr(message, "guild"):
                fromGuild = message.guild
            else:
                fromGuild = None
            if len(fromMessage.content) > 0:
                if isinstance(fromChannel, (discord.TextChannel, discord.Thread)):
                    logger.info(
                        f"{message.id} #{fromChannel.guild.name}:{fromChannel.name} <{fromMessage.author.name}:{fromMessage.author.id}> [Edit] {fromMessage.content}",
                        extra={
                            "GUILD_IDENTIFIER": fromChannel.guild.name,
                            "CHANNEL_IDENTIFIER": fromChannel.name,
                            "SENDER_NAME": fromMessage.author.name,
                            "SENDER_ID": fromMessage.author.id,
                            "MESSAGE_ID": str(fromMessage.id),
                        },
                    )
                elif isinstance(fromChannel, discord.DMChannel):
                    if fromChannel.recipient is None:
                        fromChannel = self.client.get_channel(fromChannel.id)
                    logger.info(
                        f"{message.id} @{fromChannel.recipient.name if fromChannel.recipient else fromChannel.id} <{fromMessage.author.name}:+{fromMessage.author.id}> [Edit] {fromMessage.content}",
                        extra={
                            "GUILD_IDENTIFIER": "@",
                            "CHANNEL_IDENTIFIER": fromChannel.recipient.name
                            if fromChannel.recipient
                            else fromChannel.id,
                            "SENDER_NAME": fromMessage.author.name,
                            "SENDER_ID": fromMessage.author.id,
                            "MESSAGE_ID": str(fromMessage.id),
                        },
                    )
                else:
                    # Group Channels don't support bots so neither will we
                    pass
            else:
                # Currently, we don't log empty or image-only messages
                pass
            if fromGuild:
                if isinstance(fromMessage.channel, discord.TextChannel):
                    bridge_key = f"{fromMessage.guild.name}:{fromMessage.channel.id}"
                elif isinstance(fromMessage.channel, discord.Thread):
                    thread_id = self.config.get(
                        "bridge_target_thread",
                        channel=fromMessage.channel.parent,
                        guild=fromMessage.channel.guild,
                        default=None,
                    )
                    if thread_id == fromMessage.channel.id:
                        bridge_key = (
                            f"{fromMessage.guild.name}:{fromMessage.channel.parent.id}"
                        )
                    else:
                        bridge_key = ""
                else:
                    logger.debug(
                        f"Unregistered {type(fromMessage.channel)=} in bridge_key"
                    )
                    bridge_key = ""
            else:
                bridge_key = ""
            if (
                fromGuild
                and self.config.get(guild=fromGuild, key="synchronize")
                and await self.bridge_registry(bridge_key)
            ):
                await asyncio.sleep(1)
                cur = conn.cursor()
                query_params = [
                    fromGuild.id,
                    fromChannel.id,
                    message.id,
                ]
                cur.execute(
                    "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
                    query_params,
                )
                metuples = cur.fetchall()
                conn.commit()
                logger.debug(
                    f"[Bridge] {query_params} -> {metuples}",
                    extra={"GUILD_IDENTIFIER": fromGuild.name},
                )
            else:
                metuples = []
            for metuple in metuples:
                guild_id, channel_id, message_id = metuple
                toGuild = self.client.get_guild(guild_id)
                assert toGuild is not None
                toChannel = toGuild.get_channel(channel_id)
                assert toChannel is not None
                toMessage = await toChannel.fetch_message(message_id)
                if message.pinned:
                    await toMessage.pin()
                    return
                if not self.config.get(
                    key="sync-edits",
                    guild=toGuild.id,
                    channel=toChannel.id,
                    use_category_as_channel_fallback=False,
                ):
                    logger.debug(
                        f"ORMU: Demurring to edit message at client guild request",
                        extra={"GUILD_IDENTIFIER": fromGuild.name},
                    )
                    return
                if self.config.get(
                    key="sync-deletions",
                    guild=toGuild.id,
                    channel=toChannel.id,
                    use_category_as_channel_fallback=False,
                ):
                    try:
                        # await toMessage.delete()
                        pass
                    except discord.NotFound:
                        return
                    except discord.Forbidden:
                        logger.info(
                            f"Unable to remove original message for bridge in {message.channel}! I need the manage messages permission to do that.",
                            extra={"GUILD_IDENTIFIER": fromGuild.name},
                        )
                reply_embed = []
                if fromMessage.reference:
                    reference_message = await fromMessage.channel.fetch_message(
                        fromMessage.reference.message_id
                    )
                    if reference_message:
                        reply_embed = [
                            discord.Embed(
                                description=f"Reply to [{reference_message.author}]({reference_message.jump_url})"
                            )
                        ]
                content = fromMessage.clean_content
                attachments: List[discord.File] = []
                if len(fromMessage.attachments) > 0:
                    plural = ""
                    if len(fromMessage.attachments) > 1:
                        plural = "s"
                    if (
                        fromMessage.channel.is_nsfw()
                        and not (
                            await self.bridge_registry(
                                f"{fromMessage.guild.name}:{fromMessage.channel.id}"
                            )
                        )
                        .channels[0]
                        .is_nsfw()
                    ):
                        content = f"{content}\n {len(message.attachments)} file{plural} attached from an R18 channel."
                        for attachment in fromMessage.attachments:
                            content = f"{content}\n• <{attachment.url}>"
                    else:
                        for attachment in fromMessage.attachments:
                            logger.debug(
                                f"Syncing {attachment.filename}",
                                extra={"GUILD_IDENTIFIER": fromGuild.name},
                            )
                            attachment_blob = BytesIO()
                            await attachment.save(attachment_blob)
                            attachments.append(
                                discord.File(attachment_blob, attachment.filename)
                            )
                # Why
                webhook = discord.utils.get(
                    (await self.bridge_registry(bridge_key)).webhooks,
                    channel__id=toChannel.id,
                )
                assert webhook is not None
                # TODO(nova) support multi-message sends :(
                await webhook.edit_message(
                    content=content[:2000],
                    embeds=[*fromMessage.embeds, *reply_embed],
                    files=attachments,
                    allowed_mentions=discord.AllowedMentions(
                        users=False, roles=False, everyone=False
                    ),
                    message_id=toMessage.id,
                    **({} if self.config.get() else {}),
                )
            if message.guild:
                for hotword in filter(
                    lambda hw: (type(hw) is Hotword)
                    and (
                        (
                            isinstance(hw.owner, discord.Member)
                            and discord.utils.get(
                                message.channel.members, id=hw.owner.id
                            )
                            and message.author.id != hw.owner.id
                        )
                        or (type(hw.owner) is str and hw.owner == "guild")
                    )
                    and (len(hw.user_restriction) == 0)
                    or (message.author.id in hw.user_restriction),
                    regex_cache.get(message.guild.id, []),
                ):
                    query_param = [message.id, message.channel.id]
                    if type(message.channel) is not discord.DMChannel:
                        query_param.append(message.guild.id)
                    cur = conn.cursor()
                    cur.execute(
                        f"SELECT author_id FROM attributions WHERE message = %s AND channel = %s AND guild {'= %s' if type(message.channel) is not discord.DMChannel else 'IS NULL'}",
                        query_param,
                    )
                    subtuple = cur.fetchone()
                    if (
                        subtuple
                        and not isinstance(hotword.owner, str)
                        and subtuple[0] == hotword.owner.id
                    ):
                        continue
                    if hotword.compiled_regex.search(message.content):
                        for command in hotword.target:
                            if hotword.owner.id in self.pinged_users[message.id]:
                                continue
                            else:
                                self.pinged_users[message.id].append(hotword.owner.id)
                            await command(
                                message, self.client, message.content.split(" ")
                            )
            channel_config = cast(
                dict, self.scope_config(channel=fromChannel, guild=fromGuild)
            )
            if channel_config.get("regex", None) and not (
                channel_config.get("regex-tyranny", False)
                and (
                    (
                        isinstance(fromMessage.author, discord.Member)
                        and message.channel.permissions_for(
                            fromMessage.author
                        ).manage_messages
                    )
                    or not isinstance(fromMessage.author, discord.Member)
                )
            ):
                continue_flag = await greeting.regex_filter(
                    message, self.client, channel_config
                )
                if not continue_flag:
                    return
            await self.tupper_proc(message)
        except discord.Forbidden as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"CEF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
            logger.debug(traceback.format_exc())

    async def matrix_command_handler(self, room: MatrixRoom, message: RoomMessageText):
        logger.debug(f"[MCH] {room} {message}")

    async def command_handler(self, message):
        received = datetime.utcnow()
        global config
        global sid

        user = message.author
        global Ans
        if (
            isinstance(message.channel, discord.DMChannel)
            and self.client.get_channel(message.channel.id) is None
        ):
            await user.create_dm()
        if (
            user.id == 382984420321263617
            and type(message.channel) is discord.DMChannel
            and message.content.startswith("!eval ")
        ):
            content = message.content[6:]
            try:
                if content.startswith("await"):
                    result = eval(content[6:])
                    result = await result
                else:
                    result = eval(content)
                if result:
                    await messagefuncs.sendWrappedMessage(str(result), user)
                    Ans = result
            except Exception as e:
                await messagefuncs.sendWrappedMessage(
                    f"{traceback.format_exc()}\nEVAL: {type(e).__name__} {e}", user
                )
        if (
            type(message.channel) is discord.DMChannel
            and message.channel.recipient is None
        ):
            message.channel = self.client.get_channel(message.channel.id)

        await self.bridge_message(message)
        if user == self.user:
            channel = message.channel
            assert message.channel is not None
            if type(channel) is discord.DMChannel and channel.recipient is None:
                channel = self.client.get_channel(channel.id)
            logger.info(
                f"{message.id} #{channel.guild.name if isinstance(channel, (discord.TextChannel, discord.Thread)) else 'DM'}:{channel.name if isinstance(channel, (discord.TextChannel, discord.Thread)) else (channel.recipient.name if channel.recipient else 'Unknown Recipient')} <{user.name}:{user.id}> {message.system_content}",
                extra={
                    "GUILD_IDENTIFIER": channel.guild.name
                    if isinstance(channel, (discord.TextChannel, discord.Thread))
                    else None,
                    "CHANNEL_IDENTIFIER": channel.name
                    if isinstance(channel, (discord.TextChannel, discord.Thread))
                    else (
                        channel.recipient.name
                        if channel.recipient is not None
                        else "Unknown Recipient"
                    ),
                    "SENDER_NAME": user.name,
                    "SENDER_ID": user.id,
                    "MESSAGE_ID": str(message.id),
                },
            )
            return

        guild_config = self.config.get(guild=message.guild, default={})
        channel_config = self.config.get(channel=message.channel, default={})

        try:
            blacklist_category = guild_config.get("automod-blacklist-category", [])
            blacklist_channel = guild_config.get("automod-blacklist-channel", [])
            if (
                isinstance(message.channel, (discord.TextChannel, discord.Thread))
                and message.channel.category_id not in blacklist_category
                and message.channel.id not in blacklist_channel
            ):
                sent_com_score = sid.polarity_scores(message.content)["compound"]
                if message.content == "VADER NEUTRAL":
                    sent_com_score = 0
                elif message.content == "VADER GOOD":
                    sent_com_score = 1
                elif message.content == "VADER BAD":
                    sent_com_score = -1
                logger.info(
                    f"{message.id} #{message.guild.name}:{message.channel.name} <{user.name}:{user.id}> [{sent_com_score}] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": message.guild.name,
                        "CHANNEL_IDENTIFIER": message.channel.name,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                        "SENT_COM_SCORE": sent_com_score,
                    },
                )
                if (
                    sent_com_score
                    <= float(guild_config.get("sent-com-score-threshold", -100000000))
                    and message.webhook_id is None
                    and message.guild.name
                    in config.get(section="moderation", key="guilds")
                ):
                    await janissary.modreport_function(
                        message,
                        self.client,
                        (
                            "\n[Sentiment Analysis Combined Score "
                            + str(sent_com_score)
                            + "] "
                            + message.system_content
                        ).split(" "),
                    )
            else:
                if isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                    logger.info(
                        f"{message.id} #{message.guild.name}:{message.channel.name} <{user.name}:{user.id}> [Nil] {message.system_content}",
                        extra={
                            "GUILD_IDENTIFIER": message.guild.name,
                            "CHANNEL_IDENTIFIER": message.channel.name,
                            "SENDER_NAME": user.name,
                            "SENDER_ID": user.id,
                            "MESSAGE_ID": str(message.id),
                        },
                    )
                elif type(message.channel) is discord.DMChannel:
                    if message.channel.recipient is None:
                        message.channel = await self.client.fetch_channel(
                            message.channel.id
                        )
                    logger.info(
                        f"{message.id} @{message.channel.recipient.name if message.channel.recipient else message.channel.id} <{user.name}:{user.id}> [Nil] {message.system_content}",
                        extra={
                            "GUILD_IDENTIFIER": "@",
                            "CHANNEL_IDENTIFIER": message.channel.recipient.name
                            if message.channel.recipient
                            else message.channel.id,
                            "SENDER_NAME": user.name,
                            "SENDER_ID": user.id,
                            "MESSAGE_ID": str(message.id),
                        },
                    )
                else:
                    # Group Channels don't support bots so neither will we
                    pass
        except AttributeError as e:
            if isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                logger.info(
                    f"{message.id} #{message.guild.name}:{message.channel.name} <{user.name}:{user.id}> [Nil] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": message.guild.name,
                        "CHANNEL_IDENTIFIER": message.channel.name,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                    },
                )
            elif type(message.channel) is discord.DMChannel:
                if message.channel.recipient is None:
                    message.channel = await self.client.fetch_channel(
                        message.channel.id
                    )
                    assert message.channel.recipient is not None
                logger.info(
                    f"{message.id} @{message.channel.recipient.name if message.channel.recipient else message.channel.id} <{user.name}:{user.id}> [Nil] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": "@",
                        "CHANNEL_IDENTIFIER": message.channel.recipient.name
                        if message.channel.recipient
                        else message.channel.id,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                    },
                )
            else:
                # Group Channels don't support bots so neither will we
                pass
            pass
        if (
            isinstance(message.channel, discord.Thread)
            and not message.channel.me
            and not message.channel.is_private()
            and message.channel.message_count < 4
        ):
            await self.thread_add(message.channel)
        if (
            message.author.id == 876482013287292948
            and message.channel.id == 1141826255214354462
        ):
            command = self.get_command(
                message.content, message, mode="keyword_trie", max_args=0
            )[0]
            await self.run_command(command, message, [], user, received_at=received)
            return
        if not message.webhook_id and message.author.bot:
            if message.author.id not in self.config.get(
                key="whitelist-bots", section="sync", default=[]
            ) and (
                message.guild
                and (
                    message.author.id
                    not in self.config.get(
                        key="whitelist-bots", guild=message.guild.id, default=[]
                    )
                )
            ):
                return
        if message.webhook_id:
            webhook = None
            try:
                webhook = await self.fetch_webhook_cached(message.webhook_id)
            except discord.errors.NotFound:
                return
            if webhook.name not in self.config.get(
                key="whitelist-webhooks", section="sync", default=[]
            ):
                return
        await self.tupper_proc(message)
        preview_link_found = messagefuncs.extract_identifiers_messagelink.search(
            message.content
        ) or messagefuncs.extract_previewable_link.search(message.content)
        blacklisted_preview_command = message.content.startswith(
            ("!preview", "!blockquote", "!xreact", "!tcaerx", "!react", "!flip")
        )
        should_preview_guild = type(message.channel) == discord.DMChannel or config.get(
            guild=None if not message.guild else message.guild.id,
            key="preview",
            default=False,
        )
        user_blacklisted = user.id in config.get(
            section="moderation", key="blacklist-user-usage"
        )
        if (
            preview_link_found
            and should_preview_guild
            and not (blacklisted_preview_command or user_blacklisted)
        ):
            await messagefuncs.preview_messagelink_function(message, self.client, None)
        if (
            "rot13" in message.content
            and guild_config.get("active-rot13", False)
            and not user_blacklisted
        ):
            await message.add_reaction(
                self.client.get_emoji(
                    int(config.get("discord", {}).get("rot13", "clock1130"))
                )
            )
        searchString = message.content
        if guild_config.get("prefix-replace", None):
            if searchString.startswith(guild_config["prefix-replace"]):
                searchString = searchString.replace(
                    guild_config["prefix-replace"], "!", 1
                )
            elif searchString.startswith("!"):
                searchString = searchString.replace("!", "", 1)
        if self.tag_id_as_command.search(searchString):
            searchString = self.tag_id_as_command.sub("!", searchString)
            if len(searchString) and searchString[-1] == "!":
                searchString = "!" + searchString[:-1]
        if self.config.get(section="interactivity", key="enhanced-command-finding"):
            if len(searchString) and searchString[-1] == "!":
                searchString = "!" + searchString[:-1]
            searchString = self.bang_remover.sub("!", searchString)
        searchString = searchString.rstrip()
        if len(message.stickers) > 0 and channel_config.get("kill-stickers", None):
            await message.delete()
        if channel_config.get("regex", None) == "pre-command" and not (
            channel_config.get("regex-tyranny", False)
            and message.channel.permissions_for(user).manage_messages
        ):
            continue_flag = await greeting.regex_filter(
                message, self.client, channel_config
            )
            if not continue_flag:
                return
        if message.reference and message.type is not discord.MessageType.pins_add:
            args = [message, user, "reply"]
            scoped_command = None
            if (
                self.message_reply_handlers.get(message.reference.message_id)
                and self.message_reply_handlers.get(
                    message.reference.message_id, {}
                ).get("scope", "message")
                != "channel"
            ):
                scoped_command = self.message_reply_handlers[
                    message.reference.message_id
                ]
            elif (
                self.message_reply_handlers.get(message.channel.id)
                and self.message_reply_handlers.get(message.channel.id, {}).get(
                    "scope", "message"
                )
                == "channel"
            ):
                scoped_command = self.message_reply_handlers[message.channel.id]
            refGuild = self.client.get_guild(message.reference.guild_id)
            refChannel = None
            if refGuild:
                refChannel = refGuild.get_channel(
                    message.reference.channel_id
                ) or refGuild.get_thread(message.reference.channel_id)
            if refChannel and message.reference.message_id:
                try:
                    refMessage = await refChannel.fetch_message(
                        message.reference.message_id
                    )
                    messageContent = refMessage.content
                    if scoped_command:
                        logger.debug(scoped_command)
                        if (
                            messageContent.startswith(tuple(scoped_command["trigger"]))
                            and self.allowCommand(scoped_command, message, user=user)
                            and not scoped_command.get("remove", False)
                            and scoped_command["args_num"] == 0
                        ):
                            await self.run_command(
                                scoped_command, refMessage, args, user
                            )
                    else:
                        for command in self.get_command(
                            messageContent, message, max_args=0
                        ):
                            if not command.get("remove", False):
                                await self.run_command(command, refMessage, args, user)
                except discord.Forbidden:
                    if not self.config.normalize_booleans(
                        self.user_config(
                            user.id,
                            message.guild.id,
                            key=f"readhistory_notified",
                            default="False",
                            allow_global_substitute=False,
                        )
                    ):
                        await messagefuncs.sendWrappedMessage(
                            f"Hi there! I noticed that I was unable to dereference a reply to a message due to missing Read History permissions on {message.guild} ({message.channel.mention}). You won't get another notification about this, but functionality may be impaired.",
                            message.guild.owner,
                        )
                        self.user_config(
                            user.id,
                            message.guild.id,
                            key=f"readhistory_notified",
                            value="True",
                            default="False",
                            allow_global_substitute=False,
                        )
                except Exception as e:
                    logger.warning(e)
                    _, _, exc_tb = exc_info()
                    assert exc_tb is not None
                    logger.error(
                        f"Dereference[{exc_tb.tb_lineno}]: {type(e).__name__} {e}"
                    )
        args = list(filter("".__ne__, searchString.split(" ")))
        if len(args):
            args.pop(0)
        command_ran = False
        for command in self.get_command(
            searchString, message, mode="keyword_trie", max_args=len(args)
        ):
            await self.run_command(command, message, args, user, received_at=received)
            command_ran = True
            # Run at most one command
            break
        if not command_ran:
            for command in self.get_command(searchString, message, mode="keyword_trie"):
                await messagefuncs.sendWrappedMessage(
                    "Wrong number of arguments for function",
                    message.channel,
                    delete_after=60,
                )
        if message.guild:
            for hotword in filter(
                lambda hw: (type(hw) is Hotword)
                and (
                    (
                        isinstance(hw.owner, discord.Member)
                        and message.channel.permissions_for(hw.owner).read_messages
                        and message.author.id != hw.owner.id
                        and not message.author.bot
                    )
                    or (type(hw.owner) is str and hw.owner == "guild")
                )
                and (len(hw.user_restriction) == 0)
                or (user.id in hw.user_restriction),
                regex_cache.get(message.guild.id, []),
            ):
                query_param = [message.id, message.channel.id]
                if type(message.channel) is not discord.DMChannel:
                    query_param.append(message.guild.id)
                cur = conn.cursor()
                cur.execute(
                    f"SELECT author_id FROM attributions WHERE message = %s AND channel = %s AND guild {'= %s' if type(message.channel) is not discord.DMChannel else 'IS NULL'}",
                    query_param,
                )
                subtuple = cur.fetchone()
                if (
                    subtuple
                    and not isinstance(hotword.owner, str)
                    and subtuple[0] == hotword.owner.id
                ):
                    continue
                if hotword.compiled_regex.search(message.content):
                    for command in hotword.target:
                        if hotword.owner.id in self.pinged_users[message.id]:
                            continue
                        else:
                            self.pinged_users[message.id].append(hotword.owner.id)
                        await command(message, self.client, args)
        if channel_config.get("regex", None) == "post-command" and not (
            channel_config.get("regex-tyranny", False)
            and message.channel.permissions_for(user).manage_messages
        ):
            continue_flag = await greeting.regex_filter(
                message, self.client, channel_config
            )
            if not continue_flag:
                return

    async def run_command(
        self,
        command: dict,
        message: discord.Message,
        args: list,
        user,
        ctx=None,
        ignore_stranger_danger=False,
        received_at: Optional[datetime] = None,
    ):
        if (message.content or "").startswith("!ping"):
            args.append(received_at)
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            with hub.configure_scope() as scope, hub.start_transaction(op="run_command", name=str(user)):  # type: ignore
                scope.user = {"id": user.id, "username": str(user)}
                guild = None
                if ctx and ctx.guild_id:
                    guild = self.client.get_guild(ctx.guild_id)
                if message and message.guild:
                    guild = message.guild
                if guild:
                    scope.set_tag("guild", guild.name)
                stranger_role = -1
                if guild and self.config.get(
                    "stranger_role", default=None, guild=guild.id
                ):
                    stranger_role = str(
                        self.config.get("stranger_role", default=None, guild=guild.id)
                    )
                    if stranger_role.isnumeric():
                        stranger_role = int(stranger_role)
                    else:
                        stranger_role = discord.utils.get(
                            guild.roles, name=stranger_role
                        )
                        if isinstance(stranger_role, discord.Role):
                            stranger_role = stranger_role.id
                        else:
                            stranger_role = -1
                if (
                    user
                    and isinstance(user, discord.Member)
                    and user.get_role(stranger_role)
                ):
                    if ignore_stranger_danger:
                        logger.debug(
                            f"[CH] Would ignore request, but trusting in the kindness of strangers"
                        )
                    else:
                        logger.debug(
                            f"[CH] Ignored {command} request, user is stranger danger"
                        )
                        return
                if hasattr(command, "function"):
                    if command.long_run == "author":
                        await user.trigger_typing()
                    elif command.long_run:
                        await message.channel.trigger_typing()
                    logger.debug(f"[CH] Triggered {command}")
                    if user.id in cast(
                        Iterable,
                        self.config.get(
                            section="moderation", key="blacklist-user-usage"
                        ),
                    ):
                        raise Exception(f"Blacklisted command attempt by user {user}")
                    function = command.function
                    logger.debug(function)
                    if command.sync:
                        await messagefuncs.sendWrappedMessage(
                            str(function(message, self.client, args)),
                            message.channel,
                        )
                    else:
                        await function(message, self.client, args)
                else:
                    if command.get("long_run") == "author":
                        await user.trigger_typing()
                    elif command.get("long_run") and message and message.channel:
                        await message.channel.trigger_typing()
                    logger.debug(f"[CH] Triggered {command}")
                    if user.id in cast(
                        Iterable,
                        self.config.get(
                            section="moderation", key="blacklist-user-usage"
                        ),
                    ):
                        raise Exception(f"Blacklisted command attempt by user {user}")
                    if command["async"]:
                        if command.get(
                            "slash_command",
                            command.get(
                                "message_command", command.get("component", False)
                            ),
                        ):
                            await command["function"](message, self.client, args, ctx)
                        else:
                            await command["function"](message, self.client, args)
                    else:
                        await messagefuncs.sendWrappedMessage(
                            str(command["function"](message, self.client, args)),
                            message.channel,
                        )

    def whitelist_command(self, command_name, guild_id):
        commands = self.get_command("!" + command_name)
        if not commands:
            commands = self.get_command(command_name)
        if len(commands):
            for command in commands:
                if command.get("blacklist_guild") and guild_id in command.get(
                    "blacklist_guild"
                ):
                    command["blacklist_guild"].remove(guild_id)
                    logger.debug(
                        f"Whitelist overwrites blacklist for {command} on guild {guild_id}"
                    )
        else:
            logger.error(
                f"Couldn't find {command_name} for whitelisting on guild {guild_id}"
            )

    def whitelist_limit_command(self, command_name, guild_id):
        commands = self.get_command("!" + command_name)
        if not commands:
            commands = self.get_command(command_name)
        if len(commands):
            for command in commands:
                if not command.get("whitelist_guild"):
                    command["whitelist_guild"] = []
                command["whitelist_guild"].append(guild_id)
                logger.debug(f"Whitelisting {command} on guild {guild_id}")
        else:
            logger.error(
                f"Couldn't find {command_name} for whitelisting on guild {guild_id}"
            )

    def blacklist_command(self, command_name, guild_id, channel_id=None):
        if command_name == "all":
            commands = self.commands
        else:
            commands = self.get_command("!" + command_name)
            if not len(commands):
                commands = self.get_command(command_name)
        if len(commands):
            for command in commands:
                if channel_id:
                    if not command.get("blacklist_channel"):
                        command["blacklist_channel"] = []
                    command["blacklist_channel"].append(channel_id)
                    if self.config.get(section="debug", key="blacklist", default=False):
                        logger.debug(f"Blacklisting {command} on channel {channel_id}")
                else:
                    if not command.get("blacklist_guild"):
                        command["blacklist_guild"] = []
                    command["blacklist_guild"].append(guild_id)
                    if self.config.get(section="debug", key="blacklist", default=False):
                        logger.debug(f"Blacklisting {command} on guild {guild_id}")
        else:
            logger.error(
                f"Couldn't find {command_name} for blacklisting on guild {guild_id}"
            )

    def scope_config(self, message=None, channel=None, guild=None, mutable=False):
        if guild is None:
            if channel and type(channel) != discord.DMChannel:
                guild = channel.guild
            elif message and type(channel) != discord.DMChannel:
                guild = message.guild
            else:
                return self.config
        if channel is None:
            if message:
                channel = message.channel
        if guild and type(guild) is not int:
            guild = guild.id
        if channel and type(channel) is not int:
            channel = channel.id
        try:
            if mutable:
                return self.config.get(guild=guild, channel=channel)
            else:
                return dict(self.config.get(guild=guild, channel=channel))
        except TypeError:
            return {}

    # @lru_cache(maxsize=256)
    def user_config(
        self, user, guild, key, value=None, default=None, allow_global_substitute=False
    ):
        try:
            if isinstance(guild, discord.Guild):
                guild = guild.id
            cur = conn.cursor()
            if value == "null":
                value = ""
            if value is None:
                if guild:
                    if allow_global_substitute:
                        cur.execute(
                            "SELECT value FROM user_preferences WHERE user_id = %s AND (guild_id = %s OR guild_id IS NULL) AND key = %s ORDER BY guild_id LIMIT 1;",
                            [user, guild, key],
                        )
                    else:
                        cur.execute(
                            "SELECT value FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = %s LIMIT 1;",
                            [user, guild, key],
                        )
                else:
                    cur.execute(
                        "SELECT value FROM user_preferences WHERE user_id = %s AND guild_id IS NULL AND key = %s LIMIT 1;",
                        [user, key],
                    )
                value = cur.fetchone()
                if value:
                    value = value[0]
            else:
                if key == "hotwords":
                    try:
                        ujson.loads(value)
                    except:
                        return 'Value for `hotwords` must be valid JSON. Example: ``````json\n{"dm-on-name":{"dm_me": 1, "regex": "myname", "insensitive": "true"}}\n'
                if guild:
                    cur.execute(
                        "SELECT value FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = %s LIMIT 1;",
                        [user, guild, key],
                    )
                else:
                    cur.execute(
                        "SELECT value FROM user_preferences WHERE user_id = %s AND guild_id IS NULL AND key = %s LIMIT 1;",
                        [user, key],
                    )
                old_value = cur.fetchone()
                if old_value:
                    if guild:
                        cur.execute(
                            "UPDATE user_preferences SET value = %s WHERE user_id = %s AND guild_id = %s AND key = %s;",
                            [value, user, guild, key],
                        )
                    else:
                        cur.execute(
                            "UPDATE user_preferences SET value = %s WHERE user_id = %s AND guild_id IS NULL AND key = %s;",
                            [value, user, key],
                        )
                else:
                    try:
                        cur.execute(
                            "INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, %s, %s) ON CONFLICT ON CONSTRAINT user_preferences_u_constraint DO UPDATE SET value = EXCLUDED.value;",
                            [user, guild, key, value],
                        )
                    except:
                        conn.rollback()

                        if guild:
                            cur.execute(
                                "UPDATE user_preferences SET value = %s WHERE user_id = %s AND guild_id = %s AND key = %s;",
                                [value, user, guild, key],
                            )
                        else:
                            cur.execute(
                                "UPDATE user_preferences SET value = %s WHERE user_id = %s AND guild_id IS NULL AND key = %s;",
                                [value, user, key],
                            )
                if key.startswith("twunsubscribe"):
                    import schedule

                    schedule.last_ran_fetch = None
            conn.commit()
            if value is None:
                value = default
            return value
        except UniqueViolation:
            conn.rollback()
            return "Invalid duplicate key"

    def is_admin(self, message, user=None):
        global config
        if hasattr(message, "channel"):
            channel = message.channel
        else:
            channel = message
        if user is None:
            try:
                user = channel.guild.get_member(message.author.id) or message.author
            except AttributeError:
                user = message.author
        if type(user) is discord.Member and user.guild.id != channel.guild.id:
            member = channel.guild.get_member(user)
            if member is None:
                user = client.get_user(user.id)
            else:
                user = member
        globalAdmin = user.id == config["discord"].get("globalAdmin", 0)
        serverAdmin = (
            globalAdmin and config["discord"].get("globalAdminIsServerAdmin", False)
        ) or (type(user) is discord.Member and user.guild_permissions.manage_webhooks)
        channelAdmin = (
            (globalAdmin and config["discord"].get("globalAdminIsServerAdmin", False))
            or serverAdmin
            or (
                type(user) is discord.Member
                and channel.permissions_for(user).manage_webhooks
            )
        )
        return {"global": globalAdmin, "server": serverAdmin, "channel": channelAdmin}

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if (
            before.channel is None
            and after.channel is not None
            and len(after.channel.members) == 1
        ):
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM user_preferences WHERE key = %s;",
                [f"notifyme-{after.channel.id}"],
            )
            while metuple := cur.fetchone():
                try:
                    await messagefuncs.sendWrappedMessage(
                        f"{member.display_name} is live in {after.channel.name}",
                        after.channel.guild.get_member(metuple[0]),
                    )
                except:
                    pass
            conn.commit()

    async def on_interaction(self, ctx: discord.Interaction):
        if self.config.get(section="debug", key="interaction", default=False):
            logger.debug(f"{ctx.data=}")
        if ctx.application_id != self.user.id:
            return
        if ctx.data.get("target_id"):
            message = await ctx.channel.fetch_message(ctx.data["target_id"])
        elif ctx.message:
            message = ctx.message
        else:
            message = ctx.channel.last_message
        if ctx.is_component():
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT function, state FROM message_interaction_functions WHERE message_id = %s AND user_id = %s LIMIT 1;",
                    [message.id, ctx.user.id],
                )
                metuple = cur.fetchone()
                conn.commit()
                if metuple:
                    if self.config.get(
                        section="debug", key="interaction", default=False
                    ):
                        logger.debug(f"{metuple=}")
                    command = next(
                        filter(
                            lambda c: metuple[0] in c.get("trigger", [])
                            and c.get("component"),
                            self.commands,
                        ),
                        None,
                    )
                    if command:
                        return await self.run_command(
                            command,
                            message,
                            [metuple[1]],
                            ctx.user,
                            ctx,
                        )
            except Exception as e:
                conn.rollback()
                logger.error(e)

        if not ctx.is_command():
            logger.debug(f"Discarding non-command interaction from {ctx.user}")
            return
        logger.debug(f"Interaction {ctx.data['id']} in {ctx.guild_id}")
        for command in filter(
            lambda command: command.get(
                "slash_command", command.get("message_command", False)
            ),
            self.commands,
        ):
            if (
                command.get("guild_command_ids", {}).get(ctx.data["id"], 0)
                == ctx.guild_id
            ):
                return await self.run_command(
                    command,
                    message,
                    [
                        o.get("value")
                        for o in ctx.data.get("options", [])
                        if o.get("value")
                    ],
                    ctx.user,
                    ctx,
                )
        await ctx.response.send_message(
            "Not Implemented (or couldn't find command)", ephemeral=True
        )

    async def bridge_registry(self, key: str):
        global webhooks_loaded
        synchronize = self.config.get(
            "synchronize",
            guild=discord.utils.get(self.client.guilds, name=key.split(":")[0]),
            default=False,
        )
        while 1:
            if webhooks_loaded:
                return self.webhook_sync_registry.get(key)
            if not synchronize:
                return self.webhook_sync_registry.get(key)
            if isinstance((bridge := self.webhook_sync_registry.get(key)), Bridge):
                return bridge

            await asyncio.sleep(1)
            logger.info(
                f"Awaiting {key} ready, {webhooks_loaded=}, {not synchronize=}, {self.webhook_sync_registry.get(key)=}, {type(self.webhook_sync_registry.get(key))=}"
            )

    def allowCommand(self, command, message, user=None):
        global config
        if not user:
            user = message.author
        admin = self.is_admin(message, user=user)
        if hasattr(command, "admin"):
            command_admin = command.admin
        else:
            command_admin = command.get("admin", False)
        if command_admin == "global" and admin["global"]:
            return True
        # Guild admin commands
        if isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            # Server-specific
            if (
                str(command_admin).startswith("server:")
                and message.guild.id in str_to_arr(command_admin.split(":")[1])
                and admin["server"]
            ):
                return True
            # Channel-specific
            elif (
                str(command_admin).startswith("channel:")
                and message.channel.id in str_to_arr(command_admin.split(":")[1])
                and admin["channel"]
            ):
                return True
            # Any server
            elif command_admin in ["server", True] and admin["server"]:
                return True
            # Any channel
            elif command_admin == "channel" and admin["channel"]:
                return True
        # Unprivileged
        if command_admin == False:
            return True
        else:
            # Invalid config
            return False

    async def thread_add(self, thread):
        if thread.message_count > 4:
            logger.debug("Not adding myself to a thread with a message_count > 4")
            return
        if not thread.me:
            logger.debug(f"Adding myself to new thread {thread.name} ({thread.id})")
            await thread.add_user(thread.guild.get_member(self.user.id))
        if thread.is_private():
            logger.debug("Private thread, you know what you're doing.")
            return
        if thread.guild:
            if thread.category_id not in self.config.get(
                key="automod-blacklist-category", guild=thread.guild.id
            ):
                for user in list(
                    filter(
                        lambda user: user in thread.parent.members,
                        await load_config.expand_target_list(
                            self.config.get(
                                key="manual-mod-userslist",
                                default=[thread.guild.owner.id]
                                if thread.guild.owner
                                else [],
                                guild=thread.guild.id,
                            ),
                            thread.guild,
                        ),
                    )
                ):
                    if self.config.normalize_booleans(
                        self.user_config(
                            user.id,
                            thread.guild.id,
                            key="use_threads",
                            default="True",
                            allow_global_substitute=True,
                        )
                    ):
                        logger.debug(
                            f"Adding mod {user} to thread {thread.name} ({thread.id})"
                        )
                        await thread.add_user(user)
            for user in thread.parent.members:
                use_threads = self.config.normalize(
                    str(
                        self.user_config(
                            user.id,
                            thread.guild.id,
                            key="use_threads",
                            default="false",
                            allow_global_substitute=True,
                        )
                    )
                )
                if (isinstance(use_threads, bool) and use_threads) or (
                    isinstance(use_threads, str)
                    and thread.id
                    in tuple(
                        self.config.normalize(self.config.normalize_array(use_threads))
                    )
                ):
                    logger.debug(f"Adding {user} to thread {thread.name} ({thread.id})")
                    await thread.add_user(user)
            global conn
            bridge_key = f"{thread.guild.name}:{thread.parent_id}"
            if thread.guild and self.config.get(guild=thread.guild, key="synchronize"):
                bridge = await self.bridge_registry(bridge_key)
            else:
                bridge = None
            if bridge:
                new_threads = []
                await asyncio.sleep(1)
                for bridge_channel in bridge["toChannelObject"]:
                    query_params = [
                        thread.guild.id,
                        thread.parent_id,
                        thread.id,
                        bridge_channel.guild.id,
                    ]
                    metuple = None
                    if metuple is None:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s AND toguild = %s LIMIT 1;",
                            query_params,
                        )
                        metuple = cur.fetchone()
                        conn.commit()
                    if metuple is None:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT fromguild, fromchannel, frommessage FROM messagemap WHERE toguild = %s AND tochannel = %s AND tomessage = %s LIMIT 1;",
                            query_params[:3],
                        )
                        metuple = cur.fetchone()
                        conn.commit()
                        if metuple[0] != bridge_channel.guild.id:
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s AND toguild = %s LIMIT 1;",
                                [*metuple, bridge_channel.guild.id],
                            )
                            metuple = cur.fetchone()
                            conn.commit()
                    if metuple[1] != thread.parent_id and metuple:
                        new_threads.append(
                            await (
                                await self.client.get_channel(metuple[1]).fetch_message(
                                    int(metuple[2])
                                )
                            ).create_thread(name=thread.name)
                        )
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO threads (source, target) VALUES (%s, %s);",
                        [thread.id, [thread.id for thread in new_threads]],
                    )
                    conn.commit()
                except Exception as e:
                    if "cur" in locals() and "conn" in locals():
                        conn.rollback()

    async def guild_add(self, guild):
        await guild.chunk()
        await (
            guild.public_updates_channel or guild.system_channel or guild.owner
        ).send(
            f"Thank you for adding me to {guild.name}! If you added me for bridges, please note that you must set the `synchronize` option to `On` at https://fletcher.fun to use this feature. Also, if you added me for reaction-triggered commands, you must set the `active-emoji` option to `On`. If you have issues, please join the support server at {self.config.get(section='discord', key='support_invite')} for help."
        )

    def get_member_named(self, guild, name, allow_insensitive=True):
        result = None
        members = guild.members
        if len(name) > 5 and name[-5] == "#":
            # The 5 length is checking to see if #0000 is in the string,
            # as a#0000 has a length of 6, the minimum for a potential
            # discriminator lookup.
            potential_discriminator = name[-4:]

            # do the actual lookup and return if found
            # if it isn't found then we'll do a full name lookup below.
            result = discord.utils.get(
                members, name=name[:-5], discriminator=potential_discriminator
            )
            if result is not None:
                return result

        result = discord.utils.find(lambda m: m.name == name, members)
        if result is not None:
            return result

        result = discord.utils.find(lambda m: m.nick == name, members)
        if result is not None:
            return result

        if not allow_insensitive:
            return None

        name = name.lower()
        result = discord.utils.find(lambda m: name == m.name.lower(), members)
        if result is not None:
            return result

        result = discord.utils.find(lambda m: name == m.nick.lower(), members)
        if result is not None:
            return result

    def accessible_commands(self, message, user=None):
        global config
        if message.author.id in config.get(
            section="moderation", key="blacklist-user-usage"
        ):
            return []
        admin = self.is_admin(message, user=user)
        if message.guild:
            guild_id = message.guild.id
        else:
            guild_id = -1
        channel_id = message.channel.id

        stranger_role = -1
        if (
            user
            and message.guild
            and config.get("stranger_role", default=None, guild=guild_id)
        ):
            stranger_role = str(
                config.get("stranger_role", default=None, guild=guild_id)
            )
            if stranger_role.isnumeric():
                stranger_role = int(stranger_role)
            else:
                stranger_role = discord.utils.get(
                    message.guild.roles, name=stranger_role
                )
                if isinstance(stranger_role, discord.Role):
                    stranger_role = stranger_role.id
                else:
                    stranger_role = -1
        if user and isinstance(user, discord.Member) and user.get_role(stranger_role):
            return []
        admin[""] = True
        admin[None] = True
        admin[False] = True
        if admin["global"]:

            def command_filter(c):
                return (
                    admin[c.get("admin")]
                    and (guild_id in c.get("whitelist_guild", [guild_id]))
                    and (
                        (guild_id not in c.get("blacklist_guild", []))
                        and (channel_id not in c.get("blacklist_channel", []))
                        or config.get(
                            section="discord",
                            key="globalAdminIgnoresBlacklists",
                            default=False,
                        )
                    )
                )

        elif admin["server"]:

            def command_filter(c):
                return (
                    admin[c.get("admin")]
                    and (guild_id in c.get("whitelist_guild", [guild_id]))
                    and (
                        (guild_id not in c.get("blacklist_guild", []))
                        and (channel_id not in c.get("blacklist_channel", []))
                        or config.get(
                            section="discord",
                            key="serverAdminIgnoresBlacklists",
                            default=False,
                        )
                    )
                )

        elif admin["channel"]:

            def command_filter(c):
                return (
                    admin[c.get("admin")]
                    and (guild_id in c.get("whitelist_guild", [guild_id]))
                    and (
                        (guild_id not in c.get("blacklist_guild", []))
                        and (channel_id not in c.get("blacklist_channel", []))
                        or config.get(
                            section="discord",
                            key="channelAdminIgnoresBlacklists",
                            default=False,
                        )
                    )
                )

        else:

            def command_filter(c):
                return (
                    admin[c.get("admin")]
                    and (guild_id in c.get("whitelist_guild", [guild_id]))
                    and (guild_id not in c.get("blacklist_guild", []))
                    and (channel_id not in c.get("blacklist_channel", []))
                )

        try:
            return list(filter(command_filter, self.commands))
        except IndexError:
            return []

    def get_command(
        ch,
        target_trigger,
        message=None,
        mode="exact",
        insensitive=True,
        min_args=0,
        max_args=99999,
        user=None,
    ):
        if insensitive and target_trigger:
            target_trigger = target_trigger.lower()
        if message:
            accessible_commands = ch.accessible_commands(message, user=user)
        else:
            accessible_commands = ch.commands
        accessible_commands = [
            c for c in accessible_commands if not c.get("slash_command", False)
        ]
        if mode == "keyword":

            def query_filter(c):
                return (
                    any(target_trigger in trigger for trigger in c["trigger"])
                    and min_args <= c.get("args_min", c.get("args_num", 0)) <= max_args
                )

        if mode == "keyword_trie":

            def query_filter(c):
                return (
                    target_trigger.startswith(c["trigger"])
                    and min_args <= c.get("args_min", c.get("args_num", 0)) <= max_args
                )

        elif mode == "description":

            def query_filter(c):
                return (
                    any(target_trigger in trigger for trigger in c["trigger"])
                    or target_trigger in c.get("description", "").lower()
                    and min_args <= c.get("args_min", c.get("args_num", 0)) <= max_args
                )

        else:  # if mode == "exact":

            def query_filter(c):
                return (
                    target_trigger in c["trigger"]
                    and min_args <= c.get("args_min", c.get("args_num", 0)) <= max_args
                )

        try:
            return list(filter(query_filter, accessible_commands))
        except IndexError:
            return []

    def load_hotwords(self, force_reload=False):
        global regex_cache
        global config
        ch = self
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, guild_id, value FROM user_preferences WHERE key = 'hotwords';"
            )
            hottuple = cur.fetchone()
            while hottuple:
                [user_id, guild_id, hotword_json] = hottuple
                if guild_id == 0 or guild_id is None:
                    if not ch.client.get_user(user_id):
                        hottuple = cur.fetchone()
                        continue
                    guilds = ch.client.get_user(user_id).mutual_guilds
                    try:
                        ujson.loads(hotword_json)
                    except ValueError:
                        ch.client.loop.create_task(
                            messagefuncs.sendWrappedMessage(
                                f"Error loading your global hotwords: ``json\n{hotword_json}``` is invalid JSON. Please either disable or fix this hotword.",
                                ch.client.get_user(user_id),
                            )
                        )
                        hottuple = cur.fetchone()
                        continue
                else:
                    guilds = [ch.client.get_guild(guild_id)]
                for guild in guilds:
                    if guild is None:
                        continue
                    logger.debug(f"Loading {user_id} on {guild.id}: {hotword_json}")
                    guild_config = ch.scope_config(guild=guild.id, mutable=True)
                    try:
                        hotwords = ujson.loads(hotword_json)
                    except ValueError as e:
                        exc_type, exc_obj, exc_tb = exc_info()
                        logger.info(f"LUHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                        if guild_id == 0 or guild_id is None:
                            ch.client.loop.create_task(
                                messagefuncs.sendWrappedMessage(
                                    f"Error loading your hotwords for {guild.name}: ``json\n{hotword_json}``` is invalid JSON. Please either disable or fix this hotword.",
                                    ch.client.get_user(user_id),
                                )
                            )
                        continue
                    if not guild_config.get("hotwords_loaded") or force_reload:
                        guild_config["hotwords_loaded"] = ""
                    for word in hotwords.keys():
                        try:
                            hotword = Hotword(
                                ch,
                                word,
                                hotwords[word],
                                guild.get_member(user_id),
                            )
                        except (ValueError, KeyError) as e:
                            logger.error(f"Parsing {word} for {user_id} failed: {e}")
                            continue
                        except re.error as e:
                            ch.client.loop.create_task(
                                messagefuncs.sendWrappedMessage(
                                    f"Error loading your hotwords for {guild.name}: ``json\n{hotword_json}``` contains an invalid regular expression (error during re.compile ({e}). Please either disable or fix this hotword.",
                                    ch.client.get_user(user_id),
                                )
                            )
                            continue
                        except AttributeError as e:
                            logger.debug(traceback.format_exc())
                            logger.info(
                                f"Parsing {word} for {user_id} failed: User is not on server {e}"
                            )
                            continue
                        hotwords[word] = hotword
                        guild_config["hotwords_loaded"] += ", " + word
                        if not regex_cache.get(guild.id):
                            regex_cache[guild.id] = []
                    add_me = list(
                        filter(lambda hw: type(hw) == Hotword, hotwords.values())
                    )
                    if not regex_cache.get(guild.id) or force_reload:
                        regex_cache[guild.id] = []
                    logger.debug(f"Extending regex_cache[{guild.id}] with {add_me}")
                    regex_cache[guild.id].extend(add_me)
                hottuple = cur.fetchone()
            conn.commit()
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"LUHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


ch = cast(CommandHandler, None)


async def help_function(message, client, args):
    global ch
    try:
        arg = None
        verbose = False
        public = False
        while len(args) > 0:
            arg = args[0]
            arg = arg.strip().lower()
            if arg == "verbose":
                verbose = True
                arg = None
                args = args[1:]
            elif arg == "public":
                public = True
                arg = None
                args = args[1:]
            else:
                arg = args[0]
                break

        if message.content.startswith("!man"):
            public = True

        if ch.is_admin(message)["server"] and public:
            target = message.channel
        else:
            target = message.author

        if len(args) == 0:
            arg = None

        if arg:
            keyword = " ".join(args).strip().lower()
            if keyword.startswith("!"):
                accessible_commands = ch.get_command(keyword, message, mode="keyword")
            else:
                accessible_commands = ch.get_command(
                    keyword, message, mode="description"
                )

            # Set verbose if filtered list
            if len(accessible_commands) < 5:
                verbose = True
                public = True
        else:
            try:
                accessible_commands = ch.accessible_commands(message)
            except IndexError:
                accessible_commands = []
        if not verbose:
            try:
                accessible_commands = list(
                    filter(lambda c: not c.get("hidden", False), accessible_commands)
                )
            except IndexError:
                accessible_commands = []
        delete_after = None
        if target == message.author and len(accessible_commands):
            await message.add_reaction("✅")
        if len(args) > 0 and len(accessible_commands) and verbose:
            helpMessageBody = "\n".join(
                [
                    f'__{command["module"]}__ `{"` or `".join(command["trigger"])}`: {command["description"]}\nMinimum Arguments ({command["args_num"]}): {" ".join(command["args_name"])}'
                    for command in accessible_commands
                ]
            )
        elif len(accessible_commands) == 0:
            helpMessageBody = "No commands accessible, check your input"
            delete_after = 30
        else:
            helpMessageBody = ("\n" if len(accessible_commands) < 20 else "; ").join(
                [
                    f'__{command["module"]}__ `{" or ".join(command["trigger"][:2])}`: {command["description"]}'
                    if len(accessible_commands) < 20
                    else f'{" or ".join(command["trigger"][:2])}'
                    for command in accessible_commands
                ]
            )
        try:
            if len(helpMessageBody) > 6000:
                await messagefuncs.sendWrappedMessage(
                    "Response to that help query was too long, please try a more specific query or https://fletcher.fun/man",
                    target,
                    wrap_as_embed=False,
                    delete_after=delete_after,
                )
            else:
                await messagefuncs.sendWrappedMessage(
                    helpMessageBody,
                    target,
                    wrap_as_embed=False,
                    delete_after=delete_after,
                )
        except discord.Forbidden:
            if type(target) is discord.Member:
                await messagefuncs.sendWrappedMessage(
                    "Unable to DM you a list of commands - please allow DMs from me to use this command.",
                    message.channel,
                    delete_after=60,
                )
                await message.add_reaction("🚫")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug(traceback.format_exc())
        logger.error(f"HF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


def dumpconfig_function(message, client, args):
    global config
    assert isinstance(config, load_config.FletcherConfig)
    if message.guild:
        dconfig = ch.scope_config(guild=message.guild)
    else:
        dconfig = config
    if len(args) == 1:
        return (
            "```json\n"
            + ujson.dumps(dconfig.get(" ".join(args)), ensure_ascii=False, indent=4)
            + "```"
        )
    else:
        return "```json\n" + ujson.dumps(config, ensure_ascii=False, indent=4) + "```"


async def add_emoji(message, client, args, intended_target_emoji):
    await message.add_reaction(intended_target_emoji)


class Hotword:
    def __init__(self, ch, word, hotword, owner):
        self.owner = owner
        if hotword.get("target_emoji"):
            if (
                len(hotword["target_emoji"]) > 2
                and hotword["target_emoji"] not in UNICODE_EMOJI
            ):
                intended_target_emoji = None
                if type(owner) == discord.Member:
                    intended_target_emoji = discord.utils.get(
                        owner.guild.emojis, name=hotword["target_emoji"]
                    )
                if not intended_target_emoji:
                    intended_target_emoji = discord.utils.get(
                        ch.client.emojis, name=hotword["target_emoji"]
                    )
                if intended_target_emoji:

                    self.target = [
                        partial(add_emoji, intended_target_emoji=intended_target_emoji)
                    ]
                else:
                    raise ValueError("Target emoji not found")
            else:

                self.target = [
                    partial(add_emoji, intended_target_emoji=hotword["target_emoji"])
                ]
        elif hotword.get("dm_me") or hotword.get("dm-me"):

            async def dm_me(owner, message, client, args):
                try:
                    # created_at is naîve, but specified as UTC by Discord API docs
                    sent_at = f"<t:{int(message.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.utc).timestamp())}:R>"
                    content = message.content
                    if message.author.bot and len(message.embeds):
                        embed = message.embeds[0]
                    if content == "":
                        # content = "*No Text*"
                        pass
                    else:
                        content = ">>> " + content
                    content = "@__{}__ in **#{}** ({}) at {}:\n{}".format(
                        message.author.name,
                        message.channel.name,
                        message.guild.name,
                        sent_at,
                        content,
                    )
                    content = messagefuncs.extract_links.sub(r"<\g<0>>", content)
                    if len(message.attachments) > 0:
                        plural = ""
                        if len(message.attachments) > 1:
                            plural = "s"
                        if message.channel.is_nsfw() and (
                            type(message.channel) is discord.DMChannel
                            or not message.channel.is_nsfw()
                        ):
                            content = (
                                content
                                + "\n "
                                + str(len(message.attachments))
                                + " file"
                                + plural
                                + " attached"
                            )
                            content = content + " from an r18 channel."
                            for attachment in message.attachments:
                                content = content + "\n• <" + attachment.url + ">"
                        else:
                            content = (
                                content
                                + "\n "
                                + str(len(message.attachments))
                                + " file"
                                + plural
                                + " attached"
                            )
                            content = content + " from an r18 channel."
                            for attachment in message.attachments:
                                content = content + "\n• " + attachment.url

                    response_message = await messagefuncs.sendWrappedMessage(
                        f"Hotword {word} triggered by <https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}>\n{content}",
                        client.get_user(owner.id),
                        current_user_id=owner.id,
                    )
                    await messagefuncs.preview_messagelink_function(
                        response_message, client, None
                    )
                except AttributeError:
                    logger.debug(
                        f"Couldn't send message because owner couln't be dereferenced for {word} in {message.guild}"
                    )

            self.target = [partial(dm_me, self.owner)]
        elif owner == "guild" and hotword.get("target_function"):
            self.target = [partial(ch.get_command, target_function_name)]
        else:
            raise ValueError("No valid target")
        flags = 0
        if hotword.get("insensitive"):
            flags = re.IGNORECASE
        self.user_restriction = hotword.get("user_restriction", [])
        if type(owner) is not str and hotword.get("target_emoji"):
            self.user_restriction.append(owner.id)
        self.regex = hotword["regex"]
        self.compiled_regex = re.compile(hotword["regex"], flags)

    def __iter__(self):
        return {
            "regex": self.regex,
            "compiled_regex": self.compiled_regex,
            "owner": self.owner,
            "user_restriction": self.user_restriction,
            "target": self.target,
        }


def load_guild_config(ch):
    def load_hotwords(ch):
        global regex_cache
        try:
            for guild in ch.client.guilds:
                guild_config = ch.scope_config(guild=guild, mutable=True)
                if guild_config and guild_config.get("hotwords", "").startswith("{"):
                    try:
                        hotwords = ujson.loads(guild_config.get("hotwords", "{}"))
                    except ValueError as e:
                        logger.error(e)
                        continue
                    if not guild_config.get("hotwords_loaded"):
                        guild_config["hotwords_loaded"] = ""
                    for word in hotwords.keys():
                        try:
                            hotword = Hotword(ch, word, hotwords[word], "guild")
                        except ValueError as e:
                            logger.error(f"Parsing {word} failed: {e}")
                            continue
                        hotwords[word] = hotword
                        guild_config["hotwords_loaded"] += ", " + word
                    guild_config["hotwords_loaded"] = guild_config[
                        "hotwords_loaded"
                    ].lstrip(", ")
                    if not regex_cache.get(guild.id):
                        regex_cache[guild.id] = []
                    logger.debug(
                        f"Extending regex_cache[{guild.id}] with {hotwords.values()}"
                    )
                    regex_cache[guild.id].extend(hotwords.values())
        except NameError:
            pass
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"LGHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    def load_blacklists(ch):
        for guild in ch.client.guilds:
            guild_config = ch.scope_config(guild=guild)
            for command_name in guild_config.get("blacklist-commands", []):
                ch.blacklist_command(command_name, guild.id)
            for channel in guild.text_channels:
                channel_config = ch.scope_config(guild=guild, channel=channel)
                for command_name in channel_config.get("blacklist-commands", []):
                    ch.blacklist_command(command_name, guild.id, channel.id)
        for guild in ch.client.guilds:
            guild_config = ch.scope_config(guild=guild)
            for command_name in guild_config.get("whitelist-commands", []):
                ch.whitelist_command(command_name, guild.id)
        for guild in ch.client.guilds:
            guild_config = ch.scope_config(guild=guild)
            for command_name in guild_config.get("optinlist-commands", []):
                ch.whitelist_limit_command(command_name, guild.id)

    logger.debug("LBL")
    load_blacklists(ch)
    logger.debug("LGHW")
    load_hotwords(ch)


"""
fletcher=# \d user_preferences
          Table "public.user_preferences"
  Column  |  Type  | Collation | Nullable | Default
----------+--------+-----------+----------+---------
 user_id  | bigint |           | not null |
 guild_id | bigint |           | not null |
 key      | text   |           | not null |
 value    | text   |           |          |
Indexes:
    "user_prefs_idx" btree (user_id, guild_id, key)
"""


def load_user_config(ch):
    def load_tuppers(ch):
        global config
        cur = conn.cursor()
        cur.execute(
            """
SELECT
  p.user_id user_id, p.guild_id guild_id,
  LTRIM(o.prefix) prefix,
  n.value nick,
  a.value avatar
FROM user_preferences p
  CROSS JOIN LATERAL unnest(string_to_array(p.value, ',')) AS o(prefix)
  LEFT JOIN user_preferences a
    ON p.user_id = a.user_id AND COALESCE(p.guild_id, 0) = COALESCE(a.guild_id, 0) AND a.key = 'tupper-avatar-' || LTRIM(o.prefix)
  LEFT JOIN user_preferences n
    ON p.user_id = n.user_id AND COALESCE(p.guild_id, 0) = COALESCE(n.guild_id, 0) AND n.key = 'tupper-nick-' || LTRIM(o.prefix)
WHERE p.key = 'tupper';
"""
        )
        tuptuple = cur.fetchone()
        while tuptuple:
            if not config.get("sync"):
                config["sync"] = {}
            ignorekey = f"tupper-ignore-{'m'+str(tuptuple[0])}"
            if not config["sync"].get(ignorekey):
                config["sync"][ignorekey] = []
            config["sync"][ignorekey].append(tuptuple[2])
            replacekey = f"tupper-replace-{tuptuple[1]}"
            config["sync"][f"{replacekey}-{tuptuple[0]}-{tuptuple[2]}-nick"] = tuptuple[
                3
            ]
            if tuptuple[4]:
                config["sync"][
                    f"{replacekey}-{tuptuple[0]}-{tuptuple[2]}-avatar"
                ] = tuptuple[4]
            logger.debug(f"{replacekey}-{tuptuple[0]}-{tuptuple[2]}: {tuptuple[3:]}")
            tuptuple = cur.fetchone()
        conn.commit()

    logger.debug("LT")
    load_tuppers(ch)
    logger.debug("LUHW")
    ch.load_hotwords()


@dataclass(kw_only=True)
class Component:
    type: int
    components: Optional[List] = None


@dataclass(kw_only=True)
class ActionRow(Component):
    type: int = 1
    components: List = field(default_factory=list)


@dataclass(kw_only=True)
class Button(Component):
    label: str
    custom_id: str
    style: int = 1
    type: int = 2


@dataclass(kw_only=True)
class View:
    components: List[Component] = field(default_factory=list)
    children: List = field(default_factory=list)
    __discord_ui_view__ = True

    def _start_listening_from_store(self, _) -> None:
        pass

    def refresh(self, _):
        pass

    def stop(self) -> None:
        pass

    def is_finished(self):
        return True

    def to_components(self) -> List[Component]:
        return self.components


def no_unroll_notify_view(
    message: Optional[discord.Message],
    client: discord.Client,
    args: List,
    ctx: Optional[discord.Interaction] = None,
) -> View:
    return View(
        components=[
            ActionRow(
                components=[
                    Button(
                        label=f"Currently {args[0]}, click to toggle",
                        custom_id="no_unroll_button_toggle",
                    )
                ]
            )
        ]
    )


async def user_config_menu_function(
    message: Optional[discord.Message],
    client: discord.Client,
    args: List,
    ctx: Optional[discord.Interaction] = None,
):
    assert len(args) > 0
    assert message
    if isinstance(args[0], str):
        key = args.pop()
        user = message.author
        guild = message.guild
    elif ctx and ctx.guild_id:
        key = args[0]["key"]
        user = ctx.user
        guild = client.get_guild(ctx.guild_id)
    else:
        return
    menu_preferences: Dict[str, Dict] = {
        "no_unroll_notify": {"function": no_unroll_notify_view}
    }
    dispatch_target = menu_preferences.get(key, None)
    if dispatch_target:
        toggle_config = ch.config.normalize_booleans(
            ch.user_config(
                user.id,
                guild.id if guild else 0,
                key=key,
                default="False",
                allow_global_substitute=True,
            )
        )
        if len(message.components):
            toggle_config = not args[0]["current_state"]
            ch.user_config(
                user.id,
                guild.id if guild else 0,
                key=key,
                value=str(toggle_config),
                default="False",
                allow_global_substitute=True,
            )
        view = dispatch_target["function"](message, client, [toggle_config, *args], ctx)
        if len(message.components) and ctx and ctx.response:
            await ctx.response.edit_message(content=message.content, view=view)
        else:
            messageWithView = await messagefuncs.sendWrappedMessage(
                "User configuration",
                view=view,
                target=message.channel,
            )
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO message_interaction_functions (message_id, user_id, function, state) VALUES (%s, %s, %s, %s) ON CONFLICT (message_id) DO UPDATE SET function = EXCLUDED.function, state = EXCLUDED.state;",
                    [
                        messageWithView.id,
                        user.id,
                        "user_config_menu_function",
                        ujson.dumps({"key": key, "current_state": toggle_config}),
                    ],
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(e)


def preference_function(
    message: discord.Message,
    client: discord.Client,
    args: List,
):
    global ch
    if len(args) > 1:
        value = " ".join(args[1:])
    else:
        value = None
    key = args[0]
    guild = None
    try:
        if ":" in key:
            key = key.split(":")
            guild = int(key[0])
            key = key[1]
    except:
        key = ":".join(key)
    if guild is None:
        guild = message.guild.id if message.guild else None
    value = ch.user_config(
        message.author.id,
        guild,
        key,
        value,
    )
    if value and ("secret" in key) or ("password" in key) or ("token" in key):
        return "```REDACTED```"
    return f"```{value}```"


async def dumptasks_function(message, client, args):
    tasks = asyncio.all_tasks(client.loop)
    await messagefuncs.sendWrappedMessage(tasks, message.author)


async def autounload(ch):
    try:
        logger.debug("Shutting down site")
        await ch.site.stop()
        logger.debug("Shutting down app")
        await ch.app.shutdown()
        logger.debug("Shutting down runner")
        await ch.runner.shutdown()
        logger.debug("Cleaning up runner")
        await ch.runner.cleanup()
    except Exception as e:
        logger.debug(e)


def autoload(ch):
    global client
    global config
    if ch is None:
        ch = CommandHandler(client, config)
    ch.add_command(
        {
            "trigger": ["!dumptasks"],
            "function": dumptasks_function,
            "async": True,
            "hidden": True,
            "admin": "global",
            "args_num": 0,
            "args_name": [],
            "description": "Dump current task stack",
        }
    )
    ch.add_command(
        {
            "trigger": ["!dumpbridges"],
            "function": lambda message, client, args: ", ".join(
                ch.webhook_sync_registry.keys()
            ),
            "async": False,
            "hidden": True,
            "admin": "global",
            "args_num": 0,
            "args_name": [],
            "description": "Output all bridges",
        }
    )
    ch.add_command(
        {
            "trigger": ["!dumpconfig"],
            "function": dumpconfig_function,
            "async": False,
            "hidden": True,
            "admin": "global",
            "args_num": 0,
            "args_name": [],
            "description": "Output current config",
        }
    )
    ch.add_command(
        {
            "trigger": ["!user_config_menu"],
            "function": user_config_menu_function,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "args_name": ["key"],
            "description": "Set or get user preference for this guild",
        }
    )
    ch.add_command(
        {
            "trigger": ["user_config_menu_function"],
            "function": user_config_menu_function,
            "async": True,
            "hidden": True,
            "component": True,
            "args_num": 1,
            "args_name": ["key"],
            "description": "Set or get user preference for this guild",
        }
    )
    ch.add_command(
        {
            "trigger": ["!preference"],
            "function": preference_function,
            "async": False,
            "args_num": 1,
            "args_name": ["key", "[value]"],
            "description": "Set or get user preference for this guild",
        }
    )
    ch.add_command(
        {
            "trigger": ["!privacy"],
            "function": lambda message, client, args: "Privacy policy is available at https://fletcher.fun/#privacy. For data deletion requests, please email fletcher@noblejury.com.",
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "Privacy policy",
        }
    )
    ch.add_command(
        {
            "trigger": ["!help", "!man"],
            "function": help_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "List commands and arguments",
        }
    )
    if config and ch.client:
        load_user_config(ch)
        if len(ch.commands) > 5:
            load_guild_config(ch)
            ch.client.loop.create_task(run_web_api(config, ch))
        bridge_guilds = list(
            filter(
                lambda guild: config.get(guild=guild, key="synchronize"),
                ch.client.guilds,
            )
        )
        ch.add_command(
            {
                "trigger": ["!reaction_list"],
                "function": reaction_list_function,
                "async": True,
                "hidden": True,
                "args_num": 0,
                "args_name": [""],
                "description": "List reactions",
                "message_command": True,
                "whitelist_guild": [guild.id for guild in bridge_guilds],
            }
        )
    logging.getLogger("discord.voice_client").setLevel("CRITICAL")


async def run_web_api(config, ch):
    app = Application()
    ch.app = app
    app.router.add_post("/", ch.web_handler)

    runner = AppRunner(app)
    await runner.setup()
    ch.runner = runner
    site = web.TCPSite(
        runner,
        config.get("webconsole", {}).get("hostname", "::"),
        config.get("webconsole", {}).get("port", 25585),
        reuse_port=True,
        shutdown_timeout=1,
    )
    try:
        await site.start()
    except OSError as e:
        logger.debug(e)
        pass
    ch.site = site


async def reaction_list_function(message, client, args, ctx):
    global ch
    bridge_key = f"{message.guild.name}:{message.channel.id}"
    if message.guild and ch.config.get(guild=message.guild, key="synchronize"):
        bridge = await ch.bridge_registry(bridge_key)
    else:
        bridge = None
    if bridge:
        cur = conn.cursor()
        query_params = [message.guild.id, message.channel.id, message.id]
        cur.execute(
            "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
            query_params,
        )
        metuples = cur.fetchall()
        if not len(metuples):
            cur.execute(
                "SELECT fromguild, fromchannel, frommessage FROM messagemap WHERE toguild = %s AND tochannel = %s AND tomessage = %s;",
                query_params,
            )
            metuples = cur.fetchall()
            query_params = metuples[0]
            cur.execute(
                "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
                query_params,
            )
            metuples.extend(cur.fetchall())
        else:
            metuples = [[message.guild.id, message.channel.id, message.id], *metuples]
        conn.commit()
    else:
        return await ctx.response.send_message(
            "No bridge found to list reactions from.", ephemeral=True
        )
    reactions = ""
    for metuple in metuples:
        guild_id, channel_id, message_id = metuple
        toGuild = client.get_guild(guild_id)
        assert toGuild is not None
        toChannel = toGuild.get_channel(channel_id)
        assert toChannel is not None
        toMessage = await toChannel.fetch_message(message_id)
        if len(toMessage.reactions):
            reactions += f"From #{toChannel.name} ({toGuild.name})\n"
            for r in toMessage.reactions:
                count = r.count - (1 if r.me else 0)
                users = (u for u in await r.users().flatten() if u.id != client.user.id)
                if count > 4:
                    users = itertools.islice(users, 4)
                users = (u.display_name for u in users)
                if count:
                    reactions += f"{count} x {r.emoji}{'' if count == 0 else ' '+', '.join(users)+('…' if count > 4 else '')}\n"
    if not reactions:
        reactions = "No reactions from bridged channel(s)."
    return await ctx.response.send_message(reactions[:2000], ephemeral=True)
