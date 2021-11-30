import asyncio
import chronos
import commandhandler
import discord
import logging
import messagefuncs
import datetime
import dateparser
import dateparser.search
import pytz
import psycopg2
from typing import Dict
from sentry_sdk import configure_scope
import traceback
import re
from sys import exc_info
import ujson

# global conn set by reload_function

logger = logging.getLogger("fletcher")

schedule_extract_channelmention = re.compile("(?:<#)(\d+)")


class ScheduleFunctions:
    def is_my_ban(identity, target):
        try:
            permissions = target.overwrites_for(identity)
            return (
                permissions.read_messages == False
                and permissions.send_messages == False
                and permissions.embed_links == False
            )
        except AttributeError:
            return False

    async def reminder(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        if "every " in cached_content.lower() and target_message:
            every = chronos.parse_every.search(cached_content).groups(default=1)
            try:
                cur = conn.cursor()
                target = (
                    f"NOW() + '{every[0]} {every[1]}'::interval - '1 minute'::interval"
                )
                cur.execute(
                    f"INSERT INTO reminders (userid, guild, channel, message, content, scheduled, trigger_type) VALUES (%s, %s, %s, %s, %s, {target}, 'reminder');",
                    [
                        target_message.author.id,
                        target_message.guild.id if target_message.guild else 0,
                        target_message.channel.id,
                        target_message.id,
                        cached_content,
                    ],
                )
                conn.commit()
            except Exception as e:
                logger.debug(e)
                conn.rollback()
        if target_message is None:
            return None
        link = f"https://discord.com/channels/{target_message.guild.id if target_message.guild else '@me'}/{target_message.channel.id}/{target_message.id}"
        return [
            f"Reminder for {user.mention} {link}\n> {cached_content}",
            from_channel,
        ]

    async def table(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        return f"You tabled a discussion at {created_at}: want to pick that back up?\nDiscussion link: https://discord.com/channels/{target_message.guild.id if target_message.guild else '@me'}/{target_message.channel.id}/{target_message.id}\nContent: {cached_content}"

    async def getalong(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        await from_channel.set_permissions(
            user, send_messages=True, reason="Can get along now"
        )

    async def unban(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        if target_message:
            content = target_message.content
            channels = target_message.channel_mentions
        else:
            content = cached_content
            channels = None
        args = content.split()[1:]
        is_glob = args[0].strip()[-2:] == ":*"
        if channels:
            pass
        elif is_glob:
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(args[0])
                .strip()[:-2]
                .replace("_", " "),
            )
            channels = guild.text_channels
        else:
            channel = messagefuncs.xchannel(args[0].strip(), target_message.guild)
            if channel is None and target_message:
                channel = target_message.channel
            elif channel is None:
                channel = from_channel
                logger.debug(from_channel)
            channels = [channel]
        if is_glob:
            channel_log = channels[0].guild.name
        else:
            channel_log = []
        for channel in channels:
            if ScheduleFunctions.is_my_ban(user, channel):
                await channel.set_permissions(
                    user,
                    overwrite=None,
                    reason="Unban triggered by schedule obo " + user.name,
                )
                if not is_glob:
                    channel_log += [f"{channel.guild.name}:{channel.name}"]
        if not is_glob:
            channel_log = ", ".join(channel_log)
        return f"Unban triggered by schedule for {channel_log} (`!part` to leave channel permanently)"

    async def overwrite(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        global ch
        client = ch.client
        if target_message:
            content = target_message.content
            channels = target_message.channel_mentions
        else:
            content = cached_content
            channels = None
        args = content.split()[1:]
        if len(args) > 2:
            is_glob = args[0].strip()[-2:] == ":*"
        else:
            is_glob = False
        if channels:
            pass
        elif is_glob:
            guild = discord.utils.get(
                client.guilds,
                name=messagefuncs.expand_guild_name(args[0])
                .strip()[:-2]
                .replace("_", " "),
            )
            channels = guild.text_channels
        else:
            if hasattr(target_message, "guild"):
                guild = target_message.guild
            elif hasattr(from_channel, "guild"):
                guild = from_channel.guild
            else:
                guild = discord.utils.get(
                    client.guilds,
                    name=messagefuncs.expand_guild_name(args[0])
                    .strip()[:-2]
                    .replace("_", " "),
                )
            channel = (
                messagefuncs.xchannel(args[0].strip(), guild) if len(args) else None
            )
            if channel is None and target_message:
                channel = target_message.channel
            elif channel is None:
                channel = from_channel
            channels = [channel]
        if is_glob:
            channel_log = channels[0].guild.name
        else:
            channel_log = []
        overwrites = ujson.loads(mode_args)
        for channel in filter(None, channels):
            if channel is None:
                return f"Error in executing channel override: channel does not exist for {target_message}. This is probably due to the channel being deleted since the snooze record was added.\n> {cached_content}"
            logger.debug(f"Checking {user} in {channel}")
            if ScheduleFunctions.is_my_ban(user, channel):
                if type(overwrites) == dict:
                    overwrite_params = overwrites[
                        f"{channel.guild.name}:{channel.name}"
                    ]
                else:
                    overwrite_params = overwrites
                overwrite = discord.PermissionOverwrite(**dict(overwrite_params))
                try:
                    await channel.set_permissions(
                        user,
                        overwrite=overwrite,
                        reason="Permission overwrite triggered by schedule obo "
                        + user.name,
                    )
                    if not is_glob:
                        channel_log += [f"{channel.guild.name}:{channel.name}"]
                except discord.Forbidden as e:
                    logger.warning(
                        f"TXF: Forbidden to overwrite permissions for {user} in {channel.name} ({channel.guild.name})! Bailing out."
                    )
                    if not is_glob:
                        channel_log += [
                            f"{channel.guild.name}:{channel.name} (failed to overwrite for this channel, Fletcher may not have sufficient permissions anymore)"
                        ]
        if not is_glob:
            channel_log = ", ".join(channel_log)
        return f"Permission overwrite triggered by schedule for {channel_log} (`!part` to leave channel permanently)"


modes: Dict[str, commandhandler.Command] = {
    "reminder": commandhandler.Command(
        description="set a reminder", function=ScheduleFunctions.reminder, sync=False
    ),
    "table": commandhandler.Command(
        description="tabled a discussion", function=ScheduleFunctions.table, sync=False
    ),
    "unban": commandhandler.Command(
        description="snoozed a channel", function=ScheduleFunctions.unban, sync=False
    ),
    "getalong": commandhandler.Command(
        description="timeout is up", function=ScheduleFunctions.getalong, sync=False
    ),
    "overwrite": commandhandler.Command(
        description="snoozed a single channel and kept the overwrite intact",
        function=ScheduleFunctions.overwrite,
        sync=False,
    ),
}


async def table_exec_function():
    try:
        global ch
        client = ch.client
        global conn
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        now = cur.fetchone()[0]
        cur.execute(
            "SELECT userid, guild, channel, message, content, created, trigger_type, ctid FROM reminders WHERE %s > scheduled;",
            [now],
        )
        processed_ctids = []
        tabtuple = cur.fetchone()
        while tabtuple:
            with configure_scope() as scope:
                user = client.get_user(tabtuple[0])
                if not user:
                    tabtuple = cur.fetchone()
                    continue
                scope.user = {"id": user.id, "username": str(user)}
                guild_id = tabtuple[1]
                channel_id = tabtuple[2]
                message_id = tabtuple[3]
                created = tabtuple[5]
                created_at = created.strftime("%B %d, %Y %I:%M%p UTC")
                content = tabtuple[4]
                mode_params = tabtuple[6].split(" ", 1)
                ctid = tabtuple[7]
                if len(mode_params) == 1:
                    mode = mode_params[0]
                    mode_args = None
                else:
                    mode = mode_params[0]
                    mode_args = mode_params[1]
                mode_desc = modes[mode].description
                guild = client.get_guild(guild_id)
                if guild is None and guild_id:
                    logger.info(f"TXF: Fletcher is not in guild {guild_id}")
                    await messagefuncs.sendWrappedMessage(
                        f"You {mode_desc} in a server that Fletcher no longer services, so this request cannot be fulfilled. The content of the command is reproduced below: {content}",
                        user,
                    )
                    processed_ctids += [ctid]
                    tabtuple = cur.fetchone()
                    continue
                from_channel = client.get_channel(channel_id)
                target_message = None
                try:
                    target_message = await from_channel.fetch_message(message_id)
                    # created_at is naîve, but specified as UTC by Discord API docs
                except (discord.NotFound, AttributeError) as e:
                    pass
                todo = await modes[mode].function(
                    target_message,
                    user,
                    content,
                    mode_args,
                    created_at,
                    from_channel,
                )
                try:
                    if type(todo) is str:
                        await messagefuncs.sendWrappedMessage(todo, user)
                    elif type(todo) is list:
                        await messagefuncs.sendWrappedMessage(*todo)
                    elif type(todo) is dict:
                        await messagefuncs.sendWrappedMessage(**todo)
                    elif todo is None:
                        pass
                    else:
                        raise asyncio.CancelledError()
                except discord.Forbidden:
                    pass
                processed_ctids += [ctid]
                tabtuple = cur.fetchone()
        cur.execute("DELETE FROM reminders WHERE %s > scheduled;", [now])
        conn.commit()
        global reminder_timerhandle
        await asyncio.sleep(61)
        reminder_timerhandle = asyncio.create_task(table_exec_function())
    except asyncio.CancelledError:
        logger.debug("TXF: Interrupted, bailing out")
        raise
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        if "ctid" in locals():
            logger.info(f"TXF: Error in ctid row {ctid}")
            await messagefuncs.sendWrappedMessage(
                f"TXF: Error in ctid row {ctid}", ch.global_admin
            )
        logger.info(traceback.format_exc())
        logger.error(f"TXF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def reminder_function(message, client, args):
    try:
        mcontent = message.content
        if args[0] == "me":
            args = args[1:]
            mcontent = mcontent.replace("me ", "", 1)
        if type(message.channel) is not discord.DMChannel and 378641129916203019 in [
            member.id for member in message.channel.members
        ]:
            return
        global conn
        cur = conn.cursor()
        content = "Remind me"
        interval = None
        every = None
        if args[0].lower() == "at":
            tz = chronos.get_tz(message=message)
            d = dateparser.search.search_dates(
                mcontent,
                settings={
                    "RELATIVE_BASE": datetime.datetime.now(tz).replace(tzinfo=None),
                    "PREFER_DATES_FROM": "future",
                    "PREFER_DAY_OF_MONTH": "first",
                    "TIMEZONE": str(tz),
                    "RETURN_AS_TIMEZONE_AWARE": True,
                },
            )[0]
            if d[1].tzinfo is None or d[1].tzinfo.utcoffset(d[1]) is None:
                interval = d[1].replace(tzinfo=tz)
            else:
                interval = d[1]
            if (
                interval.day == datetime.datetime.now(tz).day + 1
                and interval.hour < 12
                and " am" not in d[0].lower()
            ):
                interval = interval - datetime.timedelta(hours=12)
            interval = interval.astimezone(
                datetime.datetime.now().astimezone().tzinfo
            ).replace(tzinfo=None)
            target = f"'{interval}'"
            content = mcontent.split(d[0], 1)[1].strip() or content
        # if args[0].lower() == "in":
        else:
            if args[0].lower() != "in":
                args = ["in", *args]
                mcontent = " ".join(["!remindme", "in", mcontent.split(" ")[1:]])
            interval = chronos.parse_interval.search(
                mcontent.lower().split(
                    " in " if args[0].lower() == "in" else "!remindme", 1
                )[1]
            )
            target = f"NOW() + '{interval.group(0)}'::interval"
            content = mcontent.split(" in ", 1)[1][interval.end(0) :].strip() or content
        if not target or not interval:
            return
        try:
            cur.execute(
                f"INSERT INTO reminders (userid, guild, channel, message, content, scheduled, trigger_type) VALUES (%s, %s, %s, %s, %s, {target}, 'reminder') RETURNING scheduled;",
                [
                    message.author.id,
                    message.guild.id if message.guild else 0,
                    message.channel.id,
                    message.id,
                    content,
                ],
            )
            target = cur.fetchone()[0]
            target = f"<t:{int(target.astimezone(pytz.utc).timestamp())}:R>"
            conn.commit()
            try:
                await message.add_reaction("✅")
            except:
                pass
            return await messagefuncs.sendWrappedMessage(
                f"Setting a reminder {target}\n> {content}",
                message.channel,
                delete_after=30,
            )
        except psycopg2.Error:
            conn.rollback()
            return await messagefuncs.sendWrappedMessage(
                f"Couldn't parse time syntax",
                message.channel,
                delete_after=30,
            )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("RDRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def table_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            if (
                str(args[0].emoji) == "🏓"
                and not args[1].bot
                and ch.config.get(
                    guild=message.guild, key="active-emoji", default=False
                )
            ):
                global conn
                cur = conn.cursor()
                interval = "1 day"
                cur.execute(
                    "INSERT INTO reminders (userid, guild, channel, message, content, scheduled) VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '"
                    + interval
                    + "');",
                    [
                        args[1].id,
                        message.guild.id if message.guild else 0,
                        message.channel.id,
                        message.id,
                        message.content,
                    ],
                )
                conn.commit()
                return await messagefuncs.sendWrappedMessage(
                    "Tabling conversation in #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to {} for {}".format(
                        message.channel.name,
                        message.channel.guild.name,
                        message.guild.name if message.guild else "Direct Message",
                        message.guild.id if message.guild else "@me",
                        message.channel.id,
                        message.id,
                        message.content,
                        interval,
                    ),
                    args[1],
                )
    except Exception as e:
        if "cur" in locals() and "conn" in locals():
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("TF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


# Register this module's commands
def autoload(ch):
    ch.add_command(
        {
            "trigger": ["🏓"],
            "function": table_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Table a discussion for later.",
        }
    )
    ch.add_command(
        {
            "trigger": ["!remindme", "!remind"],
            "function": reminder_function,
            "async": True,
            "args_num": 2,
            "args_name": ["in x months x weeks x weeks x days x hours x minutes"],
            "description": "Set a reminder.",
        }
    )
    global reminder_timerhandle
    try:
        reminder_timerhandle.cancel()
    except NameError:
        pass
    reminder_timerhandle = asyncio.create_task(table_exec_function())
    cur = conn.cursor()
    cur.execute(
        "SELECT m1.user1 AS user1, m1.user2 AS user2, array_intersect(string_to_array(m1.description, ','), string_to_array(m2.description, ',')) AS categories FROM matches m1 LEFT JOIN matches m2 ON m1.user1 = m2.user2 AND m1.user2 = m2.user1 WHERE m1.notification_sent = 'f' AND string_to_array(m1.description, ',') && string_to_array(m2.description, ',') AND (m1.description <> '') IS TRUE AND (m2.description <> '') IS TRUE;",
        [],
    )
    luckytuple = cur.fetchone()
    todo = "UPDATE matches SET notification_sent = 't' WHERE "
    toSend = {}
    while luckytuple:
        try:
            u1 = ch.client.get_user(luckytuple[0])
            u2 = ch.client.get_user(luckytuple[1])
            if not u1 or not u2:
                luckytuple = cur.fetchone()
                continue
            desc = [
                {
                    "date": "go on a date or something",
                    "friend": "hang out some time",
                }.get(cat, cat)
                for cat in luckytuple[2]
            ]
            desc = ", ".join(desc[:-2] + [" and ".join(desc[-2:])])
            toSend[f"{u1},{u2}"] = (
                u1,
                f"You matched with {u2.mention} ({u2.name}#{u2.discriminator}) on the following categories: {desc}. Best wishes, and I hope you enjoy each other's company!",
            )
            toSend[f"{u2},{u1}"] = (
                u2,
                f"You matched with {u1.mention} ({u1.name}#{u1.discriminator}) on the following categories: {desc}. Best wishes, and I hope you enjoy each other's company!",
            )
            todo += f"(user1 = {luckytuple[0]} AND user2 = {luckytuple[1]}) OR "
        except Exception as e:
            logger.debug(f"{e}")
            pass
        luckytuple = cur.fetchone()
    for to, send in toSend.items():
        asyncio.create_task(messagefuncs.sendWrappedMessage(send[1], send[0]))
    cur.execute(f"{todo}'f';", [])


async def autounload(ch):
    global reminder_timerhandle
    try:
        reminder_timerhandle.cancel()
    except NameError:
        pass
