import asyncio
from datetime import datetime, timedelta
import dateparser.search
import discord
import logging
import messagefuncs
from sys import exc_info
import random
import textwrap
import text_manipulators
import ujson
import exceptions

# global conn set by reload_function

logger = logging.getLogger("fletcher")


async def set_role_color_function(message, client, args):
    global config
    global ch
    guild_config = ch.scope_config(guild=message.guild)
    try:
        role_list = message.channel.guild.roles
        role = discord.utils.get(role_list, name=args[0].replace("_", " "))
        if role is None and (
            guild_config.get(
                "color-role-autocreate", config.get("color-role-autocreate", "On")
            )
            == "On"
        ):
            role = await message.guild.create_role(
                name=args[0], reason="Auto-created color role"
            )
        if role is not None:
            if args[1].startswith("random"):
                args[1] = "#%06x" % random.randint(0, 0xFFFFFF)
                await message.channel.send(f"Setting color of {args[0]} to {args[1]}")
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
            await message.author.send(
                "Unable to find matching role to set color, create this role before trying to set its color."
            )
    except discord.Forbidden as e:
        await message.author.send(
            "Unable to set role color, am I allowed to edit this role?  My role must be above the target in the heirarchy, and I must have the Manage Roles permission."
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
                    argString.trim().replace(" and ", "").replace(", ", "").split(" ")
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
                        err = (
                            err
                            + " `!revoke "
                            + role.name
                            + " from me` to remove this role from yourself."
                        )
                    else:
                        err = (
                            err
                            + " `!assign "
                            + role.name
                            + " to me` to add this role to yourself."
                        )
                else:
                    if role in message.author.roles:
                        err = (
                            err
                            + " An administrator can `!revoke "
                            + role.name
                            + " from @"
                            + str(message.author.id)
                            + "` to remove this role from you."
                        )
                    else:
                        err = (
                            err
                            + " An administrator can `!assign "
                            + role.name
                            + " to @"
                            + str(message.author.id)
                            + "` to add this role to you."
                        )
                return await message.channel.send(err)
            else:
                role = await message.channel.guild.create_role(
                    name=roleProperties["name"],
                    colour=roleProperties["colour"],
                    mentionable=True,
                    reason="Role added on behalf of " + str(message.author.id),
                )
                await message.channel.send(
                    "Role " + role.mention + " successfully created."
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
                        return await message.channel.send(
                            "You already have that role, `!revoke "
                            + role.name
                            + " from me` to remove this role from yourself."
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
                        return await message.channel.send(
                            "Role assigned, `!revoke "
                            + role.name
                            + " from me` to remove this role from yourself."
                        )
                else:
                    # TODO unimplemented
                    pass
                    if role in message.author.roles:
                        err = (
                            err
                            + " An administrator can `!revoke "
                            + role.name
                            + " from @"
                            + str(message.author.id)
                            + "` to remove this role from you."
                        )
                    else:
                        err = (
                            err
                            + " An administrator can `!assign "
                            + role.name
                            + " to @"
                            + str(message.author.id)
                            + "` to add this role to you."
                        )
                return await message.channel.send(err)
            else:
                await message.channel.send(
                    "Role "
                    + roleProperties["name"]
                    + " does not exist, use the addrole command to create it."
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
                        return await message.channel.send(
                            "Role revoked, `!assign "
                            + role.name
                            + " to me` to add this role to yourself."
                        )
                    else:
                        return await message.channel.send(
                            "You don't have that role, `!assign "
                            + role.name
                            + " to me` to assign this role to yourself."
                        )
                else:
                    # TODO unimplemented
                    pass
                    if role in message.author.roles:
                        err = (
                            err
                            + " An administrator can `!revoke "
                            + role.name
                            + " from @"
                            + str(message.author.id)
                            + "` to remove this role from you."
                        )
                    else:
                        err = (
                            err
                            + " An administrator can `!assign "
                            + role.name
                            + " to @"
                            + str(message.author.id)
                            + "` to add this role to you."
                        )
                return await message.channel.send(err)
            else:
                await message.channel.send(
                    "Role "
                    + roleProperties["name"]
                    + " does not exist, use the addrole command to create it."
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
                    await message.channel.send(
                        "Role `@" + roleProperties["name"] + "` deleted."
                    )
                else:
                    await message.channel.send(
                        "You do not have permission to delete role `@"
                        + roleProperties["name"]
                        + "`."
                    )
            else:
                err = "Role `@" + roleProperties["name"] + "` does not exist!"
                if message.channel.permissions_for(message.author).manage_messages:
                    err = err + " `!addrole " + role.name + "` to add this role."
                else:
                    err = (
                        err
                        + " An administrator can `!addrole "
                        + role.name
                        + "` to add this role."
                    )
                await message.channel.send(err)
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

                def gaveled_by_admin_check(reaction, user):
                    return (
                        user.guild_permissions.manage_webhooks
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
                    reaction, user = await client.wait_for(
                        "reaction_add", timeout=6000.0, check=gaveled_by_admin_check
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
            mentionPing = await message.channel.send(
                message.author.name + " pinging " + role.mention
            )
            if not lay_mentionable:
                await role.edit(mentionable=False)
            if "snappy" in config["discord"] and config["discord"]["snappy"]:
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
        if scoped_config.get("moderation") != "On":
            logger.info(f"Moderation disabled on guild {message.guild}")
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
            users = scoped_config["mod-users"].split(",")
        else:
            users = scoped_config["manual-mod-users"].split(",")
        users = list(expand_target_list(users, message.guild))
        for target in users:
            modmail = await messagefuncs.sendWrappedMessage(report_content, target)
            if message.channel.is_nsfw():
                await modmail.add_reaction("🕜")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


def expand_target_list(targets, guild):
    inputs = list(targets)
    targets = set()
    for target in inputs:
        if target.startswith("r:"):
            members = guild.get_role(int(target[2:])).members
            targets.update(set(members))
        elif target.startswith("c:"):
            channel = guild.get_channel(int(target[2:]))
            targets.add(channel)
        else:
            # ID asssumed to be targets
            targets.add(guild.get_member(int(target)))
    return targets


async def lastactive_channel_function(message, client, args):
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
            client.request_offline_members(message.guild)
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
                    logMessage = (
                        str(member)
                        + " from non-category channel "
                        + str(channel)
                        + " in "
                        + str(member.guild)
                    )
                    logger.debug("LUF: " + logMessage)
                    log = log + "\n" + logMessage
                    if mode == "reset":
                        await channel.set_permissions(
                            member,
                            overwrite=None,
                            reason="Admin reset lockout obo " + message.author.name,
                        )
                    else:
                        await channel.set_permissions(
                            member,
                            read_messages=False,
                            read_message_history=False,
                            send_messages=False,
                            reason="Admin requested lockout obo " + message.author.name,
                        )
        await messagefuncs.sendWrappedMessage(log, message.author)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LUF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def part_channel_function(message, client, args):
    try:
        if len(message.channel_mentions) > 0:
            channels = message.channel_mentions
        elif len(args) == 0 and message.guild is None:
            return await message.author.send(
                "Parting a channel requires server and channel to be specified (e.g. `!part server:channel [hours]`)"
            )
        elif len(args) == 0:
            channel = message.channel
        elif args[0].strip()[-2:] == ":*":
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(args[0])
                .strip()[:-2]
                .replace("_", " "),
            )
            channels = guild.text_channels
        else:
            try:
                channel = messagefuncs.xchannel(args[0].strip(), message.guild)
            except exceptions.DirectMessageException:
                return await message.author.send(
                    "Parting a channel via DM requires server to be specified (e.g. `!part server:channel [hours]`)"
                )
            if channel is None:
                channel = message.channel
            channels = [channel]
        if len(channels) > 0:
            channel = channels[0]
        else:
            channel = None
        if message.guild is not None:
            guild = message.guild
        elif hasattr(channel, "guild"):
            guild = channel.guild
        else:
            await message.add_reaction("🚫")
            return await message.channel.send(
                "Failed to locate channel, please check spelling."
            )
        channel_names = ""
        for channel in channels:
            await channel.set_permissions(
                message.author,
                read_messages=False,
                read_message_history=False,
                send_messages=False,
                reason="User requested part " + message.author.name,
            )
            channel_names += f"{channel.guild.name}:{channel.name}, "
        await message.add_reaction("✅")
        await message.author.send(f"Parted from {channel_names[0:-2]}")
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
        if len(message.channel_mentions) > 0:
            channels = message.channel_mentions
        elif len(args) == 0 and message.guild is None:
            return await message.author.send(
                "Snoozing a channel requires server and channel to be specified (e.g. `!snooze server:channel [hours]`)"
            )
        elif len(args) == 0:
            channel = message.channel
        elif args[0].strip()[-2:] == ":*":
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(args[0])
                .strip()[:-2]
                .replace("_", " "),
            )
            channels = guild.text_channels
        else:
            try:
                channel = messagefuncs.xchannel(args[0].strip(), message.guild)
            except exceptions.DirectMessageException:
                return await message.author.send(
                    "Snoozing a channel via DM requires server to be specified (e.g. `!snooze server:channel [hours]`)"
                )
            if channel is None:
                channel = message.channel
            channels = [channel]
        if len(channels) > 0:
            channel = channels[0]
        else:
            channel = None
        if message.guild is not None:
            guild = message.guild
        elif hasattr(channel, "guild"):
            guild = channel.guild
        else:
            await message.add_reaction("🚫")
            return await message.channel.send(
                "Failed to locate channel, please check spelling."
            )
        if (
            channel
            and not guild.get_member(client.user.id)
            .permissions_in(channel)
            .manage_roles
        ) or (
            not channel
            and not guild.get_member(client.user.id).guild_permissions.manage_roles
        ):
            await message.add_reaction("🚫")
            return await message.channel.send(
                "Unable to snooze the requested channel(s) - owner has not granted Fletcher Manage Permissions."
            )
        cur = conn.cursor()
        if len(args) == 2:
            try:
                interval = float(args[1])
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
                interval = float(args[0])
            except (ValueError, IndexError):
                interval = float(24)
        overwrites = "unban"
        if len(channels) == 1:
            overwrites = "overwrite " + ujson.dumps(
                channels[0].overwrites_for(message.author)
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
                reason="User requested snooze " + message.author.name,
            )
            channel_names += f"{channel.guild.name}:{channel.name}, "
        channel_names = channel_names[:-2]
        if args[0].strip()[-2:] == ":*":
            channel_names = channels[0].guild.name
        conn.commit()
        await message.add_reaction("✅")
        if type(interval) == float:
            await message.author.send(
                f"Snoozed {channel_names} for {interval} hours (`!part` to leave channel permanently)"
            )
        else:
            await message.author.send(
                f"Snoozed {channel_names} until {interval} (`!part` to leave channel permanently)"
            )
    except discord.Forbidden as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SNCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.channel.send(
            "Snooze forbidden! I don't have the authority to do that."
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
            if entry.created_at > now:
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
        guild_config = ch.scope_config(guild=message.guild)
        role = discord.utils.get(
            message.guild.roles, name=guild_config.get(f"role-message-{args[0].emoji}")
        )
        if not role:
            raise Exception("Matching role not found for reaction to role-message")
        if not remove:
            await message.guild.get_member(args[1].id).add_roles(
                role, reason="Self-assigned via reaction to role-message", atomic=False
            )
            if args[0].emoji in guild_config.get("role-message-autodelete", list()):
                await message.remove_reaction(args[0].emoji, args[1])
        else:
            await message.guild.get_member(args[1].id).remove_roles(
                role, reason="Self-removed via reaction to role-message", atomic=False
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

        if len(args) > 0:
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
        await message.author.send(link)
        await message.remove_reaction("🔜", client.user)
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CLF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def copy_permissions_function(message, client, args):
    try:
        sourceChannel = args[0]
        targetChannel = message.channel

        if sourceChannel.startswith("<#"):
            sourceChannel = message.guild.get_channel(int(sourceChannel[2:-1]))
        else:
            sourceChannel = discord.utils.get(
                message.guild.text_channels, name=sourceChannel
            )

        if len(args) > 1:
            targetChannel = args[1]
            if targetChannel.startswith("<#"):
                targetChannel = message.guild.get_channel(int(targetChannel[2:-1]))
            else:
                targetChannel = discord.utils.get(
                    message.guild.text_channels, name=targetChannel
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
        emoji_query = args.pop(0).strip(":")
        if ":" in emoji_query:
            emoji_query = emoji_query.split(":")
            emoji_query[0] = messagefuncs.expand_guild_name(emoji_query[0], suffix="")
            filter_query = lambda m: m.name == emoji_query[1] and m.guild.name == emoji_query[0]
        else:
            filter_query = lambda m: m.name == emoji_query
        emoji = list(filter(filter_query, client.emojis))
        if len(args) and args[0].isnumeric():
            emoji = emoji[int(args.pop(0))]
        else:
            emoji = emoji[0]
        if len(args):
            emoji_name = args.pop(0)
        else:
            emoji_name = emoji.name
        if emoji:
            target = await message.channel.send(f"Add reaction {emoji}?")
            await target.add_reaction("✅")
            try:
                reaction, user = await client.wait_for(
                    "reaction_add",
                    timeout=6000.0,
                    check=lambda reaction, user: (str(reaction.emoji) == str("✅"))
                    and (user == message.author),
                )
            except asyncio.TimeoutError:
                await target.edit(message="Cancelled, timeout.")
                await message.remove_reaction("✅", client.user)
                pass
            custom_emoji = await message.guild.create_custom_emoji(
                name=emoji_name,
                image=(await emoji.url.read()),
                reason=f"Synced from {emoji.guild} for {message.author.name}",
            )
            await message.channel.send(custom_emoji)
    except discord.Forbidden as e:
        await message.author.send(
            "There was a permissions error when executing this command, please grant me the Manage Emojis permission and try again!"
        )
        exc_type, exc_obj, exc_tb = exc_info()
        logger.info(f"CEF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CEF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def clear_inbound_sync_function(message, client, args):
    global config
    try:
        [
            await webhook.delete()
            for webhook in await message.channel.webhooks()
            if webhook.name.startswith(
                config.get("discord", dict()).get("botNavel", "botNavel") + " ("
            )
        ]
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CISF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def add_inbound_sync_function(message, client, args):
    global config
    try:
        toChannelName = args[0].strip()
        toChannel = messagefuncs.xchannel(toChannelName, message.guild)

        await message.add_reaction("🔜")
        await message.channel.create_webhook(
            name=config.get("discord", dict()).get("botNavel", "botNavel")
            + " ("
            + toChannel.guild.name.replace(" ", "_")
            + ":"
            + toChannel.name.replace(" ", "_")
            + ")",
            reason=f"On behalf of {message.author.name}",
        )
        await message.remove_reaction("🔜", client.user)
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"AOSF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def names_sync_aware_function(message, client, args):
    global ch
    try:
        message_body = "**Users currently in this channel**:\n"
        members = message.channel.members
        if (
            message.guild.name + ":" + message.channel.name
            in ch.webhook_sync_registry.keys()
        ):
            toChannel = ch.webhook_sync_registry[
                message.guild.name + ":" + message.channel.name
            ]["toChannelObject"]
            members.extend(toChannel.members)
        members = [member.display_name for member in members]
        members = sorted(set(members))
        for member in members:
            message_body += f"•{member}\n"
        message_body = message_body[:-1]
        if len(members) > 100:
            target = message.author
        else:
            target = message.channel
        await messagefuncs.sendWrappedMessage(message_body, target)
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"NSAF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def delete_all_invites(message, client, args):
    try:
        invites = await message.guild.invites()
        for invite in invites:
            await invite.delete(reason=f"Obo {message.author.id}")
    except Exception as e:
        exc_type, exc_bj, exc_tb = exc_info()
        logger.error(f"DAI[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


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
            logger.debug(f"{voice_channel}")
            await voice_channel.set_permissions(
                message.author, connect=False, read_messages=False
            )
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_bj, exc_tb = exc_info()
        logger.error(f"VOO[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")

async def error_report_function(error_str, guild, client):
    global ch
    automod = None
    scoped_config = ch.scope_config(guild=message.guild)
    if automod:
        users = scoped_config["mod-users"].split(",")
    else:
        users = str(guild.owner.id)
    users = list(expand_target_list(users, guild))
    for target in users:
        modmail = await messagefuncs.sendWrappedMessage(report_content, target)

async def delete_my_message_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            try:
                if message.author == client.user:
                    await message.delete()
            except discord.Forbidden as e:
                logger.warning("DMMF: Forbidden to delete self-message")
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"DMMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def set_slowmode_function(message, client, args):
    global config
    try:
        if len(message.channel_mentions) > 0:
            target = message.channel_mentions[0]
            if not message.author.permissions_in(target).manage_webhooks:
                logger.warning("SSMF: Forbidden to set slowmode without target admin privileges")
                return
        else:
            target = message.channel
        await target.edit(slowmode_delay=int(args[0]))
        await message.add_reaction("✅")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SSMF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


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
            "admin": "server",
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
            "trigger": ["!copy_emoji", "!esteal"],
            "function": copy_emoji_function,
            "async": True,
            "admin": "server",
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
            "admin": "server",
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
            "admin": "global",
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
            "admin": "server",
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
            "trigger": ["❌"],
            "function": delete_my_message_function,
            "async": True,
            "hidden": False,
            "admin": "server",
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
            "args_name": ['Seconds'],
            "description": "Set channel slow-mode time",
        }
    )

    ch.add_command(
        {
            "trigger": ["!topic"],
            "function": lambda message, client, args: '#'+message.channel.name+' topic: '+message.channel.topic,
            "async": False,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "Get channel topic",
        }
    )

    for guild in ch.client.guilds:
        if ch.scope_config(guild=guild).get("role-message"):
            logger.debug(f"Adding role emoji handler for {guild}")
            ch.add_message_reaction_remove_handler(
                ch.scope_config(guild=guild).get("role-message"),
                {
                    "trigger": [""],  # Empty string: a special catch-all trigger
                    "function": lambda message, client, args: role_message_function(
                        message, client, args, remove=True
                    ),
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "Assign roles based on emoji for a given message",
                },
            )
            ch.add_message_reaction_handler(
                ch.scope_config(guild=guild).get("role-message"),
                {
                    "trigger": [""],  # Empty string: a special catch-all trigger
                    "function": role_message_function,
                    "async": True,
                    "args_num": 0,
                    "args_name": [],
                    "description": "Assign roles based on emoji for a given message",
                },
            )
