from sys import exc_info
import aiohttp
import discord
import exceptions
import io
import logging
import re
import textwrap

logger = logging.getLogger("fletcher")


def expand_guild_name(
    guild, prefix="", suffix=":", global_replace=False, case_sensitive=False
):
    global config
    acro_mapping = config.get(
        "discord-guild-expansions",
        {
            "acn": "a compelling narrative",
            "ACN": "a compelling narrative",
            "EAC": "EA Corner",
            "D": "Doissetep",
            "bocu": "Book of Creation Undone",
            "abcal": "Abandoned Castle",
        },
    )
    new_guild = guild
    for k, v in acro_mapping.items():
        regex = re.compile(f"^{prefix}{k}{suffix}|^{k}$", re.IGNORECASE)
        new_guild = regex.sub(prefix + v + suffix, new_guild)
        if not global_replace and new_guild != guild:
            logger.debug(f"Replacement found {k} -> {v}")
            if ":" in new_guild:
                new_guild = new_guild.split(":", 1)
                return new_guild[0].replace("_", " ") + ":" + new_guild[1]
            else:
                return new_guild.replace("_", " ")
    if ":" in new_guild:
        new_guild = new_guild.split(":", 1)
        return new_guild[0].replace("_", " ") + ":" + new_guild[1]

    else:
        return new_guild.replace("_", " ")


def xchannel(targetChannel, currentGuild):
    global ch
    channelLookupBy = "Name"
    toChannel = None
    toGuild = None
    if targetChannel.startswith("<#"):
        channelLookupBy = "ID"
    elif targetChannel.startswith("#"):
        channelLookupBy = "Name"
    targetChannel = targetChannel.strip("<#>!")
    logger.debug(f"XC: Channel Identifier {channelLookupBy}:{targetChannel}")
    if channelLookupBy == "Name":
        if ":" not in targetChannel and "#" not in targetChannel:
            toChannel = discord.utils.get(
                currentGuild.text_channels, name=targetChannel
            )
            toGuild = currentGuild
        else:
            targetChannel = expand_guild_name(targetChannel)
            if ":" in targetChannel:
                toTuple = targetChannel.split(":")
            elif "#" in targetChannel:
                toTuple = targetChannel.split("#")
            else:
                return None
            toGuild = discord.utils.get(ch.client.guilds, name=toTuple[0])
            if not toGuild:
                raise exceptions.DirectMessageException(
                    "Can't disambiguate channel name if in DM"
                )
            toChannel = discord.utils.get(toGuild.text_channels, name=toTuple[1])
    elif channelLookupBy == "ID":
        toChannel = ch.client.get_channel(int(targetChannel))
        toGuild = toChannel.guild
    return toChannel


async def sendWrappedMessage(msg, target, files=[], embed=None):
    msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
    last_chunk = msg_chunks.pop()
    for chunk in msg_chunks:
        await target.send(chunk)
    return await target.send(last_chunk, files=files, embed=embed)


extract_identifiers_messagelink = re.compile(
    "(?<!<)https?://(?:canary\.|ptb\.)?discord(?:app)?.com/channels/(\d+)/(\d+)/(\d+)",
    re.IGNORECASE,
)


async def teleport_function(message, client, args):
    global config
    try:
        if args[0] == "to":
            args.pop(0)
        fromChannel = message.channel
        fromGuild = message.guild
        if (
            fromChannel.id
            in config.get(section="teleport", key="fromchannel-banlist", default=[])
            and not message.author.guild_permissions.manage_webhooks
        ):
            await message.add_reaction("🚫")
            await fromChannel.send(
                "Portals out of this channel have been administratively disabled.",
                delete_after=60,
            )
            return
        toChannelName = args[0].strip()
        toChannel = None
        try:
            toChannel = xchannel(toChannelName, fromGuild)
        except AttributeError:
            await message.add_reaction("🚫")
            await fromChannel.send(
                "Cannot teleport out of a DMChannel.", delete_after=60
            )
            return
        except ValueError:
            pass
        if toChannel is None:
            await message.add_reaction("🚫")
            await fromChannel.send(
                f"Could not find channel {toChannelName}, please check for typos.",
                delete_after=60,
            )
            return
        toGuild = toChannel.guild
        if fromChannel.id == toChannel.id:
            await message.add_reaction("🚫")
            await fromChannel.send(
                "You cannot open an overlapping portal! Access denied.", delete_after=60
            )
            return
        if not toChannel.permissions_for(
            toGuild.get_member(message.author.id)
        ).send_messages:
            await message.add_reaction("🚫")
            await fromChannel.send(
                "You do not have permission to post in that channel! Access denied.",
                delete_after=60,
            )
            return
        logger.debug("Entering in " + str(fromChannel))
        try:
            fromMessage = await fromChannel.send(
                f"Opening Portal To <#{toChannel.id}> ({toGuild.name})"
            )
        except discord.Forbidden as e:
            await message.add_reaction("🚫")
            await message.author.send(
                content=f"Failed to open portal due to missing send permission on #{fromChannel.name}! Access denied."
            )
            return
        try:
            logger.debug("Exiting in " + str(toChannel))
            toMessage = await toChannel.send(
                f"Portal Opening From <#{fromChannel.id}> ({fromGuild.name})"
            )
        except discord.Forbidden as e:
            await message.add_reaction("🚫")
            await fromMessage.edit(
                content="Failed to open portal due to missing permissions! Access denied."
            )
            return
        embedTitle = f"Portal opened to #{toChannel.name}"
        if toGuild != fromGuild:
            embedTitle = f"{embedTitle} ({toGuild.name})"
        if toChannel.name == "hell":
            inPortalColor = ["red", discord.Colour.from_rgb(194, 0, 11)]
        else:
            inPortalColor = ["blue", discord.Colour.from_rgb(62, 189, 236)]
        behest = localizeName(message.author, fromGuild)
        embedPortal = discord.Embed(
            title=embedTitle,
            description=f"https://discordapp.com/channels/{toGuild.id}/{toChannel.id}/{toMessage.id} {' '.join(args[1:])}",
            color=inPortalColor[1],
        ).set_footer(
            icon_url=f"https://dorito.space/fletcher/{inPortalColor[0]}-portal.png",
            text=f"On behalf of {behest}",
        )
        if config["teleport"]["embeds"] == "on":
            tmp = await fromMessage.edit(content=None, embed=embedPortal)
        else:
            tmp = await fromMessage.edit(
                content=f"**{embedTitle}** for {behest} {' '.join(args[1:])}\n<https://discordapp.com/channels/{toGuild.id}/{toChannel.id}/{toMessage.id}>"
            )
        embedTitle = f"Portal opened from #{fromChannel.name}"
        behest = localizeName(message.author, toGuild)
        if toGuild != fromGuild:
            embedTitle = f"{embedTitle} ({fromGuild.name})"
        embedPortal = discord.Embed(
            title=embedTitle,
            description=f"https://discordapp.com/channels/{fromGuild.id}/{fromChannel.id}/{fromMessage.id} {' '.join(args[1:])}",
            color=discord.Colour.from_rgb(194, 64, 11),
        ).set_footer(
            icon_url="https://dorito.space/fletcher/orange-portal.png",
            text=f"On behalf of {behest}",
        )
        if config["teleport"]["embeds"] == "on":
            tmp = await toMessage.edit(content=None, embed=embedPortal)
        else:
            tmp = await toMessage.edit(
                content=f"**{embedTitle}** for {behest} {' '.join(args[1:])}\n<https://discordapp.com/channels/{fromGuild.id}/{fromChannel.id}/{fromMessage.id}>"
            )
        try:
            if "snappy" in config["discord"] and config["discord"]["snappy"]:
                await message.delete()
            return
        except discord.Forbidden:
            raise Exception("Couldn't delete portal request message")
        return f"Portal opened for {message.author} to {args[0]}"
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TPF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


extract_links = re.compile("(?<!<)((https?|ftp):\/\/|www\.)(\w.+\w\W?)", re.IGNORECASE)
extract_previewable_link = re.compile(
    "(?<!<)(https?://www1.flightrising.com/(?:dgen/preview/dragon|dgen/dressing-room/scry|scrying/predict)\?[^ ]+|https?://todo.sr.ht/~nova/fletcher/\d+|https?://vine.co/v/\w+)",
    re.IGNORECASE,
)


async def preview_messagelink_function(message, client, args):
    try:
        in_content = None
        if args is not None and len(args) >= 1 and args[0].isdigit():
            in_content = await messagelink_function(
                message, client, [args[0], "INTPROC"]
            )
        else:
            in_content = message.content
        # 'https://discord.com/channels/{}/{}/{}'.format(message.channel.guild.id, message.channel.id, message.id)
        try:
            urlParts = extract_identifiers_messagelink.search(in_content).groups()
        except AttributeError:
            urlParts = []
        try:
            previewable_parts = extract_previewable_link.search(in_content).groups()
        except AttributeError:
            previewable_parts = []
        attachments = []
        embed = None
        content = None
        if len(urlParts) == 3:
            guild_id = int(urlParts[0])
            channel_id = int(urlParts[1])
            message_id = int(urlParts[2])
            guild = client.get_guild(guild_id)
            if guild is None:
                logger.info("PMF: Fletcher is not in guild ID " + str(guild_id))
                await message.author.send(
                    f"Tried unrolling message link in your message <https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}>, but I do not have permissions for targetted server. Please wrap links in `<>` if you don't want me to try to unroll them, or ask the server owner to grant me Read Message History to unroll links to messages there successfully (https://man.sr.ht/~nova/fletcher/permissions.md for details)"
                )
                return
            channel = guild.get_channel(channel_id)
            target_message = await channel.fetch_message(message_id)
            # created_at is naîve, but specified as UTC by Discord API docs
            sent_at = target_message.created_at.strftime("%B %d, %Y %I:%M%p UTC")
            content = target_message.content
            if content == "":
                content = "*No Text*"
            if (
                message.guild
                and message.guild.id == guild_id
                and message.channel.id == channel_id
            ):
                content = "Message from __{}__ sent at {}:\n>>> {}".format(
                    target_message.author.name, sent_at, content
                )
            elif message.guild and message.guild.id == guild_id:
                content = "Message from __{}__ sent in <#{}> at {}:\n>>> {}".format(
                    target_message.author.name, channel_id, sent_at, content
                )
            else:
                content = "Message from __{}__ sent in **#{}** ({}) at {}:\n>>> {}".format(
                    target_message.author.name,
                    channel.name,
                    guild.name,
                    sent_at,
                    content,
                )
            if target_message.channel.is_nsfw() and not (
                type(message.channel) is discord.DMChannel or message.channel.is_nsfw()
            ):
                content = extract_links.sub(r"<\g<0>>", content)
            if len(target_message.attachments) > 0:
                plural = ""
                if len(target_message.attachments) > 1:
                    plural = "s"
                content = (
                    content
                    + "\n "
                    + str(len(target_message.attachments))
                    + " file"
                    + plural
                    + " attached"
                )
                if target_message.channel.is_nsfw() and (
                    type(message.channel) is discord.DMChannel
                    or not message.channel.is_nsfw()
                ):
                    content = content + " from an R18 channel."
                    for attachment in target_message.attachments:
                        content = content + "\n• <" + attachment.url + ">"
                else:
                    for attachment in target_message.attachments:
                        logger.debug("Syncing " + attachment.filename)
                        attachment_blob = io.BytesIO()
                        await attachment.save(attachment_blob)
                        attachments.append(
                            discord.File(attachment_blob, attachment.filename)
                        )

                if args is not None and len(args) >= 1 and args[0].isdigit():
                    content = (
                        content
                        + f"\nSource: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                    )
        elif len(previewable_parts):
            if "flightrising" in previewable_parts[0]:
                import swag

                attachments = [
                    await swag.flightrising_function(
                        message, client, [previewable_parts[0], "INTPROC"]
                    )
                ]
                content = "FlightRising Preview"
            elif "todo.sr.ht" in previewable_parts[0]:
                import versionutils

                embed = await versionutils.buglist_function(
                    message, client, [previewable_parts[0].split("/")[-1], "INTPROC"]
                )
                content = "Todo Preview"
            elif "vine" in previewable_parts[0]:
                import swag

                attachments = [
                    await swag.vine_function(
                        message,
                        client,
                        [previewable_parts[0].split("/")[-1], "INTPROC"],
                    )
                ]
                content = "Vine Preview"
        # TODO 🔭 to preview?
        if content:
            return await sendWrappedMessage(
                content, message.channel, files=attachments, embed=embed
            )
    except discord.Forbidden as e:
        await message.author.send(
            f"Tried unrolling message link in your message https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}, but I do not have permissions for that channel. Please wrap links in `<>` if you don't want me to try to unroll them, or ask the channel owner to grant me Read Message History to unroll links to messages there successfully (https://man.sr.ht/~nova/fletcher/permissions.md for details)"
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("PMF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        # better for there to be no response in that case


async def messagelink_function(message, client, args):
    global config
    try:
        msg = None
        for channel in message.channel.guild.text_channels:
            try:
                msg = await channel.fetch_message(int(args[0]))
                break
            except discord.Forbidden as e:
                pass
            except discord.NotFound as e:
                pass
        if msg and not (len(args) == 2 and args[1] == "INTPROC"):
            await message.channel.send(
                "Message link on behalf of {}: https://discord.com/channels/{}/{}/{}".format(
                    message.author, msg.channel.guild.id, msg.channel.id, msg.id
                )
            )
            if "snappy" in config["discord"] and config["discord"]["snappy"]:
                await message.delete()
            return
        elif msg:
            return "https://discord.com/channels/{}/{}/{}".format(
                msg.channel.guild.id, msg.channel.id, msg.id
            )
        else:
            return await message.channel.send("Message not found", delete_after=60)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


url_search = re.compile(
    "(?:(?:[\w]+:)?//)?(?:(?:[\d\w]|%[a-fA-f\d]{2,2})+(?::(?:[\d\w]|%[a-fA-f\d]{2,2})+)?@)?(?:[\d\w][-\d\w]{0,253}[\d\w]\.)+[\w]{2,63}(?::[\d]+)?(?:/(?:[-+_~.\d\w]|%[a-fA-f\d]{2,2})*)*(?:\?(?:&?(?:[-+_~.\d\w]|%[a-fA-f\d]{2,2})=?)*)?(?:#(?:[-+_~.\d\w]|%[a-fA-f\d]{2,2})*)?"
)


async def bookmark_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            if str(args[0].emoji) == "🔖":
                bookmark_message = "Bookmark to conversation in #{} ({}) https://discord.com/channels/{}/{}/{} via reaction to {}".format(
                    message.channel.name,
                    message.guild.name,
                    message.guild.id,
                    message.channel.id,
                    message.id,
                    message.content,
                )
                await sendWrappedMessage(bookmark_message, args[1])
                urls = url_search.findall(message.content)
                if not len(urls):
                    return
                pocket_consumer_key = ch.config.get(
                    section="pocket", key="consumer_key"
                )
                if not pocket_consumer_key:
                    logger.debug("No pocket_consumer_key set")
                    return
                pocket_access_token = ch.user_config(
                    args[1].id, None, "pocket_access_token"
                )
                if not pocket_access_token:
                    return
                for url in url_search.findall(message.content):
                    logger.debug(f"Pocketing {url}")
                    async with aiohttp.ClientSession() as session:
                        params = aiohttp.FormData()
                        params.add_field("title", message.content)
                        params.add_field("url", url)
                        params.add_field("consumer_key", pocket_consumer_key)
                        params.add_field("access_token", pocket_access_token)
                        async with session.post(
                            "https://getpocket.com/v3/add", data=params
                        ):
                            return
            elif str(args[0].emoji) == "🔗":
                return await args[1].send(
                    "https://discord.com/channels/{}/{}/{}".format(
                        message.guild.id, message.channel.id, message.id
                    )
                )
        else:
            await sendWrappedMessage(
                "Bookmark to conversation in #{} ({}) https://discord.com/channels/{}/{}/{} {}".format(
                    message.channel.recipient
                    if type(message.channel) is discord.DMChannel
                    else message.channel.name,
                    message.guild.name,
                    message.guild.id,
                    message.channel.id,
                    message.id,
                    " ".join(args),
                ),
                message.author,
            )
            return await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("BMF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def paste_function(message, client, args):
    try:
        async for historical_message in message.author.history(
            oldest_first=False, limit=10
        ):
            if historical_message.author == client.user:
                paste_content = historical_message.content
                attachments = []
                if len(historical_message.attachments) > 0:
                    for attachment in historical_message.attachments:
                        logger.debug("Syncing " + attachment.filename)
                        attachment_blob = io.BytesIO()
                        await attachment.save(attachment_blob)
                        attachments.append(
                            discord.File(attachment_blob, attachment.filename)
                        )
                paste_message = await message.channel.send(
                    paste_content, files=attachments
                )
                await preview_messagelink_function(paste_message, client, args)
                return
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("PF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def subscribe_function(message, client, args):
    global ch
    try:
        guild_config = ch.scope_config(guild=message.guild, mutable=True)
        if not guild_config.get("subscribe"):
            guild_config["subscribe"] = {}
        if not guild_config["subscribe"].get(message.id):
            guild_config["subscribe"][message.id] = []
        if len(args) == 3 and type(args[1]) is discord.Member:
            cur = conn.cursor()
            if args[2] != "remove":
                cur.execute(
                    "INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, 'subscribe', %s) ON CONFLICT DO NOTHING;",
                    [args[1].id, message.guild.id, str(message.id)],
                )
                conn.commit()
                if args[1].id not in guild_config["subscribe"][message.id]:
                    guild_config["subscribe"][message.id].append(args[1].id)
                await args[1].send(
                        f"By reacting with {args[0]}, you subscribed to reaction on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} ({message.channel.name}:{message.guild.name}). You can unreact to unsubscribe from these notifications."
                )
            else:
                cur.execute(
                    "DELETE FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = 'subscribe' AND value = %s;",
                    [args[1].id, message.guild.id, str(message.id)],
                )
                conn.commit()
                if args[1].id in guild_config["subscribe"][message.id]:
                    guild_config["subscribe"][message.id].remove(args[1].id)
                await args[1].send(
                        f"By unreacting with {args[0]}, you unsubscribed from reactions on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} ({message.channel.name}:{message.guild.name})."
                )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SUBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def localizeName(user, guild):
    localized = guild.get_member(user.id)
    if localized is None:
        localizeName = user.name
    else:
        localized = localized.display_name
    return localized


sanitize_font = re.compile(r"[^❤A-Za-z0-9 /]")

# Register this module's commands
def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!teleport", "!portal", "!tp"],
            "function": teleport_function,
            "async": True,
            "args_num": 1,
            "args_name": ["string"],
            "description": "Create a link bridge to another channel",
        }
    )
    ch.add_command(
        {
            "trigger": ["!message"],
            "function": messagelink_function,
            "async": True,
            "args_num": 1,
            "args_name": ["string"],
            "description": "Create a link to the message with ID `!message XXXXXX`",
        }
    )
    ch.add_command(
        {
            "trigger": ["!preview"],
            "function": preview_messagelink_function,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "long_run": True,
            "args_name": ["string"],
            "description": "Retrieve message body by link (used internally to unwrap message links in chat)",
        }
    )
    ch.add_command(
        {
            "trigger": ["🔖", "🔗", "!bookmark"],
            "function": bookmark_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "DM the user a bookmark to the current place in conversation",
        }
    )
    ch.add_command(
        {
            "trigger": ["!paste"],
            "function": paste_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Paste last copied link",
        }
    )
    ch.add_command(
        {
            "trigger": ["📡"],
            "function": subscribe_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Subscribe to reaction notifications on this message",
        }
    )
    ch.add_command(
        {
            "trigger": ["📡"],
            "function": subscribe_function,
            "async": True,
            "remove": True,
            "args_num": 0,
            "args_name": [],
            "description": "Subscribe to reaction notifications on this message",
        }
    )


async def autounload(ch):
    pass
