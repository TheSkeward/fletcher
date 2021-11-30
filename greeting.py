import asyncio
import discord
import io
import logging
import messagefuncs
import random
import re
from sys import exc_info
from datetime import datetime, timedelta, timezone

# global conn set by reload_function

logger = logging.getLogger("fletcher")


async def restorerole_function(member, client, config):
    try:
        global conn
        cur = conn.cursor()
        cur.execute(
            "SELECT nickname, roles FROM permaRoles WHERE userid = %s AND guild = %s;",
            [member.id, member.guild.id],
        )
        roles = cur.fetchone()
        if roles is not None:
            name = roles[0]
            roles = roles[1]
            cur.execute(
                "DELETE FROM permaRoles WHERE userid = %s AND guild = %s;",
                [member.id, member.guild.id],
            )
        conn.commit()
        if roles is None and config.get("default_join_role"):
            name = None
            roles = [config.get("default_join_role")]
        elif roles is None:
            return
        # Silently drop deleted roles
        roles = list(filter(None, [member.guild.get_role(role) for role in roles]))
        logger.info(
            f'RPR: Restoring roles {",".join([str(role) for role in roles])} for {member.id} in {member.guild.id}'
        )
        await member.edit(nick=name, roles=roles, reason="Restoring Previous Roles")
    except discord.Forbidden as e:
        await messagefuncs.sendWrappedMessage(
            f'Error Restoring roles {",".join([str(role) for role in roles])} and nick {name} for {member.name} ({member.id}): {e}',
            member.guild.owner,
        )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"RPR[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def saverole_function(member, client, config):
    try:
        global conn
        if len(member.roles):
            roles = [role.id for role in member.roles if role.is_assignable()]
            logger.info(
                f'SRF: Storing roles {",".join([str(role) for role in roles])} for {member.id} in {member.guild.id}'
            )
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO permaRoles (userid, guild, roles, updated, nickname) VALUES (%s, %s, %s, %s, %s);",
                [
                    member.id,
                    member.guild.id,
                    [role.id for role in member.roles],
                    datetime.now(),
                    member.display_name,
                ],
            )
            conn.commit()
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"SRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def greet_function(member, client, config):
    try:
        await messagefuncs.sendWrappedMessage(config["greet_message"], member)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"GF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def lockout_function(member, client, config):
    try:
        if type(member) is discord.Member:
            for category, channels in member.guild.by_category():
                if category is not None:
                    logger.debug(
                        "LOF: "
                        + str(member)
                        + " from category "
                        + str(category)
                        + " in "
                        + str(member.guild)
                    )
                    await category.set_permissions(
                        member,
                        read_messages=False,
                        read_message_history=False,
                        send_messages=False,
                        reason="Lockout policy for new members",
                    )
                else:
                    for channel in channels:
                        logger.debug(
                            "LOF: "
                            + str(member)
                            + " from non-category channel "
                            + str(channel)
                            + " in "
                            + str(member.guild)
                        )
                        await channel.set_permissions(
                            member,
                            read_messages=False,
                            read_message_history=False,
                            send_messages=False,
                            reason="Lockout policy for new members",
                        )
            await messagefuncs.sendWrappedMessage(config["lockout_message"], member)
            await messagefuncs.sendWrappedMessage(
                f"If you would like access to this guild, reply to this message with `I agree` to indicate that you have read the rules and conditions. If not, do nothing and you will be automatically removed in {config['lockout_timeout']} seconds.",
                member,
            )

            def check(m):
                return (
                    m.content == "I agree"
                    and type(m.channel) is discord.DMChannel
                    and m.channel.recipient == member
                )

            try:
                msg = await client.wait_for(
                    "message", timeout=float(config["lockout_timeout"]), check=check
                )
            except asyncio.TimeoutError:
                await messagefuncs.sendWrappedMessage(
                    "Timed out waiting for agreement to rules. You have been automatically kicked from the server.",
                    member,
                )
                await member.kick(reason="Failed to agree to rules in timely manner.")
            else:
                await memssagefuncs.sendWrappedMessage(
                    "Thank you for your cooperation! Granting you member permissions. Please note that this server may have additional roles that restrict channels.",
                    member,
                )
                for category, channels in member.guild.by_category():
                    if category is not None:
                        logger.debug(
                            f"LOF: {member} from category {category} in {member.guild}"
                        )
                        await category.set_permissions(
                            member,
                            None,
                            reason="Lockout policy for new members (agreed to rules)",
                        )
                    else:
                        for channel in channels:
                            logger.debug(
                                f"LOF: {member} from non-category channel {channel} in {member.guild}"
                            )
                            await channel.set_permissions(
                                member,
                                None,
                                reason="Lockout policy for new members (agreed to rules)",
                            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LOF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def randomize_role_function(member, client, config):
    try:
        if type(member) is discord.Member:
            role = member.guild.get_role(
                int(random.choice(config["randomize_role_list"]))
            )
            logger.info("RRF: adding role " + str(role) + " to " + str(member))
            await member.add_roles(
                role,
                reason="Per Randomize Role Guild setting (see randomize_role_list)",
                atomic=False,
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"RRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def printhello_reload_function(guild, client, config):
    logger.debug(
        "PHRF: Hello to guild "
        + guild.name
        + " at "
        + str(datetime.now(timezone.utc))
        + "!"
    )


async def chanban_join_function(member, client, config):
    logger.info(
        "CBJF: "
        + str(member)
        + " "
        + str(config["chanban_younger_than"])
        + " "
        + str(member.guild.get_channel(int(config["chanban_channel"])).name)
    )
    await member.guild.get_channel(int(config["chanban_channel"])).set_permissions(
        member, read_messages=False, send_messages=False, embed_links=False
    )


async def thread_keepalive_reload_function(guild, client, config):
    try:
        member = guild.get_member(client.user.id)
        for channel in (
            channel
            for channel in guild.text_channels
            if channel.permissions_for(member).read_message_history
        ):
            async for thread in channel.archived_threads(
                private=False, limit=50, joined=True
            ):
                if (
                    not thread.locked
                    and not thread.fetch_message(thread.last_message_id).archiver_id
                ):
                    await thread.edit(archived=False)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TKRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def chanban_reload_function(guild, client, config):
    try:
        channel = guild.get_channel(int(config["chanban_channel"]))
        logger.debug(
            "CBRF: " + str(config["chanban_younger_than"]) + " " + channel.name
        )
        now = datetime.now(tz=timezone.utc)
        age_of_consent = timedelta(seconds=int(config["chanban_younger_than"]))
        age_of_consent_expiry = timedelta(
            seconds=int(config["chanban_younger_than"]), hours=2
        )
        younglings = [
            member
            for member in guild.members
            if now - member.joined_at < age_of_consent
        ]
        member_overrides = [
            member
            for member, permissions in channel.overwrites.items()
            if isinstance(member, discord.Member)
        ]
        for member in younglings:
            if member not in member_overrides:
                logger.info("CBRF: Banning " + str(member))
                await channel.set_permissions(
                    member, read_messages=False, send_messages=False, embed_links=False
                )
        for member in member_overrides:
            permissions = channel.overwrites_for(member)
            if (
                now - member.joined_at > age_of_consent
                and now - member.joined_at < age_of_consent_expiry
                and permissions.read_messages == False
                and permissions.send_messages == False
                and permissions.embed_links == False
            ):
                logger.info("CBRF: Unbanning " + str(member))
                await channel.set_permissions(member, overwrite=None)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"CBRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def regex_filter(message, client, config):
    try:
        if config.get("regex-allowmode") == "whitelist":
            whitelist_mode = True
        else:
            whitelist_mode = False
        if config.get("regex-target") == "author":
            subject = str(message.author)
        else:
            subject = str(message.content)
        re_flags = 0
        if config.get("regex-ignorecase"):
            re_flags = re_flags | re.IGNORECASE
        matching = re.search(config["regex-pattern"], subject, re_flags)
        if matching and whitelist_mode:
            allowed = True
        elif not matching and whitelist_mode:
            allowed = False
        elif matching and not whitelist_mode:
            allowed = False
        # elif not matching and not whitelist_mode:
        else:
            allowed = True
        if not allowed:
            if "regex-warn-reaction" in config:
                if len(config["regex-warn-reaction"]) > 1:
                    target_emoji = discord.utils.get(
                        message.guild.emojis, name=config["regex-warn-reaction"]
                    )
                    if target_emoji is None:
                        target_emoji = discord.utils.get(
                            client.get_all_emojis(), name=config["regex-warn-reaction"]
                        )
                else:
                    target_emoji = config["regex-warn-reaction"]
                await message.add_reaction(target_emoji)
            if "regex-warn" in config:
                if config.get("regex-warn-target") == "author":
                    target = message.author
                else:
                    target = message.channel
                if "regex-warn-timeout" in config:
                    if config["regex-warn-timeout"].isdigit():
                        timeout = int(config["regex-warn-timeout"])
                    else:
                        timeout = None
                else:
                    timeout = 60
                await messagefuncs.sendWrappedMessage(
                    config["regex-warn"].replace("\\n", "\n").format(**vars()),
                    target,
                    delete_after=timeout,
                )

            if config.get("regex-kill"):
                if message.channel.permissions_for(message.author).manage_messages:
                    emoji = client.get_emoji(787460478527078450)
                    await message.add_reaction(emoji)
                    await asyncio.sleep(10)
                    await message.remove_reaction(emoji, client.user)
                try:
                    await message.delete()
                except discord.Forbidden as e:
                    logger.warning(
                        "MRF: Forbidden to delete message in " + str(message.channel)
                    )
                    pass
        return allowed
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def alphabetize_channels(guild, client, config):
    # In categories, don't order categories themselves
    try:
        runagain = True
        while runagain:
            position = 0
            runagain = False
            for category_tuple in guild.by_category():
                channels = (
                    category_tuple[1]
                    if not category_tuple[0]
                    else category_tuple[0].channels
                )
                if category_tuple[0] and category_tuple[0].name in config.get(
                    "azsort-exclude", ""
                ).split(","):
                    position += len(channels)
                    continue
                channels = list(
                    filter(
                        lambda channel: type(channel) == discord.TextChannel, channels
                    )
                )
                az_channels = sorted(channels, key=lambda channel: channel.name)
                logger.debug(
                    f'Alphabetizing {category_tuple[0].name if category_tuple[0] and category_tuple[0].name else "Unnamed Category"}',
                    extra={"FLETCHER_MODULE": "alphabetize_channels"},
                )
                moves = 0
                for channel in az_channels:
                    logger.debug(
                        f"#{channel.name} {channel.position} -> {position}",
                        extra={"FLETCHER_MODULE": "alphabetize_channels"},
                    )
                    if channel.position != position:
                        moves += 1
                        if not moves % 10:
                            await asyncio.sleep(60)
                        runagain = True
                        logger.info(
                            f"Moving {channel} to {position} from {channel.position}",
                            extra={"FLETCHER_MODULE": "alphabetize_channels"},
                        )
                        if channel.position != 0:
                            try:
                                await channel.edit(
                                    position=position, reason="Alphabetizing"
                                )
                            except discord.InvalidArgument as e:
                                # Ignore issues with position being too high for voice channels
                                pass
                    position += 1
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"ACF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


# Register functions in client
def autoload(ch):
    ch.add_remove_handler("save_roles", saverole_function)
    ch.add_join_handler("restore_roles", restorerole_function)
    ch.add_join_handler("lockout", lockout_function)
    ch.add_join_handler("greet", greet_function)
    ch.add_join_handler("randomize_role", randomize_role_function)
    ch.add_reload_handler("printhello", printhello_reload_function)
    ch.add_join_handler("chanban", chanban_join_function)
    ch.add_reload_handler("chanban", chanban_reload_function)
    ch.add_reload_handler("thread_keepalive", thread_keepalive_reload_function)
    ch.add_reload_handler("azsort", alphabetize_channels)


async def autounload(ch):
    pass
