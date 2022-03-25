from datetime import datetime, timedelta, timezone
from PIL import Image, ImageOps
import io
from functools import partial
from sys import exc_info
from functools import lru_cache
import aiohttp
import asyncio
import commandhandler
import dateparser.search
import Levenshtein
import discord
import exceptions
import load_config
import logging
import messagefuncs
import netcode
import psycopg2
import random
import traceback
import text_manipulators
import ujson

# global conn set by reload_function

logger = logging.getLogger("fletcher")


def consume_channel_token(args):
    channel_name = ""
    args_consumed = 0
    for arg in args:
        args_consumed += 1
        channel_name += " " + arg
        if (":" in channel_name) or "#" in channel_name:
            break
    args = args[args_consumed:]
    channel_name = channel_name.lstrip()
    return channel_name, args


async def set_role_color_function(message, client, args):
    global config
    global ch
    guild_config = ch.scope_config(guild=message.guild)
    try:
        role_list = message.channel.guild.roles
        role = discord.utils.get(role_list, name=args[0].replace("_", " "))
        if role is None and ch.config.get(
            "color-role-autocreate", guild=message.guild.id, default=False
        ):
            role = await message.guild.create_role(
                name=args[0], reason="Auto-created color role"
            )
        if role is not None:
            if args[1].startswith("random"):
                args[1] = "#%06x" % random.randint(0, 0xFFFFFF)
                await messagefuncs.sendWrappedMessage(
                    f"Setting color of {args[0]} to {args[1]}", message.channel
                )
            if args[1].startswith("#"):
                args[1] = args[1][1:]
            rgb = [
                int(args[1][0:2], 16),
                int(args[1][2:4], 16),
                int(args[1][4:6], 16),
            ]
            await role.edit(
                colour=discord.Colour.from_rgb(rgb[0], rgb[1], rgb[2]),
                reason="Role edited on behalf of " + str(message.author.id),
            )
            if "snappy" in config["discord"] and config["discord"]["snappy"]:
                await message.delete()
            if len(message.mentions) == 1:
                await message.mentions[0].add_roles(
                    role, reason="Color role", atomic=False
                )
            await message.add_reaction("✅")
        else:
            await messagefuncs.sendWrappedMessage(
                "Unable to find matching role to set color, create this role before trying to set its color.",
                message.author,
            )
    except discord.Forbidden as e:
        await message.sendWrappedMessage(
            "Unable to set role color, am I allowed to edit this role?  My role must be above the target in the heirarchy, and I must have the Manage Roles permission.",
            message.author,
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SRCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def addrole_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            pass  # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            roleProperties = {"name": None, "colour": None, "mentionable": True}
            if " with " in argString:
                roleProperties["name"] = argString.split(" with")[0]
                argString = (
                    argString.split(" with")[1]
                    .lower()
                    .replace("color", "colour")
                    .replace("pingable", "mentionable")
                )
                it = iter(
                    argString.strip().replace(" and ", "").replace(", ", "").split(" ")
                )
                for prop, val in zip(it, it):
                    if prop == "colour":
                        roleProperties["colour"] = discord.Colour.from_rgb(
                            int(val[0 - 1]), int(val[2 - 3]), int(val[4 - 5])
                        )
                    elif (prop == "mentionable" and val in ["no", "false"]) or (
                        prop == "not" and val == "mentionable"
                    ):
                        roleProperties["mentionable"] = False
            else:
                roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                err = "Role already exists!"
                if (
                    not role.mentionable
                    or message.channel.permissions_for(message.author).manage_messages
                ):
                    if role in message.author.roles:
                        err = f"{err} `!revoke {role.name} to me` to remove this role from yourself."
                    else:
                        err = f"{err} `!assign {role.name} to me` to add this role to yourself."
                else:
                    if role in message.author.roles:
                        err = f"{err} An administrator can `!revoke {role.name} to @{message.author.id}` to remove this role from you."
                    else:
                        err = f"{err} An administrator can `!assign {role.name} to @{message.author.id}` to add this role to you."
                return await messagefuncs.sendWrappedMessage(err, message.channel)
            else:
                role = await message.channel.guild.create_role(
                    name=roleProperties["name"],
                    colour=roleProperties["colour"],
                    mentionable=True,
                    reason="Role added on behalf of " + str(message.author.id),
                )
                await messagefuncs.sendWrappedMessage(
                    f"Role {role.mention} successfully created.", message.channel
                )
                await role.edit(mentionable=roleProperties["mentionable"])
                if "snappy" in config["discord"] and config["discord"]["snappy"]:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ARF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def assignrole_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            pass  # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            if argString.endswith(" to me"):
                argString = argString[:-6]
            roleProperties = {"name": None}
            roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                if (
                    not role.mentionable
                    or message.channel.permissions_for(message.author).manage_messages
                ):
                    if role in message.author.roles:
                        return await messagefuncs.sendWrappedMessage(
                            f"You already have that role, `!revoke {role.name} from me` to remove this role from yourself.",
                            message.channel,
                        )
                    else:
                        if (
                            "snappy" in config["discord"]
                            and config["discord"]["snappy"]
                        ):
                            await message.delete()
                        await message.author.add_roles(
                            role, reason="Self-assigned", atomic=False
                        )
                        return await messagefuncs.sendWrappedMessage(
                            f"Role assigned, `!revoke {role.name} from me` to remove this role from yourself.",
                            message.channel,
                        )
                else:
                    # TODO unimplemented
                    pass
                    if role in message.author.roles:
                        err = f"{err} An administrator can `!revoke {role.name} to @{message.author.id}` to remove this role from you."
                    else:
                        err = f"{err} An administrator can `!assign {role.name} to @{message.author.id}` to add this role to you."
                return await messagefuncs.sendWrappedMessage(err, message.channel)
            else:
                await messagefuncs.sendWrappedMessage(
                    f"Role {roleProperties['name']} does not exist, use the addrole command to create it.",
                    message.channel,
                )
                if "snappy" in config["discord"] and config["discord"]["snappy"]:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ASRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def revokerole_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            pass  # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            if argString.endswith(" from me"):
                argString = argString[:-8]
            roleProperties = {"name": None}
            roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                if (
                    not role.mentionable
                    or message.channel.permissions_for(message.author).manage_messages
                ):
                    if role in message.author.roles:
                        if (
                            "snappy" in config["discord"]
                            and config["discord"]["snappy"]
                        ):
                            await message.delete()
                        await message.author.remove_roles(
                            role, reason="Self-assigned", atomic=False
                        )
                        return await messagefuncs.sendWrappedMessage(
                            f"Role revoked, `!assign {role.name} to me` to add this role to yourself.",
                            message.channel,
                        )
                    else:
                        return await messagefuncs.sendWrappedMessage(
                            f"You don't have that role, `!assign {role.name} to me` to assign this role to yourself.",
                            message.channel,
                        )
                else:
                    # TODO unimplemented
                    pass
                    if role in message.author.roles:
                        err = f"{err} An administrator can `!revoke {role.name} from @{message.author.id}` to remove this role from you."
                    else:
                        err = f"{err} An administrator can `!assign {role.name} to @{message.author.id}` to add this role to you."
                return await messagefuncs.sendWrappedMessage(err, message.channel)
            else:
                await messagefuncs.sendWrappedMessage(
                    f"Role {roleProperties['name']} does not exist, use the addrole command to create it.",
                    message.channel,
                )
                if "snappy" in config["discord"] and config["discord"]["snappy"]:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"RSRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def delrole_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            pass  # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            roleProperties = {"name": None}
            roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                if message.channel.permissions_for(message.author).manage_messages:
                    await role.delete(reason="On behalf of " + str(message.author))
                    await messagefuncs.sendWrappedMessage(
                        f"Role `@{roleProperties['name']}` deleted.", message.channel
                    )
                else:
                    await messagefuncs.sendWrappedMessage(
                        f"You do not have permission to delete role `@{roleProperties['name']}`.",
                        message.channel,
                    )
            else:
                err = f"Role `@{roleProperties['name']}` does not exist!"
                if message.channel.permissions_for(message.author).manage_messages:
                    err += f" `!addrole {role.name}` to add this role."
                else:
                    err += f" An administrator can `!addrole {role.name}` to add this role."
                await messagefuncs.sendWrappedMessage(err, message.channel)
                if "snappy" in config["discord"] and config["discord"]["snappy"]:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"DRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def modping_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            pass  # Reaction
        else:
            if not message.channel.permissions_for(message.author).manage_messages:

                def gaveled_by_admin_check(reaction):
                    return (
                        reaction.member.guild_permissions.manage_webhooks
                        and str(reaction.emoji) == "<:gavel:430638348189827072>"
                    )

                try:
                    await modreport_function(
                        message,
                        client,
                        (
                            "\nRole ping requested for " + " ".join(args).lstrip("@")
                        ).split(" "),
                    )
                    reaction = await client.wait_for(
                        "raw_reaction_add", timeout=6000.0, check=gaveled_by_admin_check
                    )
                except asyncio.TimeoutError:
                    raise Exception("Timed out waiting for approval")
            role_list = message.channel.guild.roles
            role = discord.utils.get(
                role_list, name=" ".join(args).lstrip("@").split("\n")[0]
            )
            lay_mentionable = role.mentionable
            if not lay_mentionable:
                await role.edit(mentionable=True)
            mentionPing = await messagefuncs.sendWrappedMessage(
                f"{message.author.name} pinging {role.mention}", message.channel
            )
            if not lay_mentionable:
                await role.edit(mentionable=False)
            if (
                ch.user_config(
                    message.author.id,
                    message.guild.id,
                    "snappy",
                    default=False,
                    allow_global_substitute=True,
                )
                or ch.config.get(key="snappy", guild=message.guild.id)
            ):
                mentionPing.delete()
            logger.debug(f"MPF: pinged {mentionPing.id} for guild {message.guild.name}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MPF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def modreport_function(message, client, args):
    global config
    try:
        report_content = None
        plaintext = None
        automod = None
        scoped_config = ch.scope_config(guild=message.guild)
        if (
            not scoped_config.get("moderation")
            or type(message.channel) is discord.DMChannel
        ):
            logger.info(f"Moderation disabled on guild {message.guild}")
            if not (len(args) == 3 and type(args[1]) is discord.Member):
                await messagefuncs.sendWrappedMessage(
                    f"Fletcher-assisted moderation disabled on guild {message.guild}. Check with your local mods directly, or ask them to enable anonymous mod reports by setting `moderation` to on at https://fletcher.fun",
                    message.author,
                    delete_after=60,
                )
            return
        if len(args) == 3 and type(args[1]) is discord.Member:
            try:
                await message.remove_reaction("👁‍🗨", args[1])
            except discord.Forbidden as e:
                logger.warning("MRF: Forbidden from removing modreport reaction")
                pass
            plaintext = message.content
            report_content = f"Mod Report: #{message.channel.name} ({message.channel.guild.name}) {message.jump_url} via reaction to "
            automod = False
        else:
            plaintext = " ".join(args)
            report_content = f"Mod Report: #{message.channel.name} ({message.channel.guild.name}) {message.jump_url} "
            automod = True
        if message.channel.is_nsfw():
            report_content = report_content + await text_manipulators.rot13_function(
                message, client, [plaintext, "INTPROC"]
            )
        else:
            report_content = report_content + plaintext
        if "mod-message-prefix" in scoped_config:
            report_content = scoped_config["mod-message-prefix"] + "\n" + report_content
        if "mod-message-suffix" in scoped_config:
            report_content = report_content + "\n" + scoped_config["mod-message-suffix"]
        if automod:
            users = scoped_config["mod-userslist"]
        else:
            users = scoped_config.get("manual-mod-userslist", [message.guild.owner.id])
        users = list(load_config.expand_target_list(users, message.guild))
        for target in users:
            modmail = await messagefuncs.sendWrappedMessage(report_content, target)
            if message.channel.is_nsfw():
                await modmail.add_reaction("🕜")
    except discord.Forbidden:
        await messagefuncs.sendWrappedMessage(
            f"Unable to send modreport: {e}", message.guild.owner
        )
    except KeyError as e:
        await error_report_function(f"{e} config key missing", message.guild, client)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def lastactive_channel_function(message, client, args):
    try:
        lastMonth = None
        before = True
        now = datetime.now(timezone.utc)
        try:
            if args[0]:
                try:
                    lastMonth = now.date() - timedelta(days=int(args[0]))
                except ValueError:
                    if args[1]:
                        if args[0].startswith("a"):
                            before = False
                        lastMonth = now.date() - timedelta(days=int(args[1]))
                    pass
        except IndexError:
            pass
        msg = ""
        for channel in message.channel.guild.text_channels:
            try:
                category_pretty = ""
                if channel.category_id:
                    category_pretty = (
                        f" [{client.get_channel(channel.category_id).name}]"
                    )
                created_at = (await channel.history(limit=1).flatten())[0].created_at
                created_pretty = text_manipulators.pretty_date(created_at)
                if created_pretty:
                    created_pretty = f" ({created_pretty})"
                if lastMonth:
                    if (before and lastMonth < created_at.date()) or (
                        not before and lastMonth > created_at.date()
                    ):
                        msg = f'{msg}\n<#{channel.id}>{category_pretty}: {created_at.isoformat(timespec="minutes")}{created_pretty}'
                    else:
                        # filtered out
                        pass
                else:
                    msg = f'{msg}\n<#{channel.id}>{category_pretty}: {created_at.isoformat(timespec="minutes")}{created_pretty}'
            except discord.NotFound as e:
                pass
            except IndexError as e:
                msg = f"{msg}\n<#{channel.id}>{category_pretty}: Bad History"
                pass
            except discord.Forbidden as e:
                msg = f"{msg}\n<#{channel.id}>{category_pretty}: Forbidden"
                pass
        msg = f"**Channel Activity:**{msg}"
        await messagefuncs.sendWrappedMessage(msg, message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LACF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def lastactive_user_function(message, client, args):
    try:
        lastMonth = None
        before = True
        now = datetime.utcnow()
        try:
            if args[0]:
                try:
                    lastMonth = now.date() - timedelta(days=int(args[0]))
                except ValueError:
                    if args[1]:
                        if args[0].startswith("a"):
                            before = False
                        lastMonth = now.date() - timedelta(days=int(args[1]))
                    pass
        except IndexError:
            pass
        if message.guild.large:
            message.guild.chunk()
        users = {}
        tomorrow = datetime.today() + timedelta(days=1)
        for m in message.guild.members:
            users[m.id] = tomorrow
        for channel in message.channel.guild.text_channels:
            async for message in channel.history(limit=None):
                try:
                    logger.debug(
                        f"[{message.created_at} <#{channel.id}>] <@{message.author.id}>: {message.content}"
                    )
                    if message.created_at < users[message.author.id]:
                        users[message.author.id] = message.created_at
                except discord.NotFound as e:
                    pass
                except discord.Forbidden as e:
                    pass
        msg = f"**User Activity:**{msg}"
        for user_id, last_active in users:
            if last_active == datetime.today() + timedelta(days=1):
                last_active = "None"
            else:
                last_active = text_manipulators.pretty_date(last_active)
            msg = f"{msg}\n<@{user_id}>: {last_active}"
        await messagefuncs.sendWrappedMessage(msg, message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LSU[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def kick_user_function(message, client, args):
    try:
        if len(message.mentions) >= 1:
            member = message.mentions[0]
        else:
            member = message.guild.get_member(int(args[0]))
        logMessage = " ".join(args[1:]).strip()
        if not len(logMessage):
            logMessage = "A message was not provided."
        logMessage = f"You have been kicked from {message.guild.name}. If you have questions, please contact a moderator for that guild.\nReason: {logMessage}"
        logger.info(
            f"KUF: <@{message.author.id}> kicked <@{member.id}> from {message.guild.id} for {logMessage}"
        )
        try:
            await messagefuncs.sendWrappedMessage(logMessage, member)
        # TODO make this a more specific catch block
        except Exception as e:
            exc_type, exc_obj, exc_tb = exc_info()
            logger.error(f"KUF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
            # Ignore blocks etc
            pass
        await member.kick(reason=f"{logMessage} obo {message.author.name}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"KUF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def lockout_user_function(message, client, args):
    try:
        if len(message.mentions) >= 1:
            member = message.mentions[0]
        else:
            member = message.guild.get_member(int(args[0]))
        if len(args) >= 2 and args[1] == "reset":
            mode = "reset"
        else:
            mode = "hide"
        if len(args) >= 3 and args[2] == "thorough":
            thorough = True
        else:
            thorough = False
        if len(args) >= 4:
            filter_id = int(args[3])
        else:
            filter_id = None
        log = "Lockout " + mode + " completed for " + member.name
        for category, channels in member.guild.by_category():
            if category is not None and (
                (filter_id and category.id == filter_id) or not filter_id
            ):
                logMessage = (
                    str(member)
                    + " from category "
                    + str(category)
                    + " in "
                    + str(member.guild)
                )
                logger.debug("LUF: " + logMessage)
                log = log + "\n" + logMessage
                if mode == "reset":
                    await category.set_permissions(
                        member,
                        overwrite=None,
                        reason="Admin reset lockout obo " + message.author.name,
                    )
                else:
                    await category.set_permissions(
                        member,
                        read_messages=False,
                        read_message_history=False,
                        send_messages=False,
                        reason="Admin requested lockout obo " + message.author.name,
                    )
            if (category is None) or (
                thorough
                and category is not None
                and ((filter_id and category.id == filter_id))
                or not filter_id
            ):
                for channel in channels:
                    if mode == "reset":
                        await channel.set_permissions(
                            member,
                            overwrite=None,
                            reason=f"Admin reset lockout obo {message.author.name}",
                        )
                        logMessage = f"{member} from non-category channel {channel} in {member.guild}"
                        logger.debug("LUF: " + logMessage)
                        log += f"\n{logMessage}"
                    else:
                        try:
                            await channel.set_permissions(
                                member,
                                read_messages=False,
                                read_message_history=False,
                                send_messages=False,
                                reason=f"Admin requested lockout obo {message.author.name}",
                            )
                            logMessage = f"{member} from non-category channel {channel} in {member.guild}"
                            logger.debug("LUF: " + logMessage)
                            log += f"\n{logMessage}"
                        except discord.Forbidden as e:
                            await messagefuncs.sendWrappedMessage(
                                f"Forbidden to set permissions on {channel}",
                                message.author,
                            )
        await messagefuncs.sendWrappedMessage(log, message.author)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LUF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def part_channel_function(message, client, args, ctx=None):
    try:
        if message and len(message.channel_mentions) > 0:
            channels = message.channel_mentions
        elif len(args) == 0 and message and message.guild is None:
            error = "Parting a channel requires server and channel to be specified (e.g. `!part server:channel`)"
            if ctx:
                return await ctx.response.send_message(error, ephemeral=True)
            return await messagefuncs.sendWrappedMessage(
                error,
                message.author,
            )
        elif len(args) == 0:
            channels = [ctx.channel if ctx else message.channel]
        elif args[0].strip()[-2:] == ":*":
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(args[0])
                .strip()[:-2]
                .replace("_", " "),
            )
            channels = [*guild.text_channels, *guild.voice_channels]
        else:
            try:
                old_args = [*args]
                channel_name, args = consume_channel_token(args)
                channel = messagefuncs.xchannel(
                    channel_name, message.guild if message else ctx.channel.guild
                )
            except (exceptions.DirectMessageException, AttributeError):
                return await messagefuncs.sendWrappedMessage(
                    "Parting a channel via DM requires server to be specified (e.g. `!part server:channel`)",
                    message.author,
                )
            if channel:
                channels = [channel]
            else:
                channels = []
        if len(channels) > 0:
            channel = channels[0]
        else:
            channel = None
        if message and message.guild is not None:
            guild = message.guild
        if ctx and ctx.guild is not None:
            guild = ctx.guild
        elif hasattr(channel, "guild"):
            assert isinstance(channel, discord.TextChannel)
            guild = channel.guild
        if not len(channels):
            error_msg = "Failed to locate channel, please check spelling."
            if len(old_args) and guild:
                error_msg += f" Did you mean `{sorted([*guild.text_channels, *guild.voice_channels], key=lambda channel: Levenshtein.distance(channel.name, old_args[0]))[0].name}`?"
            if ctx:
                return await ctx.response.send_message(error_msg, ephemeral=True)
            await message.add_reaction("🚫")
            return await messagefuncs.sendWrappedMessage(error_msg, message.channel)
        channel_names = ""
        for channel in channels:
            await channel.set_permissions(
                message.author if message else ctx.user,
                read_messages=False,
                read_message_history=False,
                send_messages=False,
                reason=f"User requested part {(message.author if message else ctx.user).name}",
            )
            channel_names += f"{channel.guild.name}:{channel.name}, "
        if ctx:
            return await ctx.response.send_message(
                f"Parted from {channel_names[0:-2]}", ephemeral=True
            )
        await message.add_reaction("✅")
        await messagefuncs.sendWrappedMessage(
            f"Parted from {channel_names[0:-2]}", message.author
        )
    except (discord.NotFound, discord.Forbidden) as e:
        await messagefuncs.sendWrappedMessage(e, message.author)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"PCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def optin_channel_function(message, client, args):
    try:
        pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"OICF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


# Requires schedule.py to clear reminders
async def snooze_channel_function(message, client, args):
    try:
        global conn
        channels = None
        if len(message.channel_mentions) > 0:
            channels = message.channel_mentions
        elif len(args) == 0 and message.guild is None:
            return await messagefuncs.sendWrappedMessage(
                "Snoozing a channel requires server and channel to be specified (e.g. `!snooze server:channel [hours]`)",
                message.author,
            )
        elif len(args) == 0:
            channel = message.channel
        elif ":*" in message.content:
            guild_name, args = consume_channel_token(args)
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(guild_name)
                .strip()[:-2]
                .replace("_", " "),
            )
            channels = guild.text_channels
        else:
            try:
                old_args = [*args]
                channel_name, args = consume_channel_token(args)
                channel = messagefuncs.xchannel(channel_name, message.guild)
            except exceptions.DirectMessageException:
                return await messagefuncs.sendWrappedMessage(
                    "Snoozing a channel via DM requires server to be specified (e.g. `!snooze server:channel [hours]`)",
                    message.author,
                )
        if channels is None:
            if channel:
                channels = [channel]
            else:
                channels = []
        if len(channels) > 0:
            channel = channels[0]
        else:
            channel = None
        if hasattr(channel, "guild"):
            guild = channel.guild
        elif message.guild is not None:
            guild = message.guild
        if not len(channels):
            error_msg = "Failed to locate channel, please check spelling."
            if len(old_args):
                error_msg += f" Did you mean `{sorted([*guild.text_channels, *guild.voice_channels], key=lambda channel: Levenshtein.distance(channel.name, old_args[0]))[0].name}`?"
            await message.add_reaction("🚫")
            return await messagefuncs.sendWrappedMessage(error_msg, message.author)
        if (
            channel
            and not channel.permissions_for(
                guild.get_member(client.user.id)
            ).manage_roles
        ) or (
            not channel
            and not guild.get_member(client.user.id).guild_permissions.manage_roles
        ):
            await message.add_reaction("🚫")
            return await messagefuncs.sendWrappedMessage(
                f"Unable to snooze the requested channel(s) ({channel} in {guild}) - owner has not granted Fletcher Manage Permissions.",
                message.author,
            )
        cur = conn.cursor()
        if len(args) == 2:
            try:
                interval = float(args[1].rstrip("h"))
            except ValueError:
                interval = float(24)
        elif len(args) > 1:
            try:
                interval = dateparser.search.search_dates(
                    message.content,
                    settings={
                        "PREFER_DATES_FROM": "future",
                        "PREFER_DAY_OF_MONTH": "first",
                    },
                )[0][1]
            except (ValueError, IndexError, TypeError):
                interval = float(24)
        else:
            try:
                interval = float(args[0].rstrip("h"))
            except (ValueError, IndexError):
                interval = float(24)
        quote = "'"
        overwrites = "overwrite " + ujson.dumps(
            {
                f"{guild.name.replace(quote, quote+quote)}:{channel.name}": dict(
                    channel.overwrites_for(message.author)
                )
                for channel in channels
            }
        )
        if type(interval) == float:
            cur.execute(
                f"INSERT INTO reminders (userid, guild, channel, message, content, scheduled, trigger_type) VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '{interval} hours', '{overwrites}');",
                [
                    message.author.id,
                    guild.id,
                    message.channel.id,
                    message.id,
                    message.content,
                ],
            )
        else:
            cur.execute(
                f"INSERT INTO reminders (userid, guild, channel, message, content, scheduled, trigger_type) VALUES (%s, %s, %s, %s, %s, %s, '{overwrites}');",
                [
                    message.author.id,
                    guild.id,
                    message.channel.id,
                    message.id,
                    message.content,
                    interval,
                ],
            )
        channel_names = ""
        for channel in channels:
            await channel.set_permissions(
                message.author,
                read_messages=False,
                read_message_history=False,
                send_messages=False,
                embed_links=False,
                reason=f"User requested snooze {message.author.name}",
            )
            channel_names += f"{channel.guild.name}:{channel.name}, "
        channel_names = channel_names[:-2]
        try:
            if args[0].strip()[-2:] == ":*":
                channel_names = channels[0].guild.name
        except IndexError:
            pass
        conn.commit()
        await message.add_reaction("✅")
        if type(interval) == float:
            await messagefuncs.sendWrappedMessage(
                f"Snoozed {channel_names} for {interval} hours (`!part` to leave channel permanently)",
                message.author,
            )
        else:
            await messagefuncs.sendWrappedMessage(
                f"Snoozed {channel_names} until {interval} (`!part` to leave channel permanently)",
                message.author,
            )
    except discord.Forbidden as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.info(f"SNCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await messagefuncs.sendWrappedMessage(
            "Snooze forbidden! I don't have the authority to do that.",
            message.channel,
            delete_after=30,
        )
    except psycopg2.errors.InvalidDatetimeFormat as e:
        conn.rollback()
        await messagefuncs.sendWrappedMessage(
            "Invalid time specifier.", message.channel, delete_after=30
        )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SNCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def sudo_function(message, client, args):
    try:
        guild_config = ch.scope_config(guild=message.guild)
        if "wheel-role" not in guild_config:
            raise Exception(
                "No guild-specific configuration for wheel on guild "
                + str(message.guild)
            )
        now = datetime.utcnow()
        role = message.guild.get_role(int(guild_config["wheel-role"]))
        if not role:
            raise Exception("Wheel role not found")
        await message.author.add_roles(role, reason="Sudo escalation", atomic=False)
        await message.add_reaction("✅")
        tries = 0
        while tries < 600:
            await asyncio.sleep(1)
            try:
                # Discord audit log has an after parameter which hasn't worked in ages :(
                entry = await message.guild.audit_logs(
                    limit=None, user=message.author, oldest_first=False
                ).next()
            except discord.NoMoreItems:
                entry = None
                pass
            if entry and entry.created_at > now:
                logger.info("SUDOF: " + str(entry))
                await message.author.remove_roles(
                    role, reason="Sudo deescalation (commanded)", atomic=False
                )
                return
            tries = tries + 1
        logger.info("SUDOF: timeout")
        await message.author.remove_roles(
            role, reason="Sudo deescalation (timeout)", atomic=False
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SUDOF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def role_message_function(message, client, args, remove=False):
    try:
        reaction, user, mode = args
        reaction_name = (
            reaction.emoji.name[1:-1]
            if isinstance(reaction.emoji, discord.Emoji)
            else str(reaction.emoji)
        )
        role = ch.config.get(
            key=f"role-message-{reaction_name}-{message.id}",
            default=0,
            guild=message.guild,
        )
        if role == 0:
            role = ch.config.get(
                key=f"role-message-{reaction_name}", default=0, guild=message.guild
            )
        audit_channel = ch.config.get(
            key="audit-channel", default=0, guild=message.guild
        )
        if audit_channel:
            audit_channel = message.guild.get_channel(audit_channel)
        role_str = role
        if type(role) is int:
            role = message.guild.get_role(role)
        else:
            role = discord.utils.get(message.guild.roles, name=role)
        if not role:
            error_message = f"Matching role {role_str} not found for reaction role-message-{reaction_name} to https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}"
            raise exceptions.MisconfigurationException(error_message)
        if not remove:
            error_message = f"Assigning role {role.mention} to {user.mention} via {reaction.emoji} on https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}"
            if (
                ch.config.get(
                    key="role-message-mode", default="open", guild=message.guild
                )
                == "confirm"
            ):
                confirmMessage = await messagefuncs.sendWrappedMessage(
                    f"{user.mention} ({user.display_name}) requests entry to role __@{role.name}__. To confirm entry react with a checkmark. If you do not wish to grant entry, no further action is required.",
                    message.author,
                )
                await confirmMessage.add_reaction("✅")
                try:
                    reaction = await client.wait_for(
                        "raw_reaction_add",
                        timeout=60000.0 * 24,
                        check=lambda reaction: reaction.message_id == confirmMessage.id
                        and (str(reaction.emoji) == "✅")
                        and (reaction.user_id == message.author.id),
                    )
                except asyncio.TimeoutError:
                    await confirmMessage.edit(
                        content=f"~~{confirmMessage.content}~~Request expired due to timeout."
                    )
                    await confirmMessage.remove_reaction("✅", client.user)
                    return
            await message.guild.get_member(user.id).add_roles(
                role, reason="Self-assigned via reaction to role-message", atomic=False
            )
            if args[0].emoji in ch.config.get(
                key="role-message-autodelete", guild=message.guild, default=[]
            ):
                await message.remove_reaction(reaction.emoji, user)
            if audit_channel:
                await messagefuncs.sendWrappedMessage(error_message, audit_channel)
        else:
            error_message = f"Removing role {role.mention} from {user.mention} via {reaction.emoji} on https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}"
            await message.guild.get_member(user.id).remove_roles(
                role, reason="Self-removed via reaction to role-message", atomic=False
            )
            if audit_channel:
                await messagefuncs.sendWrappedMessage(error_message, audit_channel)
    except (discord.Forbidden, exceptions.MisconfigurationException) as e:
        exc_type, exc_obj, exc_tb = exc_info()
        await messagefuncs.sendWrappedMessage(
            f"RMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}", message.guild.owner
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"RMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def chanlog_function(message, client, args):
    try:
        await message.add_reaction("🔜")
        content = f"Log for {message.guild.name}:{message.channel.name}"
        if "short" in args:

            async def log_message(message, last_created_at=None, last_author_name=None):
                message_created_at = message.created_at.strftime("%b %d %Y %H:%M:%S")
                if (
                    last_created_at
                    and message.created_at.date() == last_created_at.date()
                ):
                    message_created_at = message_created_at.split(" ")[3]
                author_name = f"<{message.author.display_name}> "
                if last_author_name == message.author.display_name:
                    author_name = " " * len(author_name)
                content = (
                    f"{message_created_at} {author_name}{message.system_content}\n"
                )
                for attachment in message.attachments:
                    content += f"{message_created_at} {author_name}{attachment.url}\n"
                for reaction in message.reactions:
                    users = await reaction.users().flatten()
                    users = [user.display_name for user in users]
                    content += f'{",".join(users)} reacted with {reaction.emoji}\n'
                return content

        else:

            async def log_message(message, last_created_at=None, last_author_name=None):
                content = f'{message.id} {message.created_at.strftime("%b %d %Y %H:%M:%S")} <{message.author.display_name}:{message.author.id}> {message.system_content}\n'
                for attachment in message.attachments:
                    content += f'{message.id} {message.created_at.strftime("%b %d %Y %H:%M:%S")} <{message.author.display_name}:{message.author.id}> {attachment.url}\n'
                for reaction in message.reactions:
                    async for user in reaction.users():
                        content += f"Reaction to {message.id}: {reaction.emoji} from {user.display_name} ({user.id})\n"
                return content

        if len(args) > 0 and args[0].isnumeric():
            content += f" before {args[0]}"
            before = await message.channel.fetch_message(id=args[0])
        else:
            before = None
        if len(args) > 1:
            content += f" after {args[1]}"
            after = await message.channel.fetch_message(id=args[1])
        else:
            after = None

        content += f" as of {datetime.utcnow()}\n"

        last_created_at = None
        last_author_name = None
        if len(args) > 2 and args[2] == "reverse":
            if before:
                content += await log_message(before)
                last_created_at = before.created_at
                last_author_name = before.author.display_name
            async for historical_message in message.channel.history(
                limit=None, oldest_first=False, before=before, after=after
            ):
                content += await log_message(
                    historical_message, last_created_at, last_author_name
                )
                last_created_at = historical_message.created_at
                last_author_name = historical_message.author.display_name
            if after:
                content += await log_message(after, last_created_at, last_author_name)
        else:
            if after:
                content += await log_message(after)
                last_created_at = after.created_at
                last_author_name = after.author.display_name
            async for historical_message in message.channel.history(
                limit=None, oldest_first=True, before=before, after=after
            ):
                content += await log_message(
                    historical_message, last_created_at, last_author_name
                )
                last_created_at = historical_message.created_at
                last_author_name = historical_message.author.display_name
            if before:
                content += await log_message(before, last_created_at, last_author_name)
        link = text_manipulators.fiche_function(content, message.id)
        await messagefuncs.sendWrappedMessage(link, message.author)
        await message.remove_reaction("🔜", client.user)
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CLF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def copy_permissions_function(message, client, args):
    try:
        sourceChannel = args[0]
        targetChannel = message.channel

        if type(targetChannel) is discord.DMChannel:
            return await messagefuncs.sendWrappedMessage(
                f"This command cannot be run in DMs.",
                message.author,
            )
        if sourceChannel.startswith("<#"):
            sourceChannel = message.guild.get_channel(int(sourceChannel[2:-1]))
        else:
            sourceChannel = discord.utils.get(
                message.guild.channels, name=sourceChannel
            )

        if len(args) > 1:
            targetChannel = args[1]
            if targetChannel.startswith("<#"):
                targetChannel = message.guild.get_channel(int(targetChannel[2:-1]))
            else:
                targetChannel = discord.utils.get(
                    message.guild.channels, name=targetChannel
                )
        if not ch.is_admin(targetChannel, message.author)["channel"] or not ch.is_admin(
            sourceChannel, message.author
        ):
            return await messagefuncs.sendWrappedMessage(
                f"You do not have permission to perform this operation on either {sourceChannel} or {targetChannel}.",
                message.author,
            )

        await message.add_reaction("🔜")
        set_permissions_tasks = []
        for key, overwrite in targetChannel.overwrites.items():
            logging.info(
                f"Removing overwrite {overwrite} for {key} from {targetChannel.name}"
            )
            set_permissions_tasks.append(
                targetChannel.set_permissions(key, overwrite=None)
            )
        await asyncio.gather(*set_permissions_tasks)
        set_permissions_tasks = []
        for key, overwrite in sourceChannel.overwrites.items():
            logging.info(
                f"Adding overwrite {overwrite} for {key} from {sourceChannel.name} to {targetChannel.name}"
            )
            set_permissions_tasks.append(
                targetChannel.set_permissions(
                    key,
                    overwrite=overwrite,
                    reason=f"Sync from {sourceChannel.name} for {message.author.name}",
                )
            )
        await asyncio.gather(*set_permissions_tasks)
        await message.remove_reaction("🔜", client.user)
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CPF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def copy_emoji_function(message, client, args):
    try:
        if not message.channel.permissions_for(message.author).manage_emojis:
            await message.add_reaction("🙅‍♀️")
            return
        if len(args) == 2:
            url = args[0] if "." in args[0] else args[1]
            emoji_name = args[1] if url == args[0] else args[0]
            emoji = None
        elif len(args) == 1 and args[0].startswith("<") and args[0].endswith(">"):
            parts = args[0][2:-1].split(":")
            emoji_name = parts[0]
            emoji = None
            url = f"https://cdn.discordapp.com/emojis/{parts[1]}.png"
        else:
            emoji_query = args.pop(0).strip(":")
            if ":" in emoji_query:
                emoji_query = emoji_query.split(":")
                emoji_query[0] = messagefuncs.expand_guild_name(
                    emoji_query[0], suffix=""
                )
                filter_query = (
                    lambda m: m.name == emoji_query[1]
                    and m.guild.name == emoji_query[0]
                )
            else:
                filter_query = lambda m: m.name == emoji_query
            emoji = list(filter(filter_query, client.emojis))
            if len(args) > 0 and args[0].isnumeric():
                emoji = emoji[int(args.pop(0))]
            elif len(emoji):
                emoji = emoji[0]
            else:
                error_msg = "Emoji not found on any Fletcher-enabled server."
                if isinstance(emoji_query, str):
                    error_msg += f" Did you mean `{sorted(client.emojis, key=lambda emoji: Levenshtein.distance(emoji.name, emoji_query))[0].name}`?"
                await messagefuncs.sendWrappedMessage(
                    error_msg, message.channel, delete_after=30
                )
                return
            if len(args) > 0:
                emoji_name = args.pop(0)
            else:
                emoji_name = emoji.name
            url = emoji.url
        if ".webp" in url:
            url = url.replace(".webp", ".png", 1)
        if "!laetse" in message.content:
            image_blob = await netcode.simple_get_image(url)
            image_blob.seek(0)
            image = Image.open(image_blob)
            flip_image = ImageOps.mirror(ImageOps.flip(image))
            output_image_blob = io.BytesIO()
            flip_image.save(output_image_blob, format="PNG", optimize=True)
            output_image_blob.seek(0)
            emoteServer = client.get_guild(
                ch.config.get(section="discord", key="emoteServer", default=0)
            )
            try:
                processed_emoji = await emoteServer.create_custom_emoji(
                    name=emoji.name[::-1],
                    image=output_image_blob.read(),
                    reason="xreact flip-o-matic",
                )
            except discord.Forbidden:
                logger.error("discord.emoteServer misconfigured!")
            except discord.HTTPException:
                output_image_blob.seek(0)
                await random.choice(emoteServer.emojis).delete()
                processed_emoji = await emoteServer.create_custom_emoji(
                    name=emoji.name[::-1],
                    image=output_image_blob.read(),
                    reason="xreact flip-o-matic",
                )
            url = processed_emoji.url
        if url:
            target = await messagefuncs.sendWrappedMessage(
                f"Add reaction {emoji if emoji else emoji_name+' ('+url+')'}?",
                message.channel,
            )
            await target.add_reaction("✅")
            try:
                await client.wait_for(
                    "raw_reaction_add",
                    timeout=6000.0,
                    check=lambda reaction: (str(reaction.emoji) == str("✅"))
                    and reaction.member
                    and message.channel.permissions_for(reaction.member).manage_emojis
                    and reaction.member.id != client.user.id
                    and reaction.message_id == target.id,
                )
            except asyncio.TimeoutError:
                await target.edit(content="Cancelled, timeout.")
                await message.remove_reaction("✅", client.user)
                return
            custom_emoji = await message.guild.create_custom_emoji(
                name=emoji_name,
                image=(await netcode.simple_get_image(url)).read(),
                reason=f"Synced{' from '+str(emoji.guild) if emoji else ' '+emoji_name} for {message.author.name}",
            )
            await messagefuncs.sendWrappedMessage(custom_emoji, message.channel)
    except discord.InvalidArgument as e:
        await messagefuncs.sendWrappedMessage(
            f"There was an invalid argument error ({e}) when executing this command, please check that you are uploading the correct file type and try again!",
            message.author,
        )
        exc_type, exc_obj, exc_tb = exc_info()
        logger.info(f"CEF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
    except discord.Forbidden as e:
        await messagefuncs.sendWrappedMessage(
            f"There was a permissions error ({e}) when executing this command, please grant me the Manage Emojis permission and try again!",
            message.author,
        )
        exc_type, exc_obj, exc_tb = exc_info()
        logger.info(f"CEF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CEF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def clear_inbound_sync_function(message, client, args):
    global config
    try:
        for webhook in await message.channel.webhooks():
            if webhook.name.startswith(
                config.get("discord", dict()).get("botNavel", "botNavel") + " ("
            ):
                await webhook.delete()
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CISF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def add_inbound_sync_function(message, client, args):
    global ch
    try:
        fromChannelName = " ".join(args).strip()
        fromChannel = messagefuncs.xchannel(fromChannelName, message.guild)
        assert isinstance(fromChannel, discord.TextChannel)
        toChannel = message.channel

        logger.debug(f"Checking permissions for {message.author} on {fromChannel}")
        fromAdmin = ch.is_admin(
            fromChannel, fromChannel.guild.get_member(message.author.id)
        )
        logger.debug(fromAdmin)
        if not fromAdmin["channel"]:
            await message.add_reaction(
                ch.config.get(guild=fromChannel.guild, key="not-allowed-react")
            )
            await messagefuncs.sendWrappedMessage(
                "You aren't an admin (Manage Webhooks permission) on the target channel, refusing.",
                message.author,
            )
            return

        soon = client.get_emoji(664472443053932604)
        try:
            await message.add_reaction(soon)
        except (discord.Forbidden, discord.InvalidArgument):
            soon = "🔜"
            await message.add_reaction(soon)
        webhook = await toChannel.create_webhook(
            name=f"{ch.config.get(section='discord', key='botNavel')} ({fromChannel.guild.name}:{fromChannel.id})",
            reason=f"On behalf of {message.author.name}",
        )
        await message.remove_reaction(soon, client.user)
        await message.add_reaction("✅")
        if not ch.config.get(
            channel=message.channel.id, guild=message.guild.id, key="synchronize"
        ):
            await messagefuncs.sendWrappedMessage(
                f"Please note that the bridge that you just constructed will not be active until the server admin sets the `synchronize` key in the {fromChannel.guild.name} server configuration at https://fletcher.fun",
                message.author,
            )
        else:
            fromChannelName = f"{fromChannel.guild.name}:{fromChannel.id}"
            if ch.webhook_sync_registry.get(fromChannelName):
                ch.webhook_sync_registry[fromChannelName].append(toChannel, webhook)
            else:
                ch.webhook_sync_registry[fromChannelName] = commandhandler.Bridge()
                ch.webhook_sync_registry[fromChannelName].append(toChannel, webhook)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"AOSF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def names_sync_aware_function(message, client, args):
    global ch
    try:
        if type(message.channel) is discord.DMChannel:
            channel_name, args = consume_channel_token(args)
            if len(args):
                return
            channel = messagefuncs.xchannel(channel_name, message.guild)
        else:
            channel = message.channel
        if not channel or not discord.utils.get(channel.members, id=message.author.id):
            return
        message_body = "**Users currently in this channel**:\n"
        members = channel.members
        bridge_key = f"{channel.guild.name}:{channel.id}"
        bridge = ch.webhook_sync_registry.get(bridge_key)
        if bridge:
            for channel in bridge.channels:
                members.extend(channel.members)
        members = {
            member.id: member.display_name
            + (
                f" ({member.name}#{member.discriminator})"
                if member.name is not member.display_name
                else ""
            )
            for member in members
        }
        members = sorted(members.values())
        for member in members:
            member = member.split("*")
            if len(member) % 2 == 1 and len(member) > 1:
                member[-2] += "\\"
            member = "*".join(member)
            message_body += f"•{member}\n"
        message_body = message_body[:-1]
        target = (
            message.channel
            if "channel" in args and len(members) < 100
            else message.author
        )
        await messagefuncs.sendWrappedMessage(message_body, target)
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"NSAF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def delete_all_invites(message, client, args):
    try:
        invites = await message.guild.invites()
        for invite in invites:
            await invite.delete(reason=f"Obo {message.author.id}")
    except Exception as e:
        exc_type, exc_bj, exc_tb = exc_info()
        logger.error(f"DAI[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def voice_opt_out(message, client, args):
    try:
        if message.guild is None or len(args) > 0:
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(args[0], suffix="")
                .strip()
                .replace("_", " "),
            )
        else:
            guild = message.guild
        logger.debug(f"Leaving voice channels in {guild}")
        for voice_channel in filter(
            lambda channel: isinstance(channel, discord.VoiceChannel), guild.channels
        ):
            if voice_channel.permissions_for(message.author).connect:
                await voice_channel.set_permissions(
                    message.author, connect=False, read_messages=False
                )
                logger.debug(f"Removed {message.author} from {voice_channel}")
        await message.add_reaction("✅")
    except discord.Forbidden as e:
        await messagefuncs.sendWrappedMessage(e, message.author)
    except Exception as e:
        exc_type, exc_bj, exc_tb = exc_info()
        logger.error(f"VOO[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def error_report_function(error_str, guild, client):
    global ch
    automod = None
    scoped_config = ch.scope_config(guild=guild)
    users = (
        scoped_config.get(scoped_config.get("errorCC", "mod-userslist"))
        or guild.owner.id
    )
    users = list(load_config.expand_target_list(users, guild))
    for target in users:
        modmail = await messagefuncs.sendWrappedMessage(
            error_str, target, current_user_id=target.id
        )


async def delete_my_message_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) in [discord.Member, discord.User]:
            try:
                if message.author.id != client.user.id and not message.author.bot:
                    return
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
                    await message.delete()
                conn.commit()
            except discord.Forbidden as e:
                logger.warning("DMMF: Forbidden to delete self-message")
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"DMMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def set_slowmode_function(message, client, args):
    global config
    try:
        if len(message.channel_mentions) > 0:
            target = message.channel_mentions[0]
            if not target.permissions_for(message.author).manage_webhooks:
                logger.warning(
                    "SSMF: Forbidden to set slowmode without target admin privileges"
                )
                return
        else:
            target = message.channel
        await target.edit(slowmode_delay=int(args[0]))
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SSMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def unpin_message_function(message, client, args):
    global ch
    try:
        if args[2] != "remove":
            return
        if (
            ch.config.get(
                guild=message.guild,
                channel=message.channel,
                key="allow_unprivileged_unpins",
                default=False,
            )
            or (
                ch.config.get(
                    guild=message.guild,
                    channel=message.channel,
                    key="allow_unprivileged_selfunpins",
                    default=False,
                )
                and message.author == args[1]
            )
            or ch.is_admin(message, user=args[1])["channel"]
        ):
            if not message.channel.permissions_for(
                message.guild.get_member(client.user.id)
            ).manage_messages:
                return await messagefuncs.sendWrappedMessage(
                    "I don't have permission to unpin messages in this channel, presumably due to misconfiguration. Please ask an admin to grant me the Manage Messages permission and try again.",
                    args[1],
                )
            try:
                await message.unpin()
            except discord.HTTPException as e:
                await messagefuncs.sendWrappedMessage(
                    "Channel presumably has more than 50 pins, please ask a moderator to remove pins to add new ones and try again.",
                    args[1],
                )
            except discord.Forbidden:
                await messagefuncs.sendWrappedMessage(
                    "I don't have permission to unpin messages in this channel, presumably due to misconfiguration. Please ask an admin to grant me the Manage Messages permission and try again.",
                    args[1],
                )
        else:
            await messagefuncs.sendWrappedMessage(
                "Server is not configured to allow you to unpin messages in this channel. Ask an admin to set `allow_unprivileged_unpins` or `allow_unprivileged_selfunpins` to `On` to use this feature.",
                args[1],
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"UPNMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def pin_message_function(message, client, args):
    global ch
    try:
        if (
            ch.config.get(
                guild=message.guild,
                channel=message.channel,
                key="allow_unprivileged_pins",
                default=False,
            )
            or (
                ch.config.get(
                    guild=message.guild,
                    channel=message.channel,
                    key="allow_unprivileged_selfpins",
                    default=False,
                )
                and message.author == args[1]
            )
            or ch.is_admin(message, user=args[1])["channel"]
        ):
            if not message.channel.permissions_for(
                message.guild.get_member(client.user.id)
            ).manage_messages:
                return await messagefuncs.sendWrappedMessage(
                    "I don't have permission to pin messages in this channel, presumably due to misconfiguration. Please ask an admin to grant me the Manage Messages permission and try again.",
                    args[1],
                )
            try:
                await message.pin()
            except discord.HTTPException:
                await messagefuncs.sendWrappedMessage(
                    "Channel presumably has more than 50 pins, please ask a moderator to remove pins to add new ones and try again.",
                    args[1],
                )
            except discord.Forbidden:
                await messagefuncs.sendWrappedMessage(
                    "I don't have permission to pin messages in this channel, presumably due to misconfiguration. Please ask an admin to grant me the Manage Messages permission and try again.",
                    args[1],
                )
        else:
            await messagefuncs.sendWrappedMessage(
                "Server is not configured to allow you to pin messages in this channel. Ask an admin to set `allow_unprivileged_pins` or `allow_unprivileged_selfpins` to `On` to use this feature.",
                args[1],
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"PNMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def invite_function(message, client, args):
    global ch
    try:
        if len(message.channel_mentions) > 0:
            channel = message.channel_mentions[0]
        elif len(args) == 0 and message.guild is None:
            raise exceptions.DirectMessageException()
        elif type(message.channel) != discord.DMChannel:
            channel = message.channel
        else:
            channel_name, args = consume_channel_token(args)
            channel = (
                messagefuncs.xchannel(channel_name, message.guild) or message.channel
            )
        if type(channel) == discord.DMChannel or not channel:
            raise discord.InvalidArgument("Channel appears to not exist or is DM")
        localizedUser = channel.guild.get_member(message.author.id)
        if not (localizedUser and ch.is_admin(channel, localizedUser))["channel"]:
            return await messagefuncs.sendWrappedMessage(
                f"You do not have permission to invite users to {channel}.",
                message.author,
            )
        members = (
            message.mentions
            if len(message.mentions)
            else [
                ch.get_member_named(channel.guild, name)
                for name in map(
                    str.strip,
                    " ".join(args).split(",") if "," in " ".join(args) else args,
                )
            ]
        )
        # if not member:
        #     member = discord.utils.find(lambda member: member.name == name or member.display_name == name, await client.get_all_members())

        soon = client.get_emoji(664472443053932604) or "🔜"
        await message.add_reaction(soon)
        for member in filter(lambda member: member and member.bot, members):
            await channel.set_permissions(
                member,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                reason="Invited by channel admin",
            )

        async def invite_member(client, member, message):
            try:
                target = await messagefuncs.sendWrappedMessage(
                    f"{message.author.display_name} cordially invites you to {channel.mention} - to accept this invitation, react with a ✅",
                    member,
                )
                await target.add_reaction("✅")
            except discord.Forbidden:
                return await messagefuncs.sendWrappedMessage(
                    f"Couldn't send invite to {member}: discord.Forbidden",
                    message.author,
                )
            try:
                reaction = await client.wait_for(
                    "raw_reaction_add",
                    timeout=60000.0 * 24,
                    check=lambda reaction: reaction.message_id == target.id
                    and (str(reaction.emoji) == "✅")
                    and (reaction.user_id == member.id),
                )
            except asyncio.TimeoutError:
                await target.edit(
                    content=f"{target.content}\nInvite expired due to timeout. You'll need to ask them for another invitation to join."
                )
                await message.remove_reaction("✅", client.user)
                return
            try:
                await channel.set_permissions(
                    member,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    reason="Invited by channel admin",
                )
                await messagefuncs.sendWrappedMessage(
                    f"{member} accepted your invite to {channel.mention}",
                    message.author,
                )
            except discord.Forbidden:
                await target.edit(
                    content=f"{target.content}\nFailed to add you to channel due to a permissions error. Your inviter has been notified."
                )
                return await messagefuncs.sendWrappedMessage(
                    f"Couldn't set channel override for accepted invite to {member}: discord.Forbidden",
                    message.author,
                )

        await asyncio.gather(
            *[
                invite_member(client, member, message)
                for member in filter(lambda member: member and not member.bot, members)
            ]
        )

        await message.remove_reaction(soon, client.user)
        await message.add_reaction("✅")
    except discord.Forbidden as e:
        return await messagefuncs.sendWrappedMessage(
            f"Permissions error while inviting: {e}.", message.author
        )
    except discord.InvalidArgument:
        return await messagefuncs.sendWrappedMessage(
            f"Invalid arguments, could not infer channel or user: {e}", message.author
        )
    except exceptions.DirectMessageException:
        return await messagefuncs.sendWrappedMessage(
            "Inviting to a channel from a DM requires server and channel to be specified (e.g. `!invite server:channel username`)",
            message.author,
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ICF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def self_service_thread_function(message, client, args):
    global ch
    try:
        if not message.channel.permissions_for(message.author).create_private_threads:
            await messagefuncs.sendWrappedMessage(
                f"You don't have permission to use a self-service thread function because you don't have create private threads permissions.",
                message.author,
            )
            return
        if len(args) == 3 and type(args[1]) is discord.Member:
            if args[2] == "add":
                try:
                    now = datetime.now(timezone.utc)
                    thread = await message.channel.create_thread(name=str(now))
                    members_to_add = [args[1]]
                    for r in message.role_mentions:
                        members_to_add.extend(r.members)
                    members_to_add.extend(message.mentions)
                    for m in list(set(members_to_add)):
                        await thread.add_membe(m)
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(
                        f"I don't have permission to create thread for __@{message.jump_url}__, and {args[1]} requested an add.",
                        message.author,
                    )
        else:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, 'threadselfmanage-{message.id}', %s) ON CONFLICT DO NOTHING;",
                [message.author.id, message.guild.id, str(message.id)],
            )
            conn.commit()
            ch.add_message_reaction_handler(
                [message.id],
                commandhandler.Command(
                    function=self_service_thread_function,
                    exclusive=True,
                    sync=False,
                    description="add user to created thread",
                ),
            )
            await message.add_reaction("🚪")
            await messagefuncs.sendWrappedMessage(
                f"Linked reactions on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} to thread creation",
                message.author,
            )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SSTF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def self_service_role_function(message, client, args):
    global ch
    try:
        if not len(message.role_mentions):
            return
        if not (
            message.author.id
            in ch.config.get(
                guild=message.guild,
                key=f"roleadmin-{message.role_mentions[0].name}-list",
                default=[],
            )
            or message.author.guild_permissions.manage_roles
        ):
            await messagefuncs.sendWrappedMessage(
                f"You don't have permission to use a self-service channel role function because you don't have manage roles permissions.",
                message.author,
            )
            return
        if len(args) == 3 and type(args[1]) is discord.Member:
            if args[2] == "add":
                try:
                    await args[1].add_roles(message.role_mentions[0])
                    if ch.config.normalize_booleans(
                        ch.user_config(
                            message.author.id,
                            message.guild.id,
                            "notifications-openrole",
                            default=True,
                            allow_global_substitute=True,
                        )
                    ):
                        await messagefuncs.sendWrappedMessage(
                            f"Added {args[1]} to role __@{message.role_mentions[0].name}__",
                            message.author,
                        )
                    await messagefuncs.sendWrappedMessage(
                        f"Added you to role __@{message.role_mentions[0].name}__",
                        args[1],
                    )
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(
                        f"I don't have permission to manage role __@{message.role_mentions[0].name}__, and {args[1]} requested an add.",
                        message.author,
                    )
            else:
                try:
                    await args[1].remove_roles(message.role_mentions[0])
                    if ch.config.normalize_booleans(
                        ch.user_config(
                            message.author.id,
                            message.guild.id,
                            "notifications-openrole",
                            default=True,
                            allow_global_substitute=True,
                        )
                    ):
                        await messagefuncs.sendWrappedMessage(
                            f"Removed {args[1]} from role __@{message.role_mentions[0].name}__",
                            message.author,
                        )
                    await messagefuncs.sendWrappedMessage(
                        f"Removed you from role __@{message.role_mentions[0].name}__",
                        args[1],
                    )
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(
                        f"I don't have permission to manage role __@{message.role_mentions[0].name}__, and {args[1]} requested removal.",
                        message.author,
                    )
        else:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, 'roleselfmanage-{message.id}', %s) ON CONFLICT DO NOTHING;",
                [message.author.id, message.guild.id, str(message.id)],
            )
            conn.commit()
            ch.add_message_reaction_remove_handler(
                [message.id],
                {
                    "trigger": [""],  # empty string: a special catch-all trigger
                    "function": self_service_role_function,
                    "exclusive": True,
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "remove user from role for a given message",
                },
            )
            ch.add_message_reaction_handler(
                [message.id],
                commandhandler.Command(
                    function=self_service_role_function,
                    exclusive=True,
                    sync=False,
                    description="add user to role for a given message",
                ),
            )
            await message.add_reaction("🚪")
            await messagefuncs.sendWrappedMessage(
                f"Linked reactions on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} to role __#{message.role_mentions[0].name}__",
                message.author,
            )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SSRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


@lru_cache(maxsize=256)
def get_warnlist(user, guild):
    if hasattr(user, "id"):
        user = user.id
    if hasattr(guild, "id"):
        guild = guild.id
    warnlist = ch.config.normalize_array(
        ch.user_config(
            user,
            guild,
            "warnlist",
            allow_global_substitute=True,
        )
        or ch.config.get("warnlist", default=[], guild=guild)
    )
    if len(warnlist) == 1 and warnlist[0].startswith("delegate:"):
        warnlist = ch.config.normalize_array(
            ch.user_config(
                int(warnlist[0].split(":")[1]),
                guild,
                "warnlist",
                allow_global_substitute=True,
            )
            or ch.config.get("warnlist", default=[], guild=guild)
        )
    warnlist = {int(warn.split("=")[0]): warn.split("=")[1] for warn in warnlist}
    logger.debug(f"{warnlist}")
    return warnlist


async def self_service_channel_function(
    message, client, args, autoclose=False, confirm=False
):
    global ch
    try:
        if not len(message.channel_mentions):
            await messagefuncs.sendWrappedMessage(
                "Could not link reactions, no channel mention found in message.",
                message.author,
            )
            return
        if not ch.is_admin(message.channel_mentions[0], message.author)["channel"]:
            await messagefuncs.sendWrappedMessage(
                f"You don't have permission to set up a self-service channel reaction function via {message.jump_url} because you don't have channel admin permissions.",
                message.author,
            )
            return
        if not ch.is_admin(message.channel, message.author)["channel"] and autoclose:
            await messagefuncs.sendWrappedMessage(
                f"You don't have permission to set up an autoclosing self-service channel reaction function via {message.jump_url} because you don't have channel admin permissions.",
                message.author,
            )
            return
        if (
            len(args) == 3
            and args[2] == "add"
            and get_warnlist(message.author.id, message.guild.id).get(args[1].id)
        ):
            confirm = get_warnlist(message.author.id, message.guild.id)[args[1].id]
        if len(args) == 3 and type(args[1]) is discord.Member:
            if args[2] == "add":
                try:
                    if confirm:
                        confirmMessage = f"{args[1].mention} ({str(args[0].emoji)}) requests entry to channel __#{message.channel_mentions[0].name}__, to confirm entry react with a checkmark. If you do not wish to grant entry, no further action is required."
                        if isinstance(confirm, str):
                            confirmMessage += "\n"
                            confirmMessage += f"Heads up! Your warnlist has triggered a confirmation before adding this user with the message '{confirm}'"
                        confirmMessage = await messagefuncs.sendWrappedMessage(
                            confirmMessage,
                            message.author,
                        )
                        await confirmMessage.add_reaction("✅")
                        try:
                            reaction = await client.wait_for(
                                "raw_reaction_add",
                                timeout=60000.0 * 24,
                                check=lambda reaction: reaction.message_id
                                == confirmMessage.id
                                and (str(reaction.emoji) == "✅")
                                and (reaction.user_id == message.author.id),
                            )
                        except asyncio.TimeoutError:
                            await confirmMessage.edit(
                                content=f"~~{confirmMessage.content}~~Request expired due to timeout."
                            )
                            await confirmMessage.remove_reaction("✅", client.user)
                            return
                    await message.channel_mentions[0].set_permissions(
                        args[1],
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                    )
                    voice_channel = discord.utils.get(
                        message.guild.voice_channels,
                        name=message.channel_mentions[0].name,
                    )
                    if voice_channel and "+voice" in message.content:
                        await voice_channel.set_permissions(
                            args[1],
                            connect=True,
                            speak=True,
                        )
                    if not autoclose:
                        await messagefuncs.sendWrappedMessage(
                            f"Added {args[1]} ({str(args[0].emoji)}) to channel __#{message.channel_mentions[0].name}__",
                            message.author,
                        )
                        await messagefuncs.sendWrappedMessage(
                            f"Added you to channel __#{message.channel_mentions[0].name}__ ({message.channel_mentions[0].mention}) by your own request (reacted with {str(args[0].emoji)} to <{message.jump_url}>).",
                            args[1],
                        )
                    else:
                        await message.channel.set_permissions(
                            args[1],
                            read_messages=False,
                            send_messages=False,
                            read_message_history=False,
                        )
                        if ch.config.normalize_booleans(
                            ch.user_config(
                                message.author.id,
                                message.guild.id,
                                "notifications-openchannel",
                                default=True,
                                allow_global_substitute=True,
                            )
                        ):
                            await messagefuncs.sendWrappedMessage(
                                f"Added {args[1]} to channel __#{message.channel_mentions[0].name}__, and removed {args[1]} from channel __#{message.channel.name}__",
                                message.author,
                            )
                        await messagefuncs.sendWrappedMessage(
                            f"Added you to channel __#{message.channel_mentions[0].name}__, and removed you from channel __#{message.channel.name}__ by your own request (reacted to <{message.jump_url}>)",
                            args[1],
                        )
                except discord.Forbidden as e:
                    await messagefuncs.sendWrappedMessage(
                        f"I don't have permission to manage members (Manage Permissions) on __#{message.channel_mentions[0].name}__, and {args[1]} requested an add\n{e}.",
                        message.author,
                    )
            elif args[2] != "add" and args[1].id != message.author.id:
                try:
                    currentPermissions = message.channel_mentions[0].permissions_for(
                        args[1]
                    )
                    if not (
                        currentPermissions.read_messages
                        or currentPermissions.send_messages
                        or currentPermissions.read_message_history
                    ):
                        return
                    await message.channel_mentions[0].set_permissions(
                        args[1],
                        read_messages=False,
                        send_messages=False,
                        read_message_history=False,
                    )
                    voice_channel = discord.utils.get(
                        message.guild.voice_channels,
                        name=message.channel_mentions[0].name,
                    )
                    if voice_channel and "+voice" in message.content:
                        await voice_channel.set_permissions(
                            args[1],
                            connect=False,
                            speak=False,
                        )
                    await messagefuncs.sendWrappedMessage(
                        f"Removed {args[1]} from channel __#{message.channel_mentions[0].name}__",
                        message.author,
                    )
                    await messagefuncs.sendWrappedMessage(
                        f"Removed you from channel __#{message.channel_mentions[0].name}__ by your own request (removed reaction from {message.jump_url})",
                        args[1],
                    )
                except discord.Forbidden:
                    await messagefuncs.sendWrappedMessage(
                        f"I don't have permission to manage members of __#{message.channel_mentions[0].name}__, and {args[1]} requested removal.",
                        message.author,
                    )
        else:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, 'chanselfmanage{'autoclose' if autoclose else 'confirm' if confirm else ''}', %s) ON CONFLICT DO NOTHING;",
                [message.author.id, message.guild.id, str(message.id)],
            )
            conn.commit()
            ch.add_message_reaction_remove_handler(
                [message.id],
                {
                    "trigger": [""],  # empty string: a special catch-all trigger
                    "function": partial(
                        self_service_channel_function,
                        autoclose=autoclose,
                        confirm=confirm,
                    ),
                    "exclusive": True,
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "remove user from channel for a given message",
                },
            )
            ch.add_message_reaction_handler(
                [message.id],
                commandhandler.Command(
                    function=partial(
                        self_service_channel_function,
                        autoclose=autoclose,
                        confirm=confirm,
                    ),
                    exclusive=True,
                    sync=False,
                    description="add user to channel for a given message",
                ),
            )
            await message.add_reaction("🚪")
            await messagefuncs.sendWrappedMessage(
                f"Linked reactions on https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} to channel read/write/read history {'with confirmation ' if confirm else ''}on #{message.channel_mentions[0].name}{'. I do not have Manage Permissions on your channel though, please do add that or users will not be successfully added/removed from the channel.' if not message.channel_mentions[0].permissions_for(message.guild.get_member(client.user.id)).manage_permissions else ''}",
                message.author,
            )
            err = (
                f"{message.author.name} attempted to link reactions for #{message.channel_mentions[0].name} to a catcher but I don't have Manage Permissions in there. This may cause issues.",
            )
            if (
                not message.channel_mentions[0]
                .permissions_for(message.guild.get_member(client.user.id))
                .manage_permissions
            ):
                await error_report_function(err, message.guild, client)
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        logger.debug(traceback.format_exc())
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SSCF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def login_function(message, client, args):
    global ch
    if args[0] == "pocket":
        async with aiohttp.ClientSession() as session:
            params = aiohttp.FormData()
            params.add_field(
                "consumer_key", ch.config.get(section="pocket", key="consumer_key")
            )
            params.add_field(
                "redirect_uri", ch.config.get(section="pocket", key="redirect_uri")
            )
            params.add_field("state", str(message.author.id))
            async with session.post(
                "https://getpocket.com/v3/oauth/request", data=params
            ) as resp:
                request_body = (await resp.read()).decode("UTF-8")
                request_token = request_body.split("=")[1]
                return await messagefuncs.sendWrappedMessage(
                    f"https://getpocket.com/auth/authorize?request_token={request_token}&redirect_uri={ch.config.get(section='pocket', key='redirect_uri')}%3Frequest_token%3D{request_token}",
                    message.channel,
                )
    elif args[0] == "complice":
        return await messagefuncs.sendWrappedMessage(
            f"https://complice.co/oauth/authorize?response_type=code&client_id={ch.config.get(section='complice', key='client_key')}&client_secret={ch.config.get(section='complice', key='client_secret')}&redirect_uri={ch.config.get(section='complice', key='redirect_uri')}&state={message.author.id}",
            message.channel,
        )
    elif args[0] == "thingiverse":
        return await messagefuncs.sendWrappedMessage(
            f"https://www.thingiverse.com/login/oauth/authorize?response_type=code&client_id={ch.config.get(section='thingiverse', key='client_key')}&redirect_uri={ch.config.get(section='thingiverse', key='redirect_uri')}&state={message.author.id}",
            message.channel,
        )
    elif args[0] == "trello":
        return await messagefuncs.sendWrappedMessage(
            f"https://trello.com/1/authorize?return_url={ch.config.get(section='trello', key='redirect_uri')}%26state={message.author.id}&response_type=postMessage&expiration=never&name={client.user.name}&scope=read,write&response_type=token&key={ch.config.get(section='trello', key='client_key')}",
            message.channel,
        )
    elif args[0] == "glowfic":
        return await messagefuncs.sendWrappedMessage(
            f"http://gabriel.noblejury.com:3002/oauth/authorize?response_type=code&client_id={ch.config.get(section='glowfic', key='client_key')}&redirect_uri={ch.config.get(section='glowfic', key='redirect_uri')}&state={message.author.id}",
            message.channel,
        )
    else:
        return await messagefuncs.sendWrappedMessage(
            f"Could not find matching service login flow for {args[0]}", message.channel
        )


async def toggle_mute_channel_function(message, client, args):
    try:
        for member in discord.utils.get(
            message.guild.voice_channels, name=" ".join(args)
        ).members:
            await member.edit(mute=not member.voice.mute)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TMCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def toggle_mute_role_function(message, client, args):
    try:
        role = discord.utils.get(message.guild.roles, name=" ".join(args))
        new_permissions = role.permissions
        new_permissions.update(speak=not role.permissions.speak)
        await role.edit(permissions=new_permissions)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TMCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def nick_change_function(message, client, args):
    try:
        if not message.guild:
            return
        if message.author.guild_permissions.manage_nicknames or (
            message.guild.get_role(
                int(ch.config.get(guild=message.guild, key="nick-changeadmin-role"))
            )
            in message.author.roles
            and message.guild.get_role(
                int(ch.config.get(guild=message.guild, key="nick-changeme-role"))
            )
            in message.mentions[0].roles
        ):
            await message.mentions[0].edit(
                nick=" ".join(args[1:]), reason=f"On behalf of {message.author}"
            )
            await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"NCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!rolecolor", "!rolecolour"],
            "function": set_role_color_function,
            "async": True,
            "admin": "server",
            "args_num": 2,
            "args_name": ["Role_Name", "rrggbb"],
            "description": "Set Role Color",
        }
    )
    ch.add_command(
        {
            "trigger": ["!roleadd", "!addrole"],
            "function": addrole_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "args_name": [],
            "description": "Add role (self-assignable by default)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!roledel", "!delrole"],
            "function": delrole_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "args_name": [],
            "description": "Delete role",
        }
    )
    ch.add_command(
        {
            "trigger": ["!revoke"],
            "function": revokerole_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "args_name": [],
            "description": "Revoke role `!revoke rolename from me`",
        }
    )
    ch.add_command(
        {
            "trigger": ["!assign"],
            "function": assignrole_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "args_name": [],
            "description": "Assign role `!assign rolename to me`",
        }
    )
    ch.add_command(
        {
            "trigger": ["!modping"],
            "function": modping_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "args_name": [],
            "description": "Ping unpingable roles (Admin)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!modreport", "👁‍🗨"],
            "function": modreport_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Report message to mods. Removed immediately after (if reaction).",
        }
    )
    ch.add_command(
        {
            "trigger": ["!lastactive_channel", "!lastactivity_channel", "!lsc"],
            "function": lastactive_channel_function,
            "async": True,
            "long_run": True,
            "admin": "server",
            "args_num": 0,
            "long_run": "author",
            "args_name": [],
            "description": "List all available channels and time of last message (Admin)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!lastactive_user", "!lastactivity_user", "!lsu"],
            "function": lastactive_user_function,
            "async": True,
            "admin": "server",
            "args_num": 0,
            "args_name": [],
            "description": "List all available users and time of last message (Admin)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!kick"],
            "function": kick_user_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "args_name": ["@user", "reason"],
            "description": "Kick user from server, and send them a message with the reason.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!lockout"],
            "function": lockout_user_function,
            "async": True,
            "admin": "server",
            "args_num": 1,
            "long_run": "author",
            "args_name": ["@user", "reset|hide"],
            "description": "Lockout or reset user permissions",
        }
    )
    ch.add_command(
        {
            "trigger": ["!optin"],
            "function": optin_channel_function,
            "async": True,
            "hidden": True,
            "admin": "global",
            "args_num": 0,
            "args_name": ["#channel"],
            "description": "Join a channel, no arguments to list available channels.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!voiceoptout"],
            "function": voice_opt_out,
            "async": True,
            "args_num": 0,
            "args_name": [""],
            "description": "Leave all voice channels for current guild. Cannot be reversed except by admin.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!part", "!optout"],
            "function": part_channel_function,
            "async": True,
            "args_num": 0,
            "args_name": ["#channel"],
            "description": "Leave a channel. Cannot be reversed except by admin.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!part"],
            "function": part_channel_function,
            "async": True,
            "args_num": 1,
            "args_min": 0,
            "args_name": ["channel;Channel Name"],
            "description": "Leave a channel. Cannot be reversed except by admin.",
            "slash_command": True,
            "whitelist_guild": [
                634249282488107028,
                345045447745732608,
                630487117688078358,
            ],
        }
    )
    ch.add_command(
        {
            "trigger": ["!snooze"],
            "function": snooze_channel_function,
            "async": True,
            "args_num": 0,
            "args_name": ["#channel"],
            "description": "Leave a channel. Reversed in 24 hours.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!sudo"],
            "function": sudo_function,
            "async": True,
            "admin": "server",
            "args_num": 0,
            "args_name": [],
            "description": "Elevate permissions for one command",  # by assigning a temporary admin-grant role
        }
    )
    ch.add_command(
        {
            "trigger": ["!chanlog"],
            "function": chanlog_function,
            "async": True,
            "admin": "channel",
            "long_run": "author",
            "args_num": 0,
            "args_name": [],
            "description": "Dump channel logs to a pastebin",
        }
    )
    ch.add_command(
        {
            "trigger": ["!delete_all_invites"],
            "function": delete_all_invites,
            "async": True,
            "admin": "server",
            "long_run": "channel",
            "args_num": 0,
            "args_name": [],
            "description": "Delete all invites for this server",
        }
    )
    ch.add_command(
        {
            "trigger": ["!copy_emoji", "!esteal", "!laestse"],
            "function": copy_emoji_function,
            "async": True,
            "args_num": 1,
            "args_name": ["reaction name", "offset (optional)"],
            "description": "Copy emoji to this server",
        }
    )
    ch.add_command(
        {
            "trigger": ["!copy_permissions_from"],
            "function": copy_permissions_function,
            "async": True,
            "long_run": "channel",
            "args_num": 1,
            "args_name": ["#source-channel", "#target-channel (optional)"],
            "description": "Copy channel permission overrides from a source channel",
        }
    )
    ch.add_command(
        {
            "trigger": ["!bridge"],
            "function": add_inbound_sync_function,
            "async": True,
            "hidden": False,
            "admin": "channel",
            "args_num": 1,
            "args_name": ["#channel"],
            "description": "Add inbound sync bridge from the current channel to the specified server-channel identifer",
        }
    )
    ch.add_command(
        {
            "trigger": ["!demolish"],
            "function": clear_inbound_sync_function,
            "async": True,
            "hidden": False,
            "admin": "channel",
            "args_num": 0,
            "args_name": [],
            "description": "Clear all inbound sync bridge(s) from the current channel",
        }
    )
    ch.add_command(
        {
            "trigger": ["!names"],
            "function": names_sync_aware_function,
            "async": True,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": 'List all users that have access to this channel, including synced users. Equivalent to IRC "NAMES" command',
        }
    )
    ch.add_command(
        {
            "trigger": ["❌", "<:deletethispost:787460478527078450>", "✖️"],
            "function": delete_my_message_function,
            "async": True,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "Delete a Fletcher message if you're responsible for it",
        }
    )
    ch.add_command(
        {
            "trigger": ["!cooldown", "!slowmode"],
            "function": set_slowmode_function,
            "async": True,
            "hidden": False,
            "admin": "channel",
            "args_num": 1,
            "args_name": ["Seconds"],
            "description": "Set channel slow-mode time",
        }
    )

    ch.add_command(
        {
            "trigger": ["📍"],
            "function": pin_message_function,
            "async": True,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "Pin message as a non-admin (if enabled in this channel)",
        }
    )

    ch.add_command(
        {
            "trigger": ["📍"],
            "function": unpin_message_function,
            "remove": True,
            "async": True,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "(On removing this emoji) Unpin message as a non-admin (if enabled in this channel)",
        }
    )

    ch.add_command(
        {
            "trigger": ["!topic"],
            "function": lambda message, client, args: f"#{message.channel.name} topic: {message.channel.topic}",
            "async": False,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "Get channel topic",
        }
    )

    ch.add_command(
        {
            "trigger": ["!login"],
            "function": login_function,
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": ["[pocket|complice|thingiverse|trello]"],
            "description": "Authenticate with an external service",
        }
    )

    ch.add_command(
        {
            "trigger": ["!invite"],
            "function": invite_function,
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": ["Username (optional discriminator)"],
            "description": "Invite user to a channel (requires channel admin permissions)",
        }
    )

    ch.add_command(
        {
            "trigger": ["!requestinvitechannel"],
            "function": partial(self_service_channel_function, confirm=True),
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": ["#channel"],
            "description": "Create message that will automatically add and remove users from a channel with a filter for confirmation.",
        }
    )

    ch.add_command(
        {
            "trigger": ["!clopenchannel"],
            "function": partial(self_service_channel_function, autoclose=True),
            "admin": "channel",
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": ["#channel"],
            "description": "Create message that will automatically add and remove users from a channel",
        }
    )

    ch.add_command(
        {
            "trigger": ["!openchannel"],
            "function": self_service_channel_function,
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": ["#channel"],
            "description": "Create message that will automatically add and remove users from a channel",
        }
    )

    ch.add_command(
        {
            "trigger": ["!threadhub"],
            "function": self_service_thread_function,
            "async": True,
            "hidden": False,
            "args_num": 0,
            "args_name": ["@mentions"],
            "description": "Create message that will automatically create private threads with the reactor and users mentioned in the message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!togglemutechannel"],
            "function": toggle_mute_channel_function,
            "async": True,
            "hidden": False,
            "admin": "server",
            "args_num": 1,
            "args_name": ["#channel"],
            "description": "Toggle server mute on all voice chat members",
        }
    )

    ch.add_command(
        {
            "trigger": ["!togglemuterole"],
            "function": toggle_mute_role_function,
            "async": True,
            "hidden": False,
            "admin": "server",
            "args_num": 1,
            "args_name": ["rolename"],
            "description": "Toggle speak on role",
        }
    )

    ch.add_command(
        {
            "trigger": ["!nick"],
            "function": nick_change_function,
            "async": True,
            "hidden": False,
            "args_num": 2,
            "args_name": ["@user_mention", "nickname"],
            "description": "Set nickname for user mentioned",
        }
    )

    def load_self_service_channels(ch):
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, guild_id, key, value FROM user_preferences WHERE key LIKE 'chanselfmanage%';"
        )
        subtuple = cur.fetchone()
        while subtuple:
            message_id = int(subtuple[3])
            logger.debug(f"adding channel management message handler {subtuple}")
            ch.add_message_reaction_remove_handler(
                [message_id],
                {
                    "trigger": [""],  # empty string: a special catch-all trigger
                    "function": partial(
                        self_service_channel_function,
                        autoclose=subtuple[2].endswith("autoclose"),
                        confirm=subtuple[2].endswith("confirm"),
                    ),
                    "exclusive": True,
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "remove user from channel for a given message",
                },
            )
            ch.add_message_reaction_handler(
                [message_id],
                commandhandler.Command(
                    function=partial(
                        self_service_channel_function,
                        autoclose=subtuple[2].endswith("autoclose"),
                        confirm=subtuple[2].endswith("confirm"),
                    ),
                    exclusive=True,
                    sync=False,
                    description="add user to channel for a given message",
                ),
            )
            subtuple = cur.fetchone()
        conn.commit()

    ch.add_command(
        {
            "trigger": ["!openrole"],
            "function": self_service_role_function,
            "async": True,
            "hidden": False,
            "args_num": 1,
            "args_name": ["@role"],
            "description": "Create message that will automatically add and remove users from a role",
        }
    )

    def load_self_service_threads(ch):
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, guild_id, key, value FROM user_preferences WHERE key LIKE 'threadselfmanage%';"
        )
        subtuple = cur.fetchone()
        while subtuple:
            message_id = int(subtuple[3])
            logger.debug(f"adding thread management message handler {subtuple}")
            ch.add_message_reaction_handler(
                [message_id],
                commandhandler.Command(
                    function=self_service_thread_function,
                    exclusive=True,
                    sync=False,
                    description="add user to created thread",
                ),
            )
            subtuple = cur.fetchone()
        conn.commit()

    def load_self_service_roles(ch):
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, guild_id, key, value FROM user_preferences WHERE key LIKE 'roleselfmanage%';"
        )
        subtuple = cur.fetchone()
        while subtuple:
            message_id = int(subtuple[3])
            logger.debug(f"adding role management message handler {subtuple}")
            ch.add_message_reaction_remove_handler(
                [message_id],
                {
                    "trigger": [""],  # empty string: a special catch-all trigger
                    "function": self_service_role_function,
                    "exclusive": True,
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "remove user from role for a given message",
                },
            )
            ch.add_message_reaction_handler(
                [message_id],
                commandhandler.Command(
                    function=self_service_role_function,
                    exclusive=True,
                    sync=False,
                    description="add user to role for a given message",
                ),
            )
            subtuple = cur.fetchone()
        conn.commit()

    for guild in ch.client.guilds:
        rml = ch.config.get(guild=guild, key="role-message-list")
        if rml and len(rml):
            logger.debug(f"adding role emoji handler for {guild.name}")
            ch.add_message_reaction_remove_handler(
                rml,
                {
                    "trigger": [""],  # empty string: a special catch-all trigger
                    "function": lambda message, client, args: role_message_function(
                        message, client, args, remove=True
                    ),
                    "exclusive": True,
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "assign roles based on emoji for a given message",
                },
            )
            ch.add_message_reaction_handler(
                rml,
                commandhandler.Command(
                    function=role_message_function,
                    exclusive=True,
                    sync=False,
                    description="assign roles based on emoji for a given message",
                ),
            )

    load_self_service_channels(ch)
    load_self_service_roles(ch)
    load_self_service_threads(ch)


async def autounload(ch):
    pass
