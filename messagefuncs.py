from sys import exc_info
import commandhandler
import asyncio
import aiohttp
import netcode
import discord
import exceptions
import io
import logging
import re
import textwrap
import traceback
from sentry_sdk import configure_scope
import pytz
import AO3

logger = logging.getLogger("fletcher")


async def add_reaction(message, reaction):
    if type(reaction) is list:
        reactions = []
        for r in reaction:
            reactions.append(await message.add_reaction(r))
        return reactions
    else:
        return await message.add_reaction(reaction)


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
    targetChannel = targetChannel.lstrip()
    targetChannel = targetChannel.replace(":#", ":")
    if targetChannel.startswith("<#"):
        channelLookupBy = "ID"
    elif targetChannel.startswith("#"):
        channelLookupBy = "Name"
    targetChannel = targetChannel.strip("<#>!")
    logger.debug(f"XC: Channel Identifier {channelLookupBy}:{targetChannel}")
    if channelLookupBy == "Name":
        if ":" not in targetChannel and "#" not in targetChannel:
            toChannel = discord.utils.get(
                [*currentGuild.text_channels, *currentGuild.voice_channels],
                name=targetChannel,
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
            if toGuild is None:
                toGuild = discord.utils.find(
                    lambda m: m.name.lower() == toTuple[0].lower(), ch.client.guilds
                )
            if toGuild is None:
                raise exceptions.DirectMessageException(
                    "Can't disambiguate channel name if in DM"
                )
            toChannel = discord.utils.find(
                lambda channel: channel.name == toTuple[1]
                or str(channel.id) == toTuple[1],
                [*toGuild.text_channels, *toGuild.voice_channels],
            )
    elif channelLookupBy == "ID":
        toChannel = ch.client.get_channel(int(targetChannel))
        toGuild = toChannel.guild
    return toChannel


async def sendWrappedMessage(
    msg=None,
    target=None,
    files=[],
    embed=None,
    delete_after=None,
    allowed_mentions=discord.AllowedMentions(everyone=False),
    wrap_as_embed=False,
    current_user_id=None,
    **kwargs,
):
    with configure_scope() as scope:
        current_user_id = current_user_id or scope._user["id"]
        # current_message_id = scope._tags.get('message_id')
        # current_channel_id = scope._tags.get('channel_id')
        # current_guild_id = scope._tags.get('guild_id')
        chunk = None
        if msg and not wrap_as_embed:
            if (
                str(msg).startswith("||")
                and str(msg).endswith("||")
                and len(msg) > 2000
            ):
                msg_chunks = [
                    f"||{chunk}||"
                    for chunk in textwrap.wrap(
                        str(msg)[2:-2], 1996, replace_whitespace=False
                    )
                ]
            elif (
                str(msg).startswith("```")
                and str(msg).endswith("```")
                and len(msg) > 2000
            ):
                msg_chunks = [
                    f"```{chunk}```"
                    for chunk in textwrap.wrap(
                        str(msg)[3:-3], 1994, replace_whitespace=False
                    )
                ]
            else:
                msg_chunks = textwrap.wrap(str(msg), 2000, replace_whitespace=False)
            last_chunk = msg_chunks.pop()
            for chunk in msg_chunks:
                sent_message = await target.send(
                    chunk,
                    delete_after=delete_after,
                    allowed_mentions=allowed_mentions,
                    **kwargs,
                )
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO attributions (author_id, from_message, from_channel, from_guild, message, channel, guild) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                    [
                        current_user_id,
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
        else:
            last_chunk = None
        if wrap_as_embed:
            embed_chunks = textwrap.wrap(str(msg), 6000, replace_whitespace=False)
            last_chunk = embed_chunks.pop()
            for msg in embed_chunks:
                embed = discord.Embed().set_footer(
                    icon_url=client.user.avatar_url, text=client.user.name
                )
                msg_chunks = textwrap.wrap(msg, 1024, replace_whitespace=False)
                for hunk in msg_chunks:
                    embed.add_field(name="\u1160", value=hunk, inline=False)
                sent_message = await target.send(
                    chunk,
                    embed=embed,
                    delete_after=delete_after,
                    allowed_mentions=allowed_mentions,
                    **kwargs,
                )
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO attributions (author_id, from_message, from_channel, from_guild, message, channel, guild) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                    [
                        current_user_id,
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
            embed = discord.Embed().set_footer(
                icon_url=client.user.display_avatar, text=client.user.name
            )
            msg_chunks = textwrap.wrap(msg, 1024, replace_whitespace=False)
            for hunk in msg_chunks:
                embed.add_field(name="\u1160", value=hunk, inline=False)
        sent_message = await target.send(
            last_chunk,
            files=files,
            embed=embed,
            delete_after=delete_after,
            allowed_mentions=allowed_mentions,
            **kwargs,
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO attributions (author_id, from_message, from_channel, from_guild, message, channel, guild) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
            [
                current_user_id,
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
        return sent_message


extract_identifiers_messagelink = re.compile(
    r"(?<!<)https?://(?:canary\.|ptb\.)?discord(?:app)?.com/channels/(\d+)/(\d+)/(\d+)",
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
            + (config.get(guild=fromGuild, key="teleport-fromchannel-banlist") or [])
            and not message.author.guild_permissions.manage_webhooks
        ):
            await message.add_reaction("🚫")
            await sendWrappedMessage(
                "Portals out of this channel have been administratively disabled.",
                fromChannel,
                delete_after=60,
            )
            return
        toChannelName = args[0].strip()
        toChannel = None
        try:
            toChannel = xchannel(toChannelName, fromGuild)
        except AttributeError as e:
            await message.add_reaction("🚫")
            await sendWrappedMessage(
                "Cannot teleport out of a DMChannel.", fromChannel, delete_after=60
            )
            return
        except ValueError:
            pass
        if toChannel is None:
            await message.add_reaction("🚫")
            await sendWrappedMessage(
                f"Could not find channel {toChannelName}, please check for typos.",
                fromChannel,
                delete_after=60,
            )
            return
        toGuild = toChannel.guild
        if fromChannel.id == toChannel.id:
            await message.add_reaction("🚫")
            await sendWrappedMessage(
                "You cannot open an overlapping portal! Access denied.",
                fromChannel,
                delete_after=60,
            )
            return
        if len(toGuild.members) == 1:
            await toGuild.chunk()
        if not toChannel.permissions_for(
            toGuild.get_member(message.author.id)
        ).send_messages:
            await message.add_reaction("🚫")
            await sendWrappedMessage(
                "You do not have permission to post in that channel! Access denied.",
                fromChannel,
                delete_after=60,
            )
            return
        logger.debug("Entering in " + str(fromChannel))
        try:
            fromMessage = await sendWrappedMessage(
                f"Opening Portal To <#{toChannel.id}> ({toGuild.name})", fromChannel
            )
        except discord.Forbidden as e:
            await message.add_reaction("🚫")
            await sendWrappedMessage(
                f"Failed to open portal due to missing send permission on #{fromChannel.name}! Access denied.",
                message.author,
            )
            return
        try:
            logger.debug(f"Exiting in {toChannel}")
            toMessage = await sendWrappedMessage(
                f"Portal Opening From <#{fromChannel.id}> ({fromGuild.name})", toChannel
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
            description=f"[{embedTitle}](https://discordapp.com/channels/{toGuild.id}/{toChannel.id}/{toMessage.id}) {' '.join(args[1:])}",
            color=inPortalColor[1],
        ).set_footer(
            icon_url=f"https://dorito.space/fletcher/{inPortalColor[0]}-portal.png",
            text=f"On behalf of {behest}",
        )
        if ch.config.get(key="teleports", guild=fromGuild) == "embed":
            tmp = await fromMessage.edit(
                content=f"<https://discordapp.com/channels/{toGuild.id}/{toChannel.id}/{toMessage.id}>",
                embed=embedPortal,
            )
        else:
            tmp = await fromMessage.edit(
                content=f"**{embedTitle}** for {behest} {' '.join(args[1:])}\n<https://discordapp.com/channels/{toGuild.id}/{toChannel.id}/{toMessage.id}>"
            )
        embedTitle = f"Portal opened from #{fromChannel.name}"
        behest = localizeName(message.author, toGuild)
        if toGuild != fromGuild:
            embedTitle = f"{embedTitle} ({fromGuild.name})"
        embedPortal = discord.Embed(
            description=f"[{embedTitle}](https://discordapp.com/channels/{fromGuild.id}/{fromChannel.id}/{fromMessage.id}) {' '.join(args[1:])}",
            color=discord.Colour.from_rgb(194, 64, 11),
        ).set_footer(
            icon_url="https://dorito.space/fletcher/orange-portal.png",
            text=f"On behalf of {behest}",
        )
        if ch.config.get(key="teleports", guild=fromGuild) == "embed":
            tmp = await toMessage.edit(
                content=f"<https://discordapp.com/channels/{fromGuild.id}/{fromChannel.id}/{fromMessage.id}>",
                embed=embedPortal,
            )
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
        logger.debug(traceback.format_exc())
        logger.error(f"TPF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


extract_links = re.compile("(?<!<)((https?|ftp):\/\/|www\.)(\w.+\w\W?)", re.IGNORECASE)
extract_previewable_link = re.compile(
    r"(?<!<)(https?://www1.flightrising.com/(?:dragon/\d+|dgen/preview/dragon|dgen/dressing-room/scry|scrying/predict)(?:\?[^ ]+)?|https?://todo.sr.ht/~nova/fletcher/\d+|https?://vine.co/v/\w+|https?://www.azlyrics.com/lyrics/.*.html|https?://www.scpwiki.com[^ ]*|https?://www.tiktok.com/@[^ ]*/video/\d*|https?://vm.tiktok.com/[^ ]*|https?://www.instagram.com/p/[^/]*/|https://media.discordapp.net/attachments/.*?.mp4|https?://arxiv.org/pdf/[0-9.]*[0-9](?:.pdf)?|https://www.oyez.org/cases/\d+/\d+-\d+|http://bash.org/\?\d+)",
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
                if not ch.user_config(
                    message.author.id,
                    message.guild.id if message.guild else None,
                    "no_unroll_notify",
                    False,
                ):
                    await sendWrappedMessage(
                        f"Tried unrolling message link in your message <https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}>, but I do not have permissions for targetted server. Please wrap links in `<>` if you don't want me to try to unroll them, or ask the server owner to grant me Read Message History to unroll links to messages there successfully (https://man.sr.ht/~nova/fletcher/permissions.md for details). To supress this message in future, use the command `!preference no_unroll_notify True`.",
                        message.author,
                    )
                return
            channel = guild.get_channel(channel_id) or guild.get_thread(channel_id)
            if not (
                guild.get_member(message.author.id)
                and channel.permissions_for(
                    guild.get_member(message.author.id)
                ).read_message_history
            ):
                return
            target_message = await channel.fetch_message(message_id)
            # created_at is naîve, but specified as UTC by Discord API docs
            sent_at = f"<t:{int(target_message.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.utc).timestamp())}:R>"
            content = target_message.content
            if target_message.author.bot and len(target_message.embeds):
                embed = target_message.embeds[0]
            if content == "":
                # content = "*No Text*"
                pass
            else:
                content = ">>> " + content
            if (
                message.guild
                and message.guild.id == guild_id
                and message.channel.id == channel_id
            ):
                content = "@__{}__ at {}:\n{}".format(
                    target_message.author.name, sent_at, content
                )
            elif message.guild and message.guild.id == guild_id:
                content = "@__{}__ in <#{}> at {}:\n{}".format(
                    target_message.author.name, channel_id, sent_at, content
                )
            else:
                content = "@__{}__ in **#{}** ({}) at {}:\n{}".format(
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
                if target_message.channel.is_nsfw() and (
                    type(message.channel) is discord.DMChannel
                    or not message.channel.is_nsfw()
                ):
                    content = (
                        content
                        + "\n "
                        + str(len(target_message.attachments))
                        + " file"
                        + plural
                        + " attached"
                    )
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

                preview_tup = await swag.flightrising_function(
                    message, client, [previewable_parts[0], "INTPROC"]
                )
                attachments = [preview_tup[0]]
                content = preview_tup[1]
            elif "bash.org" in previewable_parts[0]:
                import swag

                content = await swag.bash_preview(
                    message, client, [previewable_parts[0].split("?")[1], "INTPROC"]
                )
            elif "media.discordapp.net" in previewable_parts[0]:
                content = previewable_parts[0].replace(
                    "media.discordapp.net", "cdn.discordapp.com"
                )
            elif "//www.oyez.org" in previewable_parts[0]:
                async with session.get(
                    f"https://api.oyes.org/{previewable_parts[0].split('org/')[1]}?labels=true",
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Origin": "https://www.oyez.org",
                        "Connection": "keep-alive",
                        "Referer": "https://www.oyez.org/",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-site",
                    },
                ) as resp:
                    data = await resp.json()
                    content = f"""
{data.name} - {data.description} (find at Justia {data.justia_url}
"""
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
            elif "tiktok.com" in previewable_parts[0]:
                import swag

                content = "TikTok Preview"
                with message.channel.typing():
                    attachments = [
                        await swag.tiktok_function(
                            message,
                            client,
                            [previewable_parts[0], "INTPROC"],
                        )
                    ]
            elif "arxiv.org" in previewable_parts[0]:
                async with session.get(
                    previewable_parts[0].replace("pdf", "abs", 1).strip(".pdf")
                ) as resp:
                    text = await resp.text()
                    content = f"""
__{re.search(r'name="citation_title" content="([^"]*?)"', text).group(1)}__
{", ".join(re.findall(r'name="citation_author" content="([^"]*?)"', text))}
<{re.search(r'name="citation_pdf_url" content="([^"]*?)"', text).group(1)}>
>>> {re.search(r'name="citation_abstract" content="([^"]*?)"', text, re.MULTILINE).group(1).strip()}
"""
            elif "instagram.com" in previewable_parts[0]:
                content = "Instagram Preview"
                async with session.get(
                    "https://graph.facebook.com/v10.0/instagram_oembed",
                    params={
                        "access_token": config.get(
                            section="facebook", key="access_token"
                        ),
                        "url": previewable_parts[0],
                    },
                ) as resp:
                    json = await resp.json()
                    logger.debug(await resp.text())
                    attachments = [
                        discord.File(
                            await netcode.simple_get_image(json["thumbnail_url"]),
                            "instagram.jpg",
                        )
                    ]
            elif "azlyrics.com" in previewable_parts[0]:
                import swag

                content = await swag.azlyrics_function(
                    message,
                    client,
                    [previewable_parts[0], "INTPROC"],
                )
            elif "scpwiki.com" in previewable_parts[0]:
                import swag

                embed = await swag.scp_function(
                    message,
                    client,
                    [previewable_parts[0], "INTPROC"],
                )
                content = "SCP Preview"
        # TODO 🔭 to preview?
        if content:
            try:
                if message.author.id == client.user.id:
                    await message.edit(content=message.content + "\n" + content)
                    return
            except:
                pass
            if not all(
                [type(attachment) is discord.File for attachment in attachments]
            ):
                return
            try:
                outMessage = await sendWrappedMessage(
                    content,
                    message.channel,
                    files=attachments,
                    embed=embed,
                    current_user_id=message.author.id,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                return
            reaction = client.get_emoji(787460478527078450)
            try:
                await outMessage.add_reaction(reaction)
            except:
                try:
                    reaction = "❌"
                    await outMessage.add_reaction(reaction)
                except:
                    pass
            await asyncio.sleep(60)
            try:
                outMessage.remove_reaction(reaction, client.user)
            except:
                pass
            return outMessage
    except discord.Forbidden as e:
        if not ch.user_config(
            message.author.id,
            message.guild.id if message.guild else None,
            "no_unroll_notify",
            False,
        ):
            await sendWrappedMessage(
                f"Tried unrolling message link in your message https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}, but I do not have permissions for that channel. Please wrap links in `<>` if you don't want me to try to unroll them, or ask the channel owner to grant me Read Message History to unroll links to messages there successfully (https://man.sr.ht/~nova/fletcher/permissions.md for details). To supress this message in future, use the command `!preference no_unroll_notify True`.",
                message.author,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug(traceback.format_exc())
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
            await sendWrappedMessage(
                f"Message link on behalf of {message.author}: https://discord.com/channels/{msg.channel.guild.id}/{msg.channel.id}/{msg.id}",
                message.channel,
            )
            if "snappy" in config["discord"] and config["discord"]["snappy"]:
                await message.delete()
            return
        elif msg:
            return "https://discord.com/channels/{}/{}/{}".format(
                msg.channel.guild.id, msg.channel.id, msg.id
            )
        else:
            return await sendWrappedMessage(
                "Message not found", message.channel, delete_after=60
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


url_search = re.compile(
    "(?:(?:[\w]+:)?//)?(?:(?:[\d\w]|%[a-fA-f\d]{2,2})+(?::(?:[\d\w]|%[a-fA-f\d]{2,2})+)?@)?(?:[\d\w][-\d\w]{0,253}[\d\w]\.)+[\w]{2,63}(?::[\d]+)?(?:/(?:[-+_~.\d\w]|%[a-fA-f\d]{2,2})*)*(?:\?(?:&?(?:[-+_~.\d\w]|%[a-fA-f\d]{2,2})=?)*)?(?:#(?:[-+_~.\d\w]|%[a-fA-f\d]{2,2})*)?"
)


async def markdown_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            await sendWrappedMessage(f"```md\n{message.content[:1992]}```", args[1])
            if len(message.content) > 1992:
                await sendWrappedMessage(f"```md\n{message.content[1992:]}```", args[1])
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MDF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


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
                pocket_access_token = ch.user_config(
                    args[1].id, None, "pocket_access_token"
                )
                if pocket_access_token and len(urls):
                    pocket_consumer_key = ch.config.get(
                        section="pocket", key="consumer_key"
                    )
                    if pocket_consumer_key:
                        for url in urls:
                            logger.debug(f"Pocketing {url}")
                            params = aiohttp.FormData()
                            params.add_field("title", message.content)
                            params.add_field("url", url)
                            params.add_field("consumer_key", pocket_consumer_key)
                            params.add_field("access_token", pocket_access_token)
                            async with session.post(
                                "https://getpocket.com/v3/add", data=params
                            ):
                                pass
                trello_bookmark_list = ch.user_config(
                    args[1].id, None, "trello_bookmark_list"
                )
                if trello_bookmark_list:
                    trello_key = ch.config.get(section="trello", key="client_key")
                    trello_uat = ch.user_config(
                        args[1].id,
                        message.guild.id if message.guild else None,
                        "trello_access_token",
                        allow_global_substitute=True,
                    )
                    if trello_key and trello_uat:
                        async with session.post(
                            "https://api.trello.com/1/cards",
                            json={
                                "idList": trello_bookmark_list,
                                "desc": message.clean_content,
                                "urlSource": message.jump_url,
                            },
                            headers={
                                "Authorization": f'OAuth oauth_consumer_key="{trello_key}", oauth_token="{trello_uat}"'
                            },
                        ) as resp:
                            pass
                ao3_session = None
                for url in filter(lambda url: "archiveofourown.org/works" in url, urls):
                    if (
                        ch.user_config(args[1].id, None, "ao3-username")
                        and ch.user_config(args[1].id, None, "ao3-password")
                        and not ao3_session
                    ):
                        ao3_session = AO3.Session(
                            ch.user_config(args[1].id, None, "ao3-username"),
                            ch.user_config(args[1].id, None, "ao3-password"),
                        )
                        ao3_session.refresh_auth_token()
                    if ao3_session:
                        work = AO3.Work(
                            AO3.utils.workid_from_url(url), session=ao3_session
                        )
                        work.bookmark(
                            notes=f'<a href="{message.jump_url}">Source</a>',
                            private=config.normalize_booleans(
                                ch.user_config(
                                    args[1].id, None, "ao3-bookmark-private", True
                                )
                            ),
                        )
            elif str(args[0].emoji) == "🔗":
                return await sendWrappedMessage(
                    f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}",
                    args[1],
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
                paste_message = await sendWrappedMessage(
                    paste_content, message.channel, files=attachments
                )
                if not paste_content.startswith("OCR of "):
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
                ch.add_message_reaction_remove_handler(
                    [message.id],
                    {
                        "trigger": [""],  # empty string: a special catch-all trigger
                        "function": subscribe_send_function,
                        "exclusive": False,
                        "async": True,
                        "args_num": 0,
                        "args_name": [],
                        "description": "Notify on emoji send",
                    },
                )
                ch.add_message_reaction_handler(
                    [message.id],
                    commandhandler.Command(
                        function=subscribe_send_function,
                        exclusive=False,
                        sync=False,
                        description="Notify on emoji send",
                    ),
                )
                ch.add_message_reply_handler(
                    [message.id],
                    {
                        "trigger": [""],  # empty string: a special catch-all trigger
                        "function": subscribe_send_function,
                        "exclusive": False,
                        "async": True,
                        "args_num": 0,
                        "args_name": [],
                        "description": "Notify on emoji send",
                    },
                )
                await sendWrappedMessage(
                    f"By reacting with {args[0].emoji}, you subscribed to reactions on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} ({message.channel.name}:{message.guild.name}). You can unreact to unsubscribe from these notifications.",
                    args[1],
                )
            else:
                cur.execute(
                    "DELETE FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = 'subscribe' AND value = %s;",
                    [args[1].id, message.guild.id, str(message.id)],
                )
                conn.commit()
                if args[1].id in guild_config["subscribe"][message.id]:
                    guild_config["subscribe"][message.id].remove(args[1].id)
                await sendWrappedMessage(
                    f"By unreacting with {args[0].emoji}, you unsubscribed from reactions on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} ({message.channel.name}:{message.guild.name}).",
                    args[1],
                )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SUBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def subscribe_send_function(message, client, args):
    try:
        guild_config = ch.scope_config(guild=message.guild)
        if len(args) == 3 and type(args[1]) is discord.Member and args[2] == "add":
            user = args[1]
            content = f"{user.display_name} ({user.name}#{user.discriminator}) reacting with {args[0].emoji} to {message.jump_url}"
        elif len(args) == 3 and type(args[1]) is discord.Member and args[2] == "remove":
            user = args[1]
            content = f"{user.display_name} ({user.name}#{user.discriminator}) unreacting with {args[0].emoji} on {message.jump_url}"
        elif len(args) == 3 and type(args[1]) is discord.Member and args[2] == "reply":
            user = args[1]
            content = f"{user.display_name} ({user.name}#{user.discriminator}) replying to {args[0].jump_url} with\n> {message.content}\n({message.jump_url})"
        for user in filter(
            None,
            [
                message.guild.get_member(user_id)
                for user_id in guild_config.get("subscribe", {}).get(message.id)
            ],
        ):
            preview_message = await sendWrappedMessage(
                content,
                user,
            )
            await preview_message.edit(suppress=True)
            await preview_messagelink_function(preview_message, client, None)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def localizeName(user, guild):
    localized = guild.get_member(user.id)
    if localized is None:
        localizeName = user.name
    else:
        localized = localized.display_name
    return localized


sanitize_font = re.compile(r"[^❤A-Za-z0-9 /]")


async def archive_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            urls = url_search.findall(message.content)
            if not len(urls):
                return
            for url in urls:
                logger.debug(f"Archiving {url}")
                async with session.get(f"https://web.archive.org/save/{url}") as resp:
                    await sendWrappedMessage(
                        f"Archived URL <{url}> at <{resp.links['memento']['url']}>",
                        args[1],
                    )
            return await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("ARF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def star_function(message, client, args):
    try:
        threshold = ch.config.get(
            key="starboard-threshold",
            channel=message.channel.id,
            guild=message.guild.id,
            use_guild_as_channel_fallback=True,
        )
        channel = ch.config.get(
            key="starboard-channel",
            channel=message.channel.id,
            guild=message.guild.id,
            use_guild_as_channel_fallback=True,
        )
        channel = (
            discord.utils.get(client.guilds, name=channel)
            if type(channel) is str
            else client.get_channel(int(channel))
        )
        if threshold is None or channel is None:
            return
        if discord.utils.get(message.reactions, emoji="⭐").count == threshold:
            preview_message = await sendWrappedMessage(message.jump_url, target=channel)
            await preview_messagelink_function(preview_message, client, None)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("STARF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def translate_function(message, client, args):
    try:
        base_url = ch.config.get(section="translate", key="server_url")
        endpoint = ch.config.get(section="translate", key="endpoint")
        placeholder = await sendWrappedMessage(
            f"Translating...", target=message.channel
        )
        async with session.post(
            f"{base_url}{endpoint}",
            json={"q": " ".join(args[2:]), "source": args[0], "target": args[1]},
        ) as resp:
            await placeholder.delete()
            await sendWrappedMessage(
                f"Translation for {message.author.mention}\n> {(await resp.json())['translatedText']}",
                target=message.channel,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("TLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def create_thread(message, client, args):
    await message.create_thread(
        name=message.content.split("\n").pop(0).replace("*", "").replace("__", "")[:100]
    )
    await asyncio.sleep(0.5)
    notification = (await message.channel.history(limit=1).flatten())[0]
    if notification.type == discord.MessageType.thread_created:
        await notification.delete()


async def emoji_image_function(message, client, args):
    try:
        emoji = None
        buffer = None
        if message.guild:
            emoji = discord.utils.get(message.guild.emojis, name=args[0])
        if not emoji:
            emoji = discord.utils.get(client.emojis, name=args[0])
        if not emoji:
            emoji_query = args[0]
            try:
                buffer = await netcode.simple_get_image(
                    f"https://twemoji.maxcdn.com/v/13.0.0/72x72/{hex(ord(emoji_query))[2:]}.png"
                )
            except Exception as e:
                logger.debug("404 Image Not Found")
        if not emoji and not buffer:
            return await sendWrappedMessage(
                "No emoji found with the given name",
                delete_after=60,
                target=message.channel,
            )
        if not buffer:
            buffer = await netcode.simple_get_image(emoji.url)
        image = discord.File(
            buffer,
            f"emoji.{'gif' if emoji and emoji.animated else 'png'}",
        )
        return await sendWrappedMessage(files=[image], target=message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("TLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def getalong_filter(message, client, args):
    if ch.config.get(guild=message.guild, channel=message.channel, key="getalong-role"):
        role = discord.utils.get(
            message.guild.roles,
            name=ch.config.get(
                guild=message.guild, channel=message.channel, key="getalong-role"
            ),
        ) or message.guild.get_role(
            int(
                ch.config.get(
                    guild=message.guild, channel=message.channel, key="getalong-role"
                )
            )
        )
        ttl = ch.config.get(
            guild=message.guild, channel=message.channel, key="getalong-ttl", default=20
        )
        members = list(filter(lambda member: member != message.author, role.members))
        global conn
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM reminders WHERE guild = %s AND channel = %s AND trigger_type = 'getalong';",
            [
                message.guild.id,
                message.channel.id,
            ],
        )
        for member in members:
            logger.debug(f"Getting {member} along in {message.channel}")
            await message.channel.set_permissions(
                member, send_messages=False, reason="Getalong role"
            )
            interval = ch.config.get(
                guild=message.guild,
                channel=message.channel,
                key="getalong-ttl",
                default="20 minutes",
            )
            cur.execute(
                "INSERT INTO reminders (userid, guild, channel, message, trigger_type, scheduled) VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '"
                + interval.replace("'", "")
                + "');",
                [
                    member.id,
                    message.guild.id,
                    message.channel.id,
                    message.id,
                    "getalong",
                ],
            )
        conn.commit()


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
            "trigger": ["!bigemoji"],
            "function": emoji_image_function,
            "async": True,
            "args_num": 1,
            "args_name": ["emoji name"],
            "description": "Return larger version of an emoji",
        }
    )
    ch.add_command(
        {
            "trigger": ["!pfp", "!avatar"],
            "function": lambda message, client, args: str(
                (
                    message.mentions[0] if len(message.mentions) else message.author
                ).display_avatar
            ).replace(".webp?", ".png?"),
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "Return user's profile picture",
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
    ch.add_command(
        {
            "trigger": ["#️⃣"],
            "function": markdown_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "DM user the markdown of a message",
        }
    )

    ch.add_command(
        {
            "trigger": ["📁"],
            "function": archive_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Archive links in a message",
        }
    )

    ch.add_command(
        {
            "trigger": ["⭐"],
            "function": star_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "(if configured) put message into a starboard channel if a threshold is reached",
        }
    )

    ch.add_command(
        {
            "trigger": ["!translate"],
            "function": translate_function,
            "async": True,
            "args_num": 3,
            "args_name": [
                "Source Language [auto|ar|de|es|fr|it|pt|ru|zh]",
                "Target Language [ar|de|es|fr|it|pt|ru|zh]",
                "Query",
            ],
            "description": "Translate text from language to language",
        }
    )

    ch.add_command(
        {
            "trigger": ["create_thread"],
            "function": create_thread,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "args_name": [],
            "description": "Creates thread",
        }
    )
    ch.add_command(
        {
            "trigger": ["getalong_filter"],
            "function": getalong_filter,
            "async": True,
            "hidden": True,
            "args_num": 1,
            "args_name": ["Getalong"],
            "description": "Getalong",
        }
    )

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
                ch.add_message_reaction_remove_handler(
                    [int(subtuple[3])],
                    {
                        "trigger": [""],  # empty string: a special catch-all trigger
                        "function": subscribe_send_function,
                        "exclusive": False,
                        "async": True,
                        "args_num": 0,
                        "args_name": [],
                        "description": "Notify on emoji send",
                    },
                )
                ch.add_message_reaction_handler(
                    [int(subtuple[3])],
                    commandhandler.Command(
                        function=subscribe_send_function,
                        exclusive=False,
                        sync=False,
                        description="Notify on emoji send",
                    ),
                )
                ch.add_message_reply_handler(
                    [int(subtuple[3])],
                    {
                        "trigger": [""],  # empty string: a special catch-all trigger
                        "function": subscribe_send_function,
                        "exclusive": False,
                        "async": True,
                        "args_num": 0,
                        "args_name": [],
                        "description": "assign roles based on emoji for a given message",
                    },
                )
            guild_config["subscribe"][int(subtuple[3])].append(int(subtuple[0]))
            subtuple = cur.fetchone()
        conn.commit()

    global session
    try:
        session
    except NameError:
        session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
            }
        )
    logger.debug("LRN")
    load_react_notifications(ch)


async def autounload(ch):
    pass
