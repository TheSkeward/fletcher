from datetime import datetime
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
from functools import lru_cache

logger = logging.getLogger("fletcher")

regex_cache = dict()


def allowCommand(command, message, user=None):
    global config
    if not user:
        user = message.author
    if "admin" in command:
        # Global admin commands use builtin global admin list
        if command["admin"] == "global" and user.id in [
            int(admin.strip()) for admin in config["discord"]["globalAdmin"].split(",")
        ]:
            return True
        # Guild admin commands
        if type(message.channel) == discord.TextChannel:
            # Server-specific
            if (
                str(command["admin"]).startswith("server:")
                and message.guild.id
                in [
                    int(guild.strip())
                    for guild in command["admin"].split(":")[1].split(",")
                ]
                and user.guild_permissions.manage_webhooks
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
                and user.permissions_in(message.channel).manage_webhooks
            ):
                return True
            # Any server
            elif command["admin"] in ["server", True] and (
                message.author.guild_permissions.manage_webhooks
                or (
                    config["discord"].get("globalAdminIsServerAdmin")
                    and user.id
                    in [
                        int(admin.strip())
                        for admin in config["discord"]["globalAdmin"].split(",")
                    ]
                )
            ):
                return True
            # Any channel
            elif (
                command["admin"] == "channel"
                and user.permissions_in(message.channel).manage_webhooks
            ):
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
        command["module"] = inspect.stack()[1][1]
        self.commands.append(command)

    def add_remove_handler(self, func_name, func):
        self.remove_handlers[func_name] = func

    def add_join_handler(self, func_name, func):
        self.join_handlers[func_name] = func

    def add_reload_handler(self, func_name, func):
        self.reload_handlers[func_name] = func

    def add_message_reaction_remove_handler(self, message_id, func):
        self.message_reaction_remove_handlers[int(message_id)] = func

    def add_message_reaction_handler(self, message_id, func):
        self.message_reaction_handlers[int(message_id)] = func

    async def reaction_handler(self, reaction):
        try:
            global config
            messageContent = str(reaction.emoji)
            channel = self.client.get_channel(reaction.channel_id)
            user = channel.guild.get_member(reaction.user_id)
            message = await channel.fetch_message(reaction.message_id)
            args = [reaction, user, "add"]
            try:
                guild_config = self.scope_config(guild=message.guild)
                channel_config = self.scope_config(
                    guild=message.guild, channel=message.channel
                )
            except ValueError as e:
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
                    },
                )
            elif type(message.channel) is discord.DMChannel:
                logger.info(
                    f"@{channel.recipient.name} <{user.name}:{user.id}> reacting with {messageContent} to {message.id}",
                    extra={
                        "GUILD_IDENTIFIER": "@",
                        "CHANNEL_IDENTIFIER": channel.recipient.name,
                        "SENDER_NAME": user.name,
                        "SENDER_ID": user.id,
                        "MESSAGE_ID": str(message.id),
                    },
                )
            else:
                # Group Channels don't support bots so neither will we
                pass
            if (
                channel_config.get("blacklist-emoji")
                and not message.channel.permissions_for(message.author).manage_messages
                and messageContent in channel_config.get("blacklist-emoji")
            ):
                logger.info("Emoji removed by blacklist")
                return await message.remove_reaction(messageContent, user)
            if guild_config.get("subscribe", dict()).get(message.id):
                for user_id in guild_config.get("subscribe", dict()).get(message.id):
                    await message.guild.get_member(user_id).send(
                        f"{user.display_name} ({user.name}#{user.discriminator}) reacting with {messageContent} to https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    )
            scoped_command = None
            if self.message_reaction_handlers.get(message.id) and self.message_reaction_handlers.get(message.id).get("scope", "message") != "channel":
                scoped_command = self.message_reaction_handlers[message.id]
            elif self.message_reaction_handlers.get(message.channel.id) and self.message_reaction_handlers.get(message.channel.id).get("scope", "message") == "channel":
                scoped_command = self.message_reaction_handlers[message.channel.id]
            if scoped_command:
                logger.debug(scoped_command)
                logger.debug(args)
                if (
                    messageContent.startswith(tuple(scoped_command["trigger"]))
                    and allowCommand(scoped_command, message, user=user)
                    and scoped_command["args_num"] == 0
                ):
                    if str(user.id) in config["moderation"][
                        "blacklist-user-usage"
                    ].split(","):
                        raise Exception("Blacklisted command attempt by user")
                    logger.debug(scoped_command["function"])
                    if scoped_command["async"]:
                        return await scoped_command["function"](message, self.client, args)
                    else:
                        return await message.channel.send(
                            str(
                                scoped_command["function"](
                                    message, self.client, [reaction, user, "add"]
                                )
                            )
                        )
            for command in self.commands:
                if (
                    messageContent.startswith(tuple(command["trigger"]))
                    and allowCommand(command, message, user=user)
                    and command["args_num"] == 0
                ):
                    logger.debug(command)
                    if str(user.id) in config["moderation"][
                        "blacklist-user-usage"
                    ].split(","):
                        raise Exception("Blacklisted command attempt by user")
                    logger.debug(command["function"])
                    if command["async"]:
                        return await command["function"](message, self.client, args)
                    else:
                        return await message.channel.send(
                            str(command["function"](message, self.client, args))
                        )
            if message.guild is not None and (
                message.guild.name + ":" + message.channel.name
                in self.webhook_sync_registry.keys()
            ):
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
                    if reaction.emoji.is_custom_emoji():
                        processed_emoji = self.client.get_emoji(reaction.emoji.id)
                    else:
                        processed_emoji = reaction.emoji.name
                    logger.debug(f"RXH: Syncing {processed_emoji} to {fromMessage}")
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
                    logger.debug(f"RXH: Syncing {reaction.emoji} to {toMessage}")
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
            user = channel.guild.get_member(reaction.user_id)
            message = await channel.fetch_message(reaction.message_id)
            args = [reaction, user, "remove"]
            try:
                guild_config = self.scope_config(guild=message.guild)
                channel_config = self.scope_config(
                    guild=message.guild, channel=message.channel
                )
            except ValueError as e:
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
                logger.debug(command)
                logger.debug(args)
                if (
                    messageContent.startswith(tuple(command["trigger"]))
                    and allowCommand(command, message, user=user)
                    and command["args_num"] == 0
                ):
                    if str(user.id) in config["moderation"][
                        "blacklist-user-usage"
                    ].split(","):
                        raise Exception("Blacklisted command attempt by user")
                    logger.debug(command["function"])
                    if command["async"]:
                        return await command["function"](message, self.client, args)
                    else:
                        return await message.channel.send(
                            str(command["function"](message, self.client, args))
                        )
            for command in self.commands:
                if (
                    messageContent.startswith(tuple(command["trigger"]))
                    and allowCommand(command, message, user=user)
                    and command["args_num"] == 0
                    and command.get("remove")
                ):
                    logger.debug(command)
                    if str(user.id) in config["moderation"][
                        "blacklist-user-usage"
                    ].split(","):
                        raise Exception("Blacklisted command attempt by user")
                    logger.debug(command["function"])
                    if command["async"]:
                        return await command["function"](message, self.client, args)
                    else:
                        return await message.channel.send(
                            str(command["function"](message, self.client, args))
                        )
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"RXH[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

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

        try:
            guild_config = self.scope_config(guild=message.guild)
            channel_config = self.scope_config(
                guild=message.guild, channel=message.channel
            )
        except ValueError as e:
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
        for command in self.commands:
            if searchString.lower().startswith(
                tuple(command["trigger"])
            ) and allowCommand(command, message):
                tt = None
                if "long_run" in command:
                    if command["long_run"] == "author":
                        await message.author.trigger_typing()
                    elif command["long_run"]:
                        await message.channel.trigger_typing()
                logger.debug("[CH] Triggered " + str(command))
                args = searchString.split(" ")
                args = [item for item in args if item]
                args.pop(0)
                if str(message.author.id) in config.get("moderation", dict()).get(
                    "blacklist-user-usage", ""
                ).split(","):
                    await message.add_reaction("💔")
                    await message.channel.send(
                        "I'll only talk to you when you stop being mean to me, "
                        + message.author.display_name
                        + "!"
                    )
                    raise Exception("Blacklisted command attempt by user")
                if command["args_num"] == 0:
                    if command["async"]:
                        await command["function"](message, self.client, args)
                        break
                    else:
                        await message.channel.send(
                            str(command["function"](message, self.client, args))
                        )
                        break
                else:
                    if len(args) >= command["args_num"]:
                        if command["async"]:
                            await command["function"](message, self.client, args)
                            break
                        else:
                            await message.channel.send(
                                str(command["function"](message, self.client, args))
                            )
                            break
                    else:
                        await message.channel.send(
                            f'command "{command["trigger"][0]}" requires {command["args_num"]} argument(s) "{", ".join(command["args_name"])}"'
                        )
                        break
        if guild_config.get("hotwords"):
            for hotword in regex_cache.get(message.guild.id, []):
                if hotword["compiled_regex"].search(message.content):
                    await message.add_reaction(hotword["target_emoji"])
        if channel_config.get("regex") == "post-command" and (
            channel_config.get("regex-tyranny", "On") == "Off"
            or not message.channel.permissions_for(message.author).manage_messages
        ):
            continue_flag = await greeting.regex_filter(
                message, self.client, channel_config
            )
            if not continue_flag:
                return

    def scope_config(self, message=None, channel=None, guild=None, mutable=False):
        global config
        if guild is None:
            if channel:
                guild = channel.guild
            elif message:
                guild = message.guild
            else:
                raise ValueError("No message, channel or guild specified")
        if channel is None:
            if message:
                channel = message.channel
        if guild and type(guild) is not int:
            guild = guild.id
        if channel and type(channel) is not int:
            channel = channel.id
        if channel:
            channel = f" - {int(channel)}"
        else:
            channel = ""
        try:
            if mutable:
                return config.get(f"Guild {guild}{channel}")
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
        target = message.channel
        if (
            (not hasattr(message.author, "guild_permissions"))
            or (not message.author.guild_permissions.manage_webhooks)
            or (message.author.guild_permissions.manage_webhooks and not public)
        ):
            target = message.author
        if len(args) == 0:
            arg = None
        if (
            hasattr(message.author, "guild_permissions")
            and message.author.guild_permissions.manage_webhooks
            and len(args) > 0
            and verbose
        ):

            def command_filter(c):
                return "hidden" not in c.keys() or c["hidden"] == False

        else:

            def command_filter(c):
                return ("admin" not in c.keys() or c["admin"] == False) and (
                    "hidden" not in c.keys() or c["hidden"] == False
                )

        accessible_commands = filter(command_filter, ch.commands)
        if arg:
            keyword = " ".join(args).strip().lower()
            if keyword.startswith("!"):

                def query_filter(c):
                    for trigger in c["trigger"]:
                        if keyword in trigger:
                            return True
                    return False

            else:

                def query_filter(c):
                    for trigger in c["trigger"]:
                        if keyword in trigger:
                            return True
                    if keyword in c["description"].lower():
                        return True
                    return False

            try:
                accessible_commands = list(filter(query_filter, accessible_commands))
            except IndexError:
                accessible_commands = []
            # Set verbose if filtered list
            if len(accessible_commands) < 5:
                verbose = True
                public = True
        else:
            try:
                accessible_commands = list(accessible_commands)
            except IndexError:
                accessible_commands = []
        if target == message.author and len(accessible_commands):
            await message.add_reaction("✅")
        if len(args) > 0 and len(accessible_commands) and verbose:
            helpMessageBody = "\n".join(
                [
                    f'`{"` or `".join(command["trigger"])}`: {command["description"]}\nMinimum Arguments ({command["args_num"]}): {" ".join(command["args_name"])}'
                    for command in accessible_commands
                ]
            )
        elif len(accessible_commands) == 0:
            helpMessageBody = "No commands accessible, check your input"
        else:
            helpMessageBody = "\n".join(
                [
                    f'`{"` or `".join(command["trigger"][:2])}`: {command["description"]}'
                    for command in accessible_commands
                ]
            )
        await messagefuncs.sendWrappedMessage(helpMessageBody, target)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"HF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


def dumpconfig_function(message, client, args):
    logger.debug("Channels Loaded:")
    for channel in client.get_all_channels():
        logger.debug(str(channel.guild) + " " + str(channel))


def load_hotwords(ch):
    try:
        for guild in client.guilds:
            guild_config = self.scope_config(guild=guild)
            if guild_config.get("hotwords"):
                hotwords = ujson.loads(guild_config.get("hotwords"))
                for word in hotwords.keys():
                    target_emoji = hotwords[word]["target_emoji"]
                    if len(target_emoji) > 1:
                        target_emoji = discord.utils.get(
                            guild.emojis, name=target_emoji
                        )
                    flags = None
                    if hotwords[word]["insensitive"]:
                        flags = re.IGNORECASE
                    hotwords[word] = {
                        "target_emoji": target_emoji,
                        "regex": hotwords[word]["regex"],
                        "compiled_regex": re.compile(hotwords[word]["regex"], flags),
                    }
                regex_cache[guild.id] = hotwords.values()
    except NameError:
        pass


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
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, guild_id, key, value FROM user_preferences WHERE key = 'tupper';"
        )
        tuptuple = cur.fetchone()
        while tuptuple:
            if not ch.config.get("sync"):
                ch.config["sync"] = {}
            ignorekey = f"tupper-ignore-{tuptuple[0]}"
            if not ch.config["sync"].get(ignorekey, ""):
                ch.config["sync"][ignorekey] = ""
            ch.config["sync"][
                ignorekey
            ] += f'{ch.config["sync"][ignorekey]},{tuptuple[3]}'.strip(",")
            tuptuple = cur.fetchone()
        conn.commit()

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

    load_react_notifications(ch)
    load_tuppers(ch)

def preference_function(message, client, args):
    global ch
    if len(args) > 1:
        value = args[1]
    else:
        value = None
    return ch.user_config(message.author.id, message.guild.id, args[0], value)

def autoload(ch):
    global tag_id_as_command
    global client
    ch.add_command(
        {
            "trigger": ["!dumpconfig"],
            "function": dumpconfig_function,
            "async": False,
            "admin": True,
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
    load_user_config(ch)
    load_hotwords(ch)
