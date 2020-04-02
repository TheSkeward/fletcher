from datetime import datetime
from emoji import UNICODE_EMOJI
import asyncio
from aiohttp import web
from aiohttp.web import AppRunner, Application, TCPSite

import discord
import logging
import messagefuncs
import greeting
import inspect
import janissary
import re
from sys import exc_info
import textwrap
import ujson
from functools import lru_cache, partial

logger = logging.getLogger("fletcher")

regex_cache = dict()
webhooks_cache = dict()
remote_command_runner = None

class CommandHandler:

    # constructor
    def __init__(self, client):
        self.client = client
        self.commands = []
        self.join_handlers = {}
        self.remove_handlers = {}
        self.reload_handlers = {}
        self.message_reaction_handlers = {}
        self.message_reaction_remove_handlers = {}
        self.tag_id_as_command = re.compile(
            "(?:^(?:Oh)?\s*(?:<@"
            + str(client.user.id)
            + ">|Fletch[er]*)[, .]*)|(?:[, .]*(?:<@"
            + str(client.user.id)
            + ">|Fletch[er]*)[, .]*$)",
            re.IGNORECASE,
        )
        self.bang_remover = re.compile("^!+")

    def add_command(self, command):
        command["module"] = inspect.stack()[1][1].split("/")[-1].rstrip(".py")
        if type(command["trigger"]) != tuple:
            command["trigger"] = tuple(command["trigger"])
        self.commands.append(command)

    def add_remove_handler(self, func_name, func):
        self.remove_handlers[func_name] = func

    def add_join_handler(self, func_name, func):
        self.join_handlers[func_name] = func

    def add_reload_handler(self, func_name, func):
        self.reload_handlers[func_name] = func

    def add_message_reaction_remove_handler(self, message_ids, func):
        for message_id in message_ids.split(","):
            self.message_reaction_remove_handlers[int(message_id)] = func

    def add_message_reaction_handler(self, message_ids, func):
        for message_id in message_ids.split(","):
            self.message_reaction_handlers[int(message_id)] = func

    async def web_handler(self, request):
        json = await request.json()
        channel_config = ch.scope_config(guild=json['guild_id'], channel=json['channel_id'])
        if request.remote == channel_config.get('remote_ip', None):
            channel = self.client.get_guild(json['guild_id']).get_channel(json['channel_id'])
            await messagefuncs.sendWrappedMessage(json['message'], channel)
            return web.Response(status=200)
        return web.Response(status=400)

    async def reaction_handler(self, reaction):
        try:
            global config
            messageContent = str(reaction.emoji)
            channel = self.client.get_channel(reaction.channel_id)
            user = reaction.member
            message = await channel.fetch_message(reaction.message_id)
            admin = self.is_admin(message, user)
            args = [reaction, user, "add"]
            try:
                guild_config = self.scope_config(guild=message.guild)
                channel_config = self.scope_config(
                    guild=message.guild, channel=message.channel
                )
            except (AttributeError, ValueError) as e:
                if "guild" in str(e):
                    # DM configuration, default to none
                    guild_config = dict()
                    channel_config = dict()
            if type(channel) is discord.TextChannel:
                logger.info(
                    f"#{channel.guild.name}:{channel.name} <{user.name}:{user.id}> reacting with {messageContent} to {message.id}",
                    extra={
                        "GUILD_IDENTIFIER": channel.guild.name,
                        "CHANNEL_IDENTIFIER": channel.name,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                        "REACTION_IDENTIFIER": messageContent
                    },
                )
            elif type(channel) is discord.DMChannel:
                logger.info(
                    f"@{channel.recipient.name} <{user.name}:{user.id}> reacting with {messageContent} to {message.id}",
                    extra={
                        "GUILD_IDENTIFIER": "@",
                        "CHANNEL_IDENTIFIER": channel.recipient.name,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                        "REACTION_IDENTIFIER": messageContent
                    },
                )
            else:
                # Group Channels don't support bots so neither will we
                pass
            if (
                channel_config.get("blacklist-emoji")
                and not admin['channel']
                and messageContent in channel_config.get("blacklist-emoji")
            ):
                logger.info("Emoji removed by blacklist")
                return await message.remove_reaction(messageContent, user)
            if guild_config.get("subscribe", dict()).get(message.id):
                for user_id in guild_config.get("subscribe", dict()).get(message.id):
                    await message.guild.get_member(user_id).send(
                        f"{user.display_name} ({user.name}#{user.discriminator}) reacting with {messageContent} to https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    )
            args = [reaction, user, "add"]
            scoped_command = None
            if self.message_reaction_handlers.get(message.id) and self.message_reaction_handlers.get(message.id).get("scope", "message") != "channel":
                scoped_command = self.message_reaction_handlers[message.id]
            elif self.message_reaction_handlers.get(channel.id) and self.message_reaction_handlers.get(channel.id).get("scope", "message") == "channel":
                scoped_command = self.message_reaction_handlers[channel.id]
            if scoped_command:
                logger.debug(scoped_command)
                if (
                    messageContent.startswith(tuple(scoped_command["trigger"]))
                    and self.allowCommand(scoped_command, message, user=user)
                    and not scoped_command.get("remove", False)
                    and scoped_command["args_num"] == 0
                ):
                    await self.run_command(scoped_command, message, args, user)
            else:
                for command in self.get_command(messageContent, message, max_args=0):
                    if not command.get("remove", False):
                        await self.run_command(command, message, args, user)
            if type(channel) is discord.TextChannel and self.webhook_sync_registry.get(
                channel.guild.name + ":" + channel.name
            ):
                if reaction.emoji.is_custom_emoji():
                    processed_emoji = self.client.get_emoji(reaction.emoji.id)
                else:
                    processed_emoji = reaction.emoji.name
                logger.debug(f'RXH: syncing reaction {processed_emoji}')
                cur = conn.cursor()
                cur.execute(
                    "SELECT fromguild, fromchannel, frommessage FROM messagemap WHERE toguild = %s AND tochannel = %s AND tomessage = %s LIMIT 1;",
                    [message.guild.id, message.channel.id, message.id],
                )
                metuple = cur.fetchone()
                conn.commit()
                if metuple is not None:
                    fromGuild = self.client.get_guild(metuple[0])
                    fromChannel = fromGuild.get_channel(metuple[1])
                    fromMessage = await fromChannel.fetch_message(metuple[2])
                    logger.debug(f"RXH: -> {fromMessage}")
                    syncReaction = await fromMessage.add_reaction(processed_emoji)
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE messagemap SET reactions = reactions || %s WHERE toguild = %s AND tochannel = %s AND tomessage = %s;",
                        [
                            '{"' + reaction.emoji.name + '"}',
                            message.guild.id,
                            message.channel.id,
                            message.id,
                        ],
                    )
                    conn.commit()
                cur = conn.cursor()
                cur.execute(
                    "SELECT toguild, tochannel, tomessage FROM messagemap WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s LIMIT 1;",
                    [message.guild.id, message.channel.id, message.id],
                )
                metuple = cur.fetchone()
                conn.commit()
                if metuple is not None:
                    toGuild = self.client.get_guild(metuple[0])
                    toChannel = toGuild.get_channel(metuple[1])
                    toMessage = await toChannel.fetch_message(metuple[2])
                    logger.debug(f"RXH: -> {toMessage}")
                    syncReaction = await toMessage.add_reaction(reaction.emoji)
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE messagemap SET reactions = reactions || %s WHERE fromguild = %s AND fromchannel = %s AND frommessage = %s;",
                        [
                            '{"' + reaction.emoji.name + '"}',
                            message.guild.id,
                            message.channel.id,
                            message.id,
                        ],
                    )
                    conn.commit()
        except Exception as e:
            if "cur" in locals() and "conn" in locals():
                conn.rollback()
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"RXH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    async def reaction_remove_handler(self, reaction):
        try:
            global config
            messageContent = str(reaction.emoji)
            channel = self.client.get_channel(reaction.channel_id)
            if type(channel) == discord.DMChannel:
                user = self.client.get_user(reaction.user_id)
            else:
                user = channel.guild.get_member(reaction.user_id)
            message = await channel.fetch_message(reaction.message_id)
            args = [reaction, user, "remove"]
            try:
                guild_config = self.scope_config(guild=message.guild)
                channel_config = self.scope_config(
                    guild=message.guild, channel=message.channel
                )
            except (AttributeError, ValueError) as e:
                if "guild" in str(e):
                    # DM configuration, default to none
                    guild_config = dict()
                    channel_config = dict()
            if guild_config.get("subscribe", dict()).get(message.id):
                for user_id in guild_config.get("subscribe", dict()).get(message.id):
                    await message.guild.get_member(user_id).send(
                        f"{user.display_name} ({user.name}#{user.discriminator}) removed reaction of {messageContent} from https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    )
            if self.message_reaction_remove_handlers.get(message.id):
                command = self.message_reaction_remove_handlers[message.id]
                if self.allowCommand(command, message, user=user):
                    await self.run_command(command, message, args, user)
            for command in self.get_command(messageContent, message, max_args=0):
                if self.allowCommand(command, message, user=user) and command.get("remove"):
                    await self.run_command(command, message, args, user)
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"RRH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    async def remove_handler(self, member):
        if self.scope_config(guild=member.guild).get("on_member_remove"):
            member_remove_actions = (
                self.scope_config(guild=member.guild).get("on_member_remove").split(",")
            )
            for member_remove_action in member_remove_actions:
                if member_remove_action in self.remove_handlers.keys():
                    await self.remove_handlers[member_remove_action](
                        member, self.client, self.scope_config(guild=member.guild)
                    )
                else:
                    logger.error(
                        f"Unknown member_remove_action [{member_remove_action}]"
                    )

    async def join_handler(self, member):
        if self.scope_config(guild=member.guild).get("on_member_join"):
            member_join_actions = (
                self.scope_config(guild=member.guild).get("on_member_join").split(",")
            )
            for member_join_action in member_join_actions:
                if member_join_action in self.join_handlers.keys():
                    await self.join_handlers[member_join_action](
                        member, self.client, self.scope_config(guild=member.guild)
                    )
                else:
                    logger.error(f"Unknown member_join_action [{member_join_action}]")

    async def channel_update_handler(self, before, after):
        pass # Stub

    async def reload_handler(self):
        try:
            # Trigger reload handlers
            for guild in self.client.guilds:
                if self.scope_config(guild=guild).get("on_reload"):
                    reload_actions = (
                        self.scope_config(guild=guild).get("on_reload").split(",")
                    )
                    for reload_action in reload_actions:
                        if reload_action in self.reload_handlers.keys():
                            await self.reload_handlers[reload_action](
                                guild, self.client, self.scope_config(guild=guild)
                            )
                        else:
                            logger.error(f"Unknown reload_action [{reload_action}]")
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"RLH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    async def command_handler(self, message):
        global config
        global sid
        global webhook_cache

        try:
            guild_config = self.scope_config(guild=message.guild)
            channel_config = self.scope_config(
                guild=message.guild, channel=message.channel
            )
        except (AttributeError, ValueError) as e:
            if "guild" in str(e):
                # DM configuration, default to none
                guild_config = dict()
                channel_config = dict()

        try:
            blacklist_category = [
                int(i)
                for i in guild_config.get("automod-blacklist-category", "0").split(",")
            ]
            blacklist_channel = [
                int(i)
                for i in guild_config.get("automod-blacklist-channel", "0").split(",")
            ]
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
                    f"{message.id} #{message.guild.name}:{message.channel.name} <{message.author.name}:{message.author.id}> [{sent_com_score}] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": message.guild.name,
                        "CHANNEL_IDENTIFIER": message.channel.name,
                        "SENDER_NAME": message.author.name,
                        "SENDER_ID": message.author.id,
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
                    in config.get("moderation", dict()).get("guilds", "").split(",")
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
                        f"{message.id} #{message.guild.name}:{message.channel.name} <{message.author.name}:{message.author.id}> [Nil] {message.system_content}",
                        extra={
                            "GUILD_IDENTIFIER": message.guild.name,
                            "CHANNEL_IDENTIFIER": message.channel.name,
                            "SENDER_NAME": message.author.name,
                            "SENDER_ID": message.author.id,
                            "MESSAGE_ID": str(message.id),
                        },
                    )
                elif type(message.channel) is discord.DMChannel:
                    logger.info(
                        f"{message.id} @{message.channel.recipient.name} <{message.author.name}:{message.author.id}> [Nil] {message.system_content}",
                        extra={
                            "GUILD_IDENTIFIER": "@",
                            "CHANNEL_IDENTIFIER": message.channel.recipient.name,
                            "SENDER_NAME": message.author.name,
                            "SENDER_ID": message.author.id,
                            "MESSAGE_ID": str(message.id),
                        },
                    )
                else:
                    # Group Channels don't support bots so neither will we
                    pass
        except AttributeError as e:
            if type(message.channel) is discord.TextChannel:
                logger.info(
                    f"{message.id} #{message.guild.name}:{message.channel.name} <{message.author.name}:{message.author.id}> [Nil] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": message.guild.name,
                        "CHANNEL_IDENTIFIER": message.channel.name,
                        "SENDER_NAME": message.author.name,
                        "SENDER_ID": message.author.id,
                        "MESSAGE_ID": str(message.id),
                    },
                )
            elif type(message.channel) is discord.DMChannel:
                logger.info(
                    f"{message.id} @{message.channel.recipient.name} <{message.author.name}:{message.author.id}> [Nil] {message.system_content}",
                    extra={
                        "GUILD_IDENTIFIER": "@",
                        "CHANNEL_IDENTIFIER": message.channel.recipient.name,
                        "SENDER_NAME": message.author.name,
                        "SENDER_ID": message.author.id,
                        "MESSAGE_ID": str(message.id),
                    },
                )
            else:
                # Group Channels don't support bots so neither will we
                pass
            pass
        if config.get("sync", {}).get(f"tupper-ignore-{message.guild.id}", ""):
            for prefix in tuple(
                    config.get("sync", {})
                    .get(f"tupper-ignore-{message.guild.id}", "")
                    .split(",")
                ):
                if message.content.startswith(prefix) and config.get("sync", {}).get(f"tupper-replace-{message.guild.id}-{message.author.id}-{prefix}-nick", ""):
                    content = message.clean_content[len(prefix):]
                    attachments = []
                    if len(message.attachments) > 0:
                        plural = ""
                        if len(message.attachments) > 1:
                            plural = "s"
                        for attachment in message.attachments:
                            logger.debug("Syncing " + attachment.filename)
                            attachment_blob = io.BytesIO()
                            await attachment.save(attachment_blob)
                            attachments.append(
                                discord.File(attachment_blob, attachment.filename)
                            )
                    fromMessageName = config.get("sync", {}).get(f"tupper-replace-{message.guild.id}-{message.author.id}-{prefix}-nick", "")
                    webhook = webhooks_cache.get("sync", {}).get(f"{message.guild.id}:{message.channel.id}")
                    if not webhook:
                        try:
                            webhooks = await message.channel.webhooks()
                        except discord.Forbidden:
                            await message.author.send(f'Unable to list webhooks to fulfill your nickmask in {message.channel}! I need the manage webhooks permission to do that.')
                            continue
                        if len(webhooks) > 0:
                            webhook = discord.utils.get(webhooks, name=config.get("discord", dict()).get("botNavel", "botNavel"))
                        if not webhook:
                            webhook = await message.channel.create_webhook(name=config.get("discord", dict()).get("botNavel", "botNavel"), reason='Autocreating for nickmask')
                        webhooks_cache[f"{message.guild.id}:{message.channel.id}"] = webhook

                    await webhook.send(
                        content=content,
                        username=fromMessageName,
                        avatar_url=config.get("sync", {}).get(f"tupper-replace-{message.guild.id}-{message.author.id}-{prefix}-avatar", message.author.avatar_url_as(format="png", size=128)),
                        embeds=message.embeds,
                        tts=message.tts,
                        files=attachments,
                    )
                    try:
                        return await message.delete()
                    except discord.NotFound:
                        return
                    except discord.Forbidden:
                        return await message.author.send(f'Unable to remove original message for nickmask in {message.channel}! I need the manage messages permission to do that.')
        if (
            messagefuncs.extract_identifiers_messagelink.search(message.content)
            or messagefuncs.extract_previewable_link.search(message.content)
        ) and not message.content.startswith(("!preview", "!blockquote", "!xreact")):
            if str(message.author.id) not in config.get("moderation", dict()).get(
                "blacklist-user-usage", ""
            ).split(","):
                await messagefuncs.preview_messagelink_function(
                    message, self.client, None
                )
        if "rot13" in message.content:
            if str(message.author.id) not in config.get("moderation", dict()).get(
                "blacklist-user-usage", ""
            ).split(","):
                await message.add_reaction(
                    self.client.get_emoji(
                        int(config.get("discord", dict()).get("rot13", "clock1130"))
                    )
                )
        searchString = message.content
        searchString = self.tag_id_as_command.sub("!", searchString)
        if config["interactivity"]["enhanced-command-finding"] == "on":
            if len(searchString) and searchString[-1] == "!":
                searchString = "!" + searchString[:-1]
            searchString = self.bang_remover.sub("!", searchString)
        searchString = searchString.rstrip()
        if channel_config.get("regex") == "pre-command" and (
            channel_config.get("regex-tyranny", "On") == "Off"
            or not message.channel.permissions_for(message.author).manage_messages
        ):
            continue_flag = await greeting.regex_filter(
                message, self.client, channel_config
            )
            if not continue_flag:
                return
        args = list(filter("".__ne__, searchString.split(" ")))
        if len(args):
            args.pop(0)
        for command in self.get_command(searchString, message, mode="keyword_trie", max_args=len(args)):
            await self.run_command(command, message, args, message.author)
            # Run at most one command
            break
        if guild_config.get("hotwords_loaded"):
            for hotword in filter(lambda hw: (type(hw) is Hotword) and (len(hw.user_restriction) == 0) or (message.author.id in hw.user_restriction), regex_cache.get(message.guild.id, [])):
                if hotword.compiled_regex.search(message.content):
                    for command in hotword.target:
                        await command(message, self.client, args)
        if channel_config.get("regex") == "post-command" and (
            channel_config.get("regex-tyranny", "On") == "Off"
            or not message.channel.permissions_for(message.author).manage_messages
        ):
            continue_flag = await greeting.regex_filter(
                message, self.client, channel_config
            )
            if not continue_flag:
                return

    async def run_command(self, command, message, args, user):
        if command.get("long_run") == "author":
            await user.trigger_typing()
        elif command.get("long_run"):
            await message.channel.trigger_typing()
        logger.debug(f"[CH] Triggered {command}")
        if str(user.id) in self.scope_config()["moderation"][
            "blacklist-user-usage"
        ].split(","):
            raise Exception(f"Blacklisted command attempt by user {user}")
        if command["async"]:
            await command["function"](message, self.client, args)
        else:
            await messagefuncs.sendWrappedMessage(
                str(command["function"](message, self.client, args)),
                message.channel
            )

    def blacklist_command(self, command_name, guild_id):
        commands = self.get_command("!"+command_name)
        if len(commands):
            for command in commands:
                if not command.get("blacklist_guild"):
                    command["blacklist_guild"] = []
                command["blacklist_guild"].append(guild_id)
                logger.debug(f"Blacklisting {command} on guild {guild_id}")
        else:
            logger.error(f"Couldn't find {command_name} for blacklisting on guild {guild_id}")

    def scope_config(self, message=None, channel=None, guild=None, mutable=False):
        global config
        if guild is None:
            if channel and type(channel) != discord.DMChannel:
                guild = channel.guild
            elif message and type(channel) != discord.DMChannel:
                guild = message.guild
            else:
                return config
        if channel is None:
            if message:
                channel = message.channel
        if guild and type(guild) is not int:
            guild = guild.id
        if channel and type(channel) is not int:
            channel = channel.id
        if guild and channel and self.client.get_guild(guild).get_channel(channel).category_id:
            category = self.client.get_guild(guild).get_channel(channel).category_id
        else:
            category = None
        if channel:
            channel = f" - {int(channel)}"
        else:
            channel = ""
        try:
            if mutable:
                if config.get(f"Guild {guild}{channel}"):
                    return config.get(f"Guild {guild}{channel}")
                elif category and config.get(f"Guild {guild} - {int(category)}"):
                    return config.get(f"Guild {guild} - {int(category)}")
                else:
                    config[f"Guild {guild}{channel}"] = []
                    return config.get(f"Guild {guild}{channel}")
            else:
                if not config.get(f"Guild {guild}{channel}") and category and config.get(f"Guild {guild} - {int(category)}"):
                    return dict(config.get(f"Guild {guild} - {int(category)}"))
                else:
                    return dict(config.get(f"Guild {guild}{channel}"))
        except TypeError:
            return dict()
        
        
    @lru_cache(maxsize=256)
    def user_config(self, user, guild, key, value=None):
        cur = conn.cursor()
        if not value:
            cur.execute(
                "SELECT value FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = %s LIMIT 1;",
                [user, guild, key]
            )
            value = cur.fetchone()
            if value:
                value = value[0]
        else:
            cur.execute(
                "SELECT value FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = %s LIMIT 1;",
                [user, guild, key]
            )
            old_value = cur.fetchone()
            if old_value:
                cur.execute(
                    "UPDATE user_preferences SET value = %s WHERE user_id = %s AND guild_id = %s AND key = %s;",
                    [value, user, guild, key]
                )
            else:
                cur.execute(
                    "INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, %s, %s);",
                    [user, guild, key, value]
                )
        conn.commit()
        return value

    def is_admin(self, message, user=None):
        global config
        if not user:
            try:
                user = message.guild.get_member(message.author.id) or message.author
            except AttributeError:
                user = message.author
        globalAdmin = user.id in [int(i.strip()) for i in config["discord"].get("globalAdmin", "").split(",")]
        serverAdmin = (globalAdmin and config["discord"].get("globalAdminIsServerAdmin", "") == "True") or (type(user) is discord.Member and user.guild_permissions.manage_webhooks)
        channelAdmin = (globalAdmin and config["discord"].get("globalAdminIsServerAdmin", "") == "True") or serverAdmin or (type(user) is discord.Member  and user.permissions_in(message.channel).manage_webhooks)
        return {
                'global': globalAdmin,
                'server': serverAdmin,
                'channel': channelAdmin
                }
    def allowCommand(self, command, message, user=None):
        global config
        if not user:
            user = message.author
        admin = self.is_admin(message, user=user)
        if "admin" in command:
            if command["admin"] == "global" and admin['global']:
                return True
            # Guild admin commands
            if type(message.channel) != discord.DMChannel:
                # Server-specific
                if (
                    str(command["admin"]).startswith("server:")
                    and message.guild.id
                    in [
                        int(guild.strip())
                        for guild in command["admin"].split(":")[1].split(",")
                    ]
                    and admin['server']
                ):
                    return True
                # Channel-specific
                elif (
                    str(command["admin"]).startswith("channel:")
                    and message.channel.id
                    in [
                        int(channel.strip())
                        for channel in command["admin"].split(":")[1].split(",")
                    ]
                    and admin['channel']
                ):
                    return True
                # Any server
                elif command["admin"] in ["server", True] and admin['server']:
                    return True
                # Any channel
                elif command["admin"] == "channel" and admin['channel']:
                    return True
            # Unprivileged
            if command["admin"] == False:
                return True
            else:
                # Invalid config
                return False
        else:
            # No admin set == Unprivileged
            return True



    def accessible_commands(self, message, user=None):
        global config
        if str(message.author.id) in config["moderation"][
                "blacklist-user-usage"
                ].split(","):
            return []
        admin = self.is_admin(message, user=user)
        if admin['global']:
            def command_filter(c):
                return True
        elif admin['server']:
            def command_filter(c):
                return (type(message.channel) is discord.DMChannel or message.guild.id not in c.get("blacklist_guild", [])) and not c.get("hidden", False)
        else:
            def command_filter(c):
                return (type(message.channel) is discord.DMChannel or message.guild.id not in c.get("blacklist_guild", [])) and not c.get("admin", False) and not c.get("hidden", False)
    
        try:
            return list(filter(command_filter, self.commands))
        except IndexError:
            return []

    def get_command(ch, target_trigger, message=None, mode="exact", insensitive=True, min_args=0, max_args=99999, user=None):
        if insensitive:
            target_trigger = target_trigger.lower()
        if message:
            accessible_commands = ch.accessible_commands(message, user=user)
        else:
            accessible_commands = ch.commands
        if mode == "keyword":
            def query_filter(c):
                return any(target_trigger in trigger for trigger in c["trigger"]) and min_args <= c.get("args_num", 0) <= max_args
        if mode == "keyword_trie":
            def query_filter(c):
                return target_trigger.startswith(c["trigger"]) and min_args <= c.get("args_num", 0) <= max_args
        elif mode == "description":
            def query_filter(c):
                return any(target_trigger in trigger for trigger in c["trigger"]) or target_trigger in c["description"].lower() and min_args <= c.get("args_num", 0) <= max_args
        else: # if mode == "exact":
            def query_filter(c):
                return target_trigger in c["trigger"] and min_args <= c.get("args_num", 0) <= max_args
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

        if ch.is_admin(message)['server'] and public:
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
                accessible_commands = ch.get_command(keyword, message, mode="description")

            # Set verbose if filtered list
            if len(accessible_commands) < 5:
                verbose = True
                public = True
        else:
            try:
                accessible_commands = ch.accessible_commands(message)
            except IndexError:
                accessible_commands = []
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
        else:
            helpMessageBody = "\n".join(
                [
                    f'__{command["module"]}__ `{"` or `".join(command["trigger"][:2])}`: {command["description"]}'
                    for command in accessible_commands
                ]
            )
        await messagefuncs.sendWrappedMessage(helpMessageBody, target)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"HF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


def dumpconfig_function(message, client, args):
    global config
    if message.guild:
        dconfig = ch.scope_config(guild=message.guild)
    else:
        dconfig = config
    if len(args) == 1:
        return '```json\n'+ujson.dumps(dconfig.get(" ".join(args)), ensure_ascii=False, indent=4)+'```'
    else:
        return '```json\n'+ujson.dumps(config, ensure_ascii=False, indent=4)+'```'


class Hotword:
    def __init__(self, ch, word, hotword, owner):
        self.owner = owner
        if hotword.get("target_emoji"):
            if len(hotword["target_emoji"]) > 2 and hotword["target_emoji"] not in UNICODE_EMOJI:
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
                    raise ValueError('Target emoji not found')
            else:
                async def add_emoji(message, client, args):
                    await message.add_reaction(hotword["target_emoji"])
                self.target = [add_emoji]
        elif hotword.get("dm_me"):
            async def dm_me(owner, message, client, args):
                try:
                    await messagefuncs.sendWrappedMessage(f'Hotword {word} triggered by https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}',
                            client.get_user(owner.id))
                except AttributeError:
                    logger.debug(f'Couldn\'t send message because owner couln\'t be dereferenced for {word} in {message.guild}')
            self.target = [partial(dm_me, self.owner)]
        elif owner == "guild" and hotword.get("target_function"):
            self.target = [partial(ch.get_command, target_function_name)]
        else:
            raise ValueError('No valid target')
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
                'regex': self.regex,
                'compiled_regex': self.compiled_regex,
                'owner': self.owner,
                'user_restriction': self.user_restriction,
                'target': self.target
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
                            logger.error(f'Parsing {word} failed: {e}')
                            continue
                        hotwords[word] = hotword
                        guild_config["hotwords_loaded"] += ", " + word
                    guild_config["hotwords_loaded"] = guild_config["hotwords_loaded"].lstrip(", ")
                    if not regex_cache.get(guild.id):
                        regex_cache[guild.id] = []
                    logger.debug(f'Extending regex_cache[{guild.id}] with {hotwords.values()}')
                    regex_cache[guild.id].extend(hotwords.values())
        except NameError:
            pass
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"LGHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
    def load_blacklists(ch):
        for guild in ch.client.guilds:
            guild_config = ch.scope_config(guild=guild)
            for command_name in filter(None.__ne__, guild_config.get("blacklist-commands", "").split(",")):
                command_name = command_name.strip()
                if command_name:
                    ch.blacklist_command(command_name, guild.id)
    logger.debug('LBL')
    load_blacklists(ch)
    logger.debug('LGHW')
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
            "SELECT t.user_id, t.guild_id, t.key, t.value prefix, n.value nick, a.value avatar FROM user_preferences t RIGHT JOIN user_preferences a ON t.user_id = a.user_id AND t.guild_id = a.guild_id AND a.key = 'tupper-avatar-' || t.value RIGHT JOIN user_preferences n ON t.user_id = n.user_id AND t.guild_id = n.guild_id AND n.key = 'tupper-nick-' || t.value WHERE t.key = 'tupper';"
        )
        tuptuple = cur.fetchone()
        while tuptuple:
            if not config.get("sync"):
                config["sync"] = {}
            ignorekey = f"tupper-ignore-{tuptuple[1]}"
            replacekey = f"tupper-replace-{tuptuple[1]}"
            if not config["sync"].get(ignorekey, ""):
                config["sync"][ignorekey] = ""
            config["sync"][
                ignorekey
            ] = f'{config["sync"][ignorekey]},{tuptuple[3]}'.strip(",")
            config["sync"][
                f'{replacekey}-{tuptuple[0]}-{tuptuple[3]}-nick'
            ] = tuptuple[4]
            if tuptuple[5]:
                config["sync"][
                        f'{replacekey}-{tuptuple[0]}-{tuptuple[3]}-avatar'
                        ] = tuptuple[5]
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
                logger.debug(f'Loading {user_id} on {guild_id}: {hotword_json}')
                guild_config = ch.scope_config(guild=guild_id, mutable=True)
                try:
                    hotwords = ujson.loads(hotword_json)
                except ValueError as e:
                    exc_type, exc_obj, exc_tb = exc_info()
                    logger.info(f"LUHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                    hottuple = cur.fetchone()
                    continue
                if not guild_config.get("hotwords_loaded"):
                    guild_config["hotwords_loaded"] = ""
                for word in hotwords.keys():
                    try:
                        hotword = Hotword(ch, word, hotwords[word], ch.client.get_guild(guild_id).get_member(user_id))
                    except ValueError as e:
                        logger.error(f'Parsing {word} for {user_id} failed: {e}')
                        continue
                    except AttributeError as e:
                        logger.info(f'Parsing {word} for {user_id} failed: User is not on server {e}')
                        continue
                    hotwords[word] = hotword
                    guild_config["hotwords_loaded"] += ", " + word
                if not regex_cache.get(guild_id):
                    regex_cache[guild_id] = []
                add_me = list(filter(lambda hw: type(hw) == Hotword, hotwords.values()))
                logger.debug(f'Extending regex_cache[{guild_id}] with {add_me}')
                regex_cache[guild_id].extend(add_me)
                hottuple = cur.fetchone()
            conn.commit()
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"LUHF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

    def load_react_notifications(ch):
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, guild_id, key, value FROM user_preferences WHERE key = 'subscribe';"
        )
        subtuple = cur.fetchone()
        while subtuple:
            guild_config = ch.scope_config(guild=int(subtuple[1]), mutable=True)
            if not guild_config.get("subscribe"):
                guild_config["subscribe"] = {}
            if not guild_config["subscribe"].get(int(subtuple[3])):
                guild_config["subscribe"][int(subtuple[3])] = []
            guild_config["subscribe"][int(subtuple[3])].append(int(subtuple[0]))
            subtuple = cur.fetchone()
        conn.commit()

    logger.debug('LRN')
    load_react_notifications(ch)
    logger.debug('LT')
    load_tuppers(ch)
    logger.debug('LUHW')
    load_hotwords(ch)

def preference_function(message, client, args):
    global ch
    if len(args) > 1:
        value = " ".join(args[1:])
    else:
        value = None
    return '```'+ch.user_config(message.author.id, message.guild.id, args[0], value)+'```'

async def dumptasks_function(message, client, args):
    tasks = await client.loop.all_tasks()
    await message.author.send(f'{tasks}')

async def autounload(ch):
    try:
        await ch.runner.cleanup()
    except Exception as e:
        logger.debug(e)

def autoload(ch):
    global tag_id_as_command
    global client
    global config
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
            "function": lambda message, client, args: ", ".join(ch.webhook_sync_registry.keys()),
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
            "args_name": ['key', '[value]'],
            "description": "Set or get user preference for this guild",
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
    ch.user_config.cache_clear()
    if config and ch.client:
        load_user_config(ch)
        if len(ch.commands) > 3:
            load_guild_config(ch)
            ch.client.loop.create_task(run_web_api(config, ch))

async def run_web_api(config, ch):
    app = Application()
    app.router.add_post('/', ch.web_handler)

    runner = AppRunner(app)
    await runner.setup()
    ch.runner = runner
    site = web.TCPSite(runner, config.get("webconsole", {}).get("hostname", '::'), config.get("webconsole", {}).get("port", 25585))
    await site.start()
    ch.site = site
