from datetime import datetime
from emoji.unicode_codes import UNICODE_EMOJI
import asyncio
from io import BytesIO
from aiohttp import web, ClientSession
from aiohttp.web import AppRunner, Application
from psycopg2._psycopg import connection

import discord
import logging
import messagefuncs
import netcode
import greeting
import inspect
import janissary
import random
import re
from sys import exc_info
import traceback
import ujson
from functools import lru_cache, partial
import sentry_sdk
from asyncache import cached
from cachetools import TTLCache
import load_config
from typing import cast, TYPE_CHECKING, Dict, List, Iterable, Union, Callable, Awaitable

logger = logging.getLogger("fletcher")

regex_cache = {}
webhooks_cache = {}
remote_command_runner = None
Ans = None
config = cast(load_config.FletcherConfig, None)
conn = cast(connection, None)


def list_append(lst, item):
    lst.append(item)
    return item


def str_to_arr(string, delim=",", strip=True, filter_function=None.__ne__):
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

    def append(self, channel: discord.TextChannel, webhook: discord.Webhook):
        self.channels.append(channel)
        self.webhooks.append(webhook)


class Command:
    def __init__(
        self,
        trigger=[""],
        function: Union[Callable, Awaitable] = lambda message: message.content,
        sync=True,
        hidden=None,
        admin=False,
        args_num=0,
        args_name=[],
        description=None,
        exclusive=False,
        scope=discord.Message,
        remove=False,
        long_run=False,
    ):
        self.trigger = trigger
        self.function = function
        self.sync = sync
        self.hidden = hidden
        self.admin = admin
        self.arguments = {"min_count": args_num, "names": args_name}
        self.description = description
        self.exclusive = exclusive
        self.scope = scope
        self.remove = remove
        self.long_run = long_run

    def __str__(self) -> str:
        return f"{self.function}: {self.description}"


class CommandHandler:

    # constructor
    def __init__(self, client: discord.Client, config):
        self.client = client
        self.commands = []
        self.join_handlers = {}
        self.remove_handlers = {}
        self.reload_handlers = {}
        self.message_reply_handlers = {}
        self.message_reaction_handlers: Dict[int, Command] = {}
        self.message_reaction_remove_handlers = {}
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

        self.webhook_sync_registry: Dict[str, Bridge] = {
            "FromGuildId:FromChannelId": Bridge()
        }
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

    async def load_webhooks(self):
        webhook_sync_registry: Dict[str, Bridge] = {}
        navel_filter = f"{self.config.get(section='discord', key='botNavel')} ("
        for guild in filter(
            lambda guild: self.config.get(guild=guild, key="synchronize"),
            self.client.guilds,
        ):
            self_member = guild.get_member(self.user.id)
            assert self_member is not None
            if not self_member.guild_permissions.manage_webhooks:
                logger.warning(
                    f"LWH: Couldn't load webhooks for {guild.name} ({guild.id}), ask an admin to grant additional permissions (https://novalinium.com/go/4/fletcher)"
                )
                continue
            logger.debug(f"LWH: Querying {guild.name}")
            for webhook in filter(
                lambda webhook: webhook.name.startswith(navel_filter),
                await guild.webhooks(),
            ):
                fromTuple = webhook.name.split("(")[1].split(")")[0].split(":")
                fromTuple[0] = messagefuncs.expand_guild_name(fromTuple[0]).replace(
                    ":", ""
                )
                fromGuild = discord.utils.get(
                    self.client.guilds, name=fromTuple[0].replace("_", " ")
                )
                if not fromGuild or not fromGuild.id:
                    continue
                toChannel = guild.get_channel(webhook.channel_id)
                fromChannel = discord.utils.find(
                    lambda channel: channel.name == fromTuple[1]
                    or str(channel.id) == fromTuple[1],
                    fromGuild.text_channels,
                )
                if not fromChannel:
                    continue
                assert isinstance(toChannel, discord.TextChannel)
                fromChannelName = f'{fromTuple[0].replace("_", " ")}:{fromChannel.id}'
                # webhook_sync_registry[f"{fromGuild.id}:{webhook.id}"] = fromChannelName
                if not isinstance(webhook_sync_registry.get(fromChannelName), Bridge):
                    webhook_sync_registry[fromChannelName] = Bridge()
                bridge = cast(Bridge, webhook_sync_registry[fromChannelName])
                bridge.append(toChannel, webhook)
        self.webhook_sync_registry = webhook_sync_registry
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
        await asyncio.sleep(2)
        await self.client.change_presence(
            activity=discord.Game(name="fletcher.fun | !help", start=datetime.utcnow())
        )

    def add_command(self, command):
        command["module"] = inspect.stack()[1][1].split("/")[-1][:-3]
        if type(command["trigger"]) != tuple:
            command["trigger"] = tuple(command["trigger"])
        logger.debug(f"Loading command {command}")
        self.commands.append(command)

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

    async def tupper_proc(self, message):
        global config
        global webhooks_cache
        tupperId = 431544605209788416
        sync = cast(dict, config.get(section="sync"))
        user = message.author
        if type(message.channel) is not discord.TextChannel:
            return
        if not (
            message.guild
            and sync.get(f"tupper-ignore-{message.guild.id}")
            or sync.get(f"tupper-ignore-m{user.id}")
        ):
            return
        tupper = discord.utils.get(message.channel.members, id=tupperId)
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
            if len(message.attachments) > 0:
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
            webhook = webhooks_cache.get(f"{message.guild.id}:{message.channel.id}")
            if not webhook:
                try:
                    webhooks = await message.channel.webhooks()
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(
                        f"Unable to list webhooks to fulfill your nickmask in {message.channel}! I need the manage webhooks permission to do that.",
                        user,
                    )
                    continue
                if len(webhooks) > 0:
                    webhook = discord.utils.get(
                        webhooks, name=config.get(section="discord", key="botNavel")
                    )
                if not webhook:
                    webhook = await message.channel.create_webhook(
                        name=config.get(section="discord", key="botNavel"),
                        reason="Autocreating for nickmask",
                    )
                webhooks_cache[f"{message.guild.id}:{message.channel.id}"] = webhook

            sent_message = await webhook.send(
                content=content,
                username=fromMessageName,
                avatar_url=sync.get(
                    f"{tupperreplace}-avatar",
                    user.display_avatar,
                ),
                embeds=message.embeds if len(message.embeds) else reply_embed,
                tts=message.tts,
                files=attachments,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False
                ),
                wait=True,
            )
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
                    f"Unable to remove original message for nickmask in {message.channel}! I need the manage messages permission to do that.",
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
                messageParts = re.search(r"> <([^>]*)> (.*)", json["message"])
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

    async def reaction_handler(self, reaction):
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            if TYPE_CHECKING:
                assert hub is not None
            with hub.configure_scope() as scope:  # type: ignore
                try:
                    global config
                    messageContent = str(reaction.emoji)
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
                        scope.set_tag("guild", message.guild.name)
                    else:
                        user = self.client.get_user(reaction.user_id)
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
                        assert channel.recipient is not None
                        logger.info(
                            f"{message.id} @{channel.recipient.name} <{user.name if user else 'Unkown User'}:{reaction.user_id}> reacting with {messageContent}",
                            extra={
                                "GUILD_IDENTIFIER": "@",
                                "CHANNEL_IDENTIFIER": channel.recipient.name,
                                "SENDER_NAME": user.name if user else "Unkown User",
                                "SENDER_ID": reaction.user_id,
                                "MESSAGE_ID": str(message.id),
                                "REACTION_IDENTIFIER": messageContent,
                            },
                        )
                    else:
                        # Group Channels don't support bots so neither will we
                        pass
                    if not isinstance(user, (discord.User, discord.Member)):
                        logger.debug("Dropping reaction, user not found")
                        return
                    assert isinstance(user, (discord.User, discord.Member))
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
                        if isinstance(
                            channel, discord.TextChannel
                        ) and self.webhook_sync_registry.get(
                            f"{channel.guild.name}:{channel.id}"
                        ):
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
                                assert fromGuild is not None
                                fromChannel = fromGuild.get_channel(metuple[1])
                                assert isinstance(fromChannel, discord.TextChannel)
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
                                        "Demurring to bridge reaction to message of users on the blacklist"
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
                                        return
                                logger.debug(
                                    f"RXH: {processed_emoji} -> {fromMessage.id} ({fromGuild.name})"
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
                                toChannel = toGuild.get_channel(metuple[1])
                                assert isinstance(toChannel, discord.TextChannel)
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
                                        "Demurring to bridge reaction to message of users on the blacklist"
                                    )
                                    return
                                logger.debug(
                                    f"RXH: {processed_emoji} -> {toMessage.id} ({toGuild.name})"
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
            with hub.configure_scope() as scope:  # type: ignore
                try:
                    global config
                    messageContent = str(reaction.emoji)
                    channel = self.client.get_channel(reaction.channel_id)
                    user = None
                    if channel is None:
                        user = self.client.get_user(reaction.user_id)
                        assert user is not None
                        channel = user.create_dm()
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
                    if isinstance(channel, (discord.TextChannel, discord.Thread)):
                        user = channel.guild.get_member(reaction.user_id)
                        scope.set_tag("guild", channel.guild.name)
                    scope.user = {"id": user.id if user else 0, "username": str(user)}
                    message = await channel.fetch_message(reaction.message_id)
                    assert isinstance(user, (discord.User, discord.Member))
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
                        assert channel.recipient is not None
                        logger.info(
                            f"{message.id} @{channel.recipient.name} <{user.name}:{user.id}> unreacting with {messageContent}",
                            extra={
                                "GUILD_IDENTIFIER": "@",
                                "CHANNEL_IDENTIFIER": channel.recipient.name,
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
            with hub.configure_scope() as scope:
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
            with hub.configure_scope() as scope:  # type: ignore
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
                if member.guild_permissions.manage_guild:
                    loop.create_task(self.load_guild_invites(guild))
                reload_actions = cast(
                    Iterable,
                    self.config.get(guild=guild.id, key="on_reload_list", default=[]),
                )
                for reload_action in reload_actions:
                    if reload_action in self.reload_handlers.keys():
                        loop.create_task(
                            self.reload_handlers[reload_action](
                                guild, self.client, self.scope_config(guild=guild)
                            )
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

    async def bridge_message(self, message):
        global conn
        try:
            if not message.guild:
                return
        except AttributeError:
            return
        bridge_key = f"{message.guild.name}:{message.channel.id}"
        bridge = self.webhook_sync_registry.get(bridge_key)
        user = message.author
        # if the message is from the bot itself or sent via webhook, which is usually done by a bot, ignore it if not in whitelist
        if message.webhook_id:
            webhook = await self.fetch_webhook_cached(message.webhook_id)
            if webhook.name not in cast(
                Iterable, self.config.get(section="sync", key="whitelist-webhooks")
            ):
                if webhook.name and not webhook.name.startswith(
                    cast(str, self.config.get(section="discord", key="botNavel"))
                ):
                    logger.debug("Webhook isn't whitelisted for bridging")
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
            return
        if isinstance(bridge, Bridge):
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
                        metuple = query_params[3:]
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
                    if metuple is not None:
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
                try:
                    syncMessage = await bridge.webhooks[i].send(
                        content=content,
                        username=fromMessageName,
                        avatar_url=user.display_avatar,
                        embeds=list(filter(None, message.embeds + reply_embed))
                        if user.bot
                        else reply_embed,
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
                    )
                except discord.HTTPException as e:
                    if attachments:
                        content += f"\n {len(message.attachments)} file{'s' if len(message.attachments) > 1 else ''} attached (too large to bridge)."
                        for attachment in message.attachments:
                            content += f"\n• <{attachment.url}>"
                        syncMessage = await bridge.webhooks[i].send(
                            content=content,
                            username=fromMessageName,
                            avatar_url=user.display_avatar,
                            embeds=list(filter(None, message.embeds + reply_embed))
                            if user.bot
                            else reply_embed,
                            tts=message.tts,
                            files=[],
                            wait=True,
                            allowed_mentions=discord.AllowedMentions(
                                users=user_mentions, roles=False, everyone=False
                            ),
                        )
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
                )

    async def typing_handler(self, channel, user):
        if (
            user != self.client.user
            and type(channel) is discord.TextChannel
            and channel.guild
            and self.webhook_sync_registry.get(f"{channel.guild.name}:{channel.id}")
        ):
            await asyncio.gather(
                *[
                    channel.trigger_typing()
                    for channel in self.webhook_sync_registry[
                        f"{channel.guild.name}:{channel.id}"
                    ].channels
                ]
            )

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
                    assert fromChannel.recipient is not None
                    logger.info(
                        f"{message.id} @{fromChannel.recipient.name} <{fromMessage.author.name}:+{fromMessage.author.id}> [Edit] {fromMessage.content}",
                        extra={
                            "GUILD_IDENTIFIER": "@",
                            "CHANNEL_IDENTIFIER": fromChannel.recipient,
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
            if fromGuild and self.webhook_sync_registry.get(
                f"{fromGuild.name}:{fromChannel.id}"
            ):
                await asyncio.sleep(1)
                cur = conn.cursor()
                query_params = [fromGuild.id, fromChannel.id, message.id]
                cur.execute(
                    "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
                    query_params,
                )
                metuples = cur.fetchall()
                conn.commit()
                logger.debug(f"[Bridge] {query_params} -> {metuples}")
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
                        f"ORMU: Demurring to edit message at client guild request"
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
                            f"Unable to remove original message for bridge in {message.channel}! I need the manage messages permission to do that."
                        )
                content = fromMessage.clean_content
                attachments: List[discord.File] = []
                if len(fromMessage.attachments) > 0:
                    plural = ""
                    if len(fromMessage.attachments) > 1:
                        plural = "s"
                    if (
                        fromMessage.channel.is_nsfw()
                        and not self.webhook_sync_registry[
                            f"{fromMessage.guild.name}:{fromMessage.channel.id}"
                        ]
                        .channels[0]
                        .is_nsfw()
                    ):
                        content = f"{content}\n {len(message.attachments)} file{plural} attached from an R18 channel."
                        for attachment in fromMessage.attachments:
                            content = f"{content}\n• <{attachment.url}>"
                    else:
                        for attachment in fromMessage.attachments:
                            logger.debug(f"Syncing {attachment.filename}")
                            attachment_blob = BytesIO()
                            await attachment.save(attachment_blob)
                            attachments.append(
                                discord.File(attachment_blob, attachment.filename)
                            )
                webhook = discord.utils.get(
                    self.webhook_sync_registry[
                        f"{fromMessage.guild.name}:{fromMessage.channel.id}"
                    ].webhooks,
                    channel__id=toChannel.id,
                )
                assert webhook is not None
                await webhook.edit_message(
                    content=content,
                    embeds=fromMessage.embeds,
                    files=attachments,
                    allowed_mentions=discord.AllowedMentions(
                        users=False, roles=False, everyone=False
                    ),
                    message_id=toMessage.id,
                )
            channel_config = cast(
                dict, self.scope_config(channel=fromChannel, guild=fromGuild)
            )
            if channel_config.get("regex", None) and not (
                channel_config.get("regex-tyranny", False)
                and message.channel.permissions_for(fromMessage.author).manage_messages
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

    async def command_handler(self, message):
        global config
        global sid

        user = message.author
        global Ans
        if (
            isinstance(message.channel, discord.DMChannel)
            and self.client.get_channel(message.channel.id) is None
        ):
            await message.author.create_dm()
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
                type(message.channel) is discord.TextChannel
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
                    guild_config.get("sent-com-score-threshold")
                    and sent_com_score
                    <= float(guild_config["sent-com-score-threshold"])
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
                if type(message.channel) is discord.TextChannel:
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
                    logger.info(
                        f"{message.id} @{message.channel.recipient.name or message.channel.id} <{user.name}:{user.id}> [Nil] {message.system_content}",
                        extra={
                            "GUILD_IDENTIFIER": "@",
                            "CHANNEL_IDENTIFIER": message.channel.recipient.name
                            or message.channel.id,
                            "SENDER_NAME": user.name,
                            "SENDER_ID": user.id,
                            "MESSAGE_ID": str(message.id),
                        },
                    )
                else:
                    # Group Channels don't support bots so neither will we
                    pass
        except AttributeError as e:
            if type(message.channel) is discord.TextChannel:
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
                logger.info(
                    f"{message.id} @{message.channel.recipient.name or message.channel.id} <{user.name}:{user.id}> [Nil] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": "@",
                        "CHANNEL_IDENTIFIER": message.channel.recipient.name
                        or message.channel.id,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                    },
                )
            else:
                # Group Channels don't support bots so neither will we
                pass
            pass
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
            webhook = await self.fetch_webhook_cached(message.webhook_id)
            if webhook.name not in self.config.get(
                key="whitelist-webhooks", section="sync", default=[]
            ):
                return
        await self.tupper_proc(message)
        preview_link_found = messagefuncs.extract_identifiers_messagelink.search(
            message.content
        ) or messagefuncs.extract_previewable_link.search(message.content)
        blacklisted_preview_command = message.content.startswith(
            ("!preview", "!blockquote", "!xreact")
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
            if refChannel:
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
            await self.run_command(command, message, args, user)
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
                        type(hw.owner) is discord.Member
                        and message.channel.permissions_for(hw.owner).read_messages
                        and message.author != hw.owner
                    )
                    or (type(hw.owner) is str and hw.owner == "guild")
                )
                and (len(hw.user_restriction) == 0)
                or (user.id in hw.user_restriction),
                regex_cache.get(message.guild.id, []),
            ):
                if hotword.compiled_regex.search(message.content):
                    for command in hotword.target:
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

    async def run_command(self, command, message, args, user):
        with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
            with hub.configure_scope() as scope:  # type: ignore
                scope.user = {"id": user.id, "username": str(user)}
                if hasattr(user, "guild"):
                    scope.set_tag("guild", user.guild.name)
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
                    elif command.get("long_run"):
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

    def blacklist_command(self, command_name, guild_id):
        if command_name == "all":
            commands = self.commands
        else:
            commands = self.get_command("!" + command_name)
            if not len(commands):
                commands = self.get_command(command_name)
        if len(commands):
            for command in commands:
                if not command.get("blacklist_guild"):
                    command["blacklist_guild"] = []
                command["blacklist_guild"].append(guild_id)
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

    @lru_cache(maxsize=256)
    def user_config(
        self, user, guild, key, value=None, default=None, allow_global_substitute=False
    ):
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
                cur.execute(
                    "INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, %s, %s);",
                    [user, guild, key, value],
                )
        conn.commit()
        if value is None:
            value = default
        return value

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

    async def on_interaction(self, ctx: discord.Interaction):
        logger.debug(str(ctx))
        await ctx.response.send_message("Not Implemented")

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
        if not thread.me:
            logger.debug(f"Adding myself to new thread {thread.name} ({thread.id})")
            await thread.add_user(thread.guild.get_member(self.user.id))
        else:
            if thread.guild:
                if thread.category_id not in self.config.get(
                    key="automod-blacklist-category", guild=thread.guild.id
                ):
                    for user in list(
                        filter(
                            lambda user: user in thread.parent.members,
                            load_config.expand_target_list(
                                self.config.get(
                                    key="manual-mod-userslist",
                                    default=[thread.guild.owner.id],
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
                                default="False",
                                allow_global_substitute=True,
                            )
                        )
                    )
                    if (isinstance(use_threads, bool) and use_threads) or (
                        isinstance(use_threads, str)
                        and thread.id
                        in tuple(
                            self.config.normalize(
                                self.config.normalize_array(use_threads)
                            )
                        )
                    ):
                        logger.debug(
                            f"Adding {user} to thread {thread.name} ({thread.id})"
                        )
                        await thread.add_user(user)
                global conn
                bridge_key = f"{thread.guild.name}:{thread.parent_id}"
                bridge = self.webhook_sync_registry.get(bridge_key)
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
                                    await self.client.get_channel(
                                        metuple[1]
                                    ).fetch_message(int(metuple[2]))
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
                        or config.get(
                            section="discord",
                            key="serverlAdminIgnoresBlacklists",
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
        if insensitive:
            target_trigger = target_trigger.lower()
        if message:
            accessible_commands = ch.accessible_commands(message, user=user)
        else:
            accessible_commands = ch.commands
        if mode == "keyword":

            def query_filter(c):
                return (
                    any(target_trigger in trigger for trigger in c["trigger"])
                    and min_args <= c.get("args_num", 0) <= max_args
                )

        if mode == "keyword_trie":

            def query_filter(c):
                return (
                    target_trigger.startswith(c["trigger"])
                    and min_args <= c.get("args_num", 0) <= max_args
                )

        elif mode == "description":

            def query_filter(c):
                return (
                    any(target_trigger in trigger for trigger in c["trigger"])
                    or target_trigger in c.get("description", "").lower()
                    and min_args <= c.get("args_num", 0) <= max_args
                )

        else:  # if mode == "exact":

            def query_filter(c):
                return (
                    target_trigger in c["trigger"]
                    and min_args <= c.get("args_num", 0) <= max_args
                )

        try:
            return list(filter(query_filter, accessible_commands))
        except IndexError:
            return []


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

                    async def add_emoji(message, client, args):
                        await message.add_reaction(intended_target_emoji)

                    self.target = [add_emoji]
                else:
                    raise ValueError("Target emoji not found")
            else:

                async def add_emoji(message, client, args):
                    await message.add_reaction(hotword["target_emoji"])

                self.target = [add_emoji]
        elif hotword.get("dm_me") or hotword.get("dm-me"):

            async def dm_me(owner, message, client, args):
                try:
                    response_message = await messagefuncs.sendWrappedMessage(
                        f"Hotword {word} triggered by https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}",
                        client.get_user(owner.id),
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

    def load_hotwords(ch):
        global regex_cache
        global config
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
                    if not guild_config.get("hotwords_loaded"):
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
                    if not regex_cache.get(guild.id):
                        regex_cache[guild.id] = []
                    logger.debug(f"Extending regex_cache[{guild.id}] with {add_me}")
                    regex_cache[guild.id].extend(add_me)
                hottuple = cur.fetchone()
            conn.commit()
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"LUHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    logger.debug("LT")
    load_tuppers(ch)
    logger.debug("LUHW")
    load_hotwords(ch)


def preference_function(message, client, args):
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
    if value:
        ch.user_config.cache_clear()
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
    tasks = asyncio.Task.all_tasks(client.loop)
    await messagefuncs.sendWrappedMessage(tasks, message.author)


async def edit_tup_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) in [discord.Member, discord.User]:
            cur = conn.cursor()
            query_param = [message.id, message.channel.id]
            if type(message.channel) is not discord.DMChannel:
                query_param.append(message.guild.id)
            cur.execute(
                f"SELECT author_id FROM attributions WHERE message = %s AND channel = %s AND guild {'= %s' if type(message.channel) is not discord.DMChannel else 'IS NULL'}",
                query_param,
            )
            subtuple = cur.fetchone()
            if subtuple and int(subtuple[0]) == args[1].id:
                conn.commit()
                try:
                    await message.remove_reaction("📝", args[1])
                except:
                    pass
                preview_message = await messagefuncs.sendWrappedMessage(
                    f"Reply to edit message at {message.jump_url}", args[1]
                )
                await messagefuncs.preview_messagelink_function(
                    preview_message, client, None
                )
                try:

                    def check(m):
                        return (
                            m.channel == preview_message.channel and m.author == args[1]
                        )

                    msg = await client.wait_for("message", check=check, timeout=6000)
                except asyncio.TimeoutError:
                    return await preview_message.edit(content="Message edit timed out.")
                else:
                    global webhooks_cache
                    webhook = webhooks_cache.get(
                        f"{message.guild.id}:{message.channel.id}"
                    )
                    if not webhook:
                        try:
                            webhooks = await message.channel.webhooks()
                        except discord.Forbidden:
                            return await messagefuncs.sendWrappedMessage(
                                f"Unable to list webhooks to fulfill your nickmask in {message.channel}! I need the manage webhooks permission to do that.",
                                user,
                            )
                        if len(webhooks) > 0:
                            webhook = discord.utils.get(
                                webhooks,
                                name=config.get(section="discord", key="botNavel"),
                            )
                        if not webhook:
                            webhook = await message.channel.create_webhook(
                                name=config.get(section="discord", key="botNavel"),
                                reason="Autocreating for nickmask",
                            )
                        webhooks_cache[
                            f"{message.guild.id}:{message.channel.id}"
                        ] = webhook
                    editMessage = await webhook.edit_message(
                        message.id,
                        content=msg.content,
                        allowed_mentions=discord.AllowedMentions(
                            users=False, roles=False, everyone=False
                        ),
                    )
                    return await msg.add_reaction("✅")
            conn.commit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ETF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


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
    ch.add_command(
        {
            "trigger": ["📝"],
            "function": edit_tup_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Allows you to edit a nickmasked message",
        }
    )
    ch.user_config.cache_clear()
    if config and ch.client:
        load_user_config(ch)
        if len(ch.commands) > 5:
            load_guild_config(ch)
            ch.client.loop.create_task(run_web_api(config, ch))
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
