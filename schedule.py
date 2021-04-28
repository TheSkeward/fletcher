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
from sentry_sdk import configure_scope
import traceback
import re
from sys import exc_info
import textwrap
import ujson

# global conn set by reload_function

logger = logging.getLogger("fletcher")

schedule_extract_channelmention = re.compile("(?:<#)(\d+)")


class ScheduleFunctions:
    def is_my_ban(identity, target):
        permissions = target.overwrites_for(identity)
        return (
            permissions.read_messages == False
            and permissions.send_messages == False
            and permissions.embed_links == False
        )

    async def reminder(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        if type(from_channel) is not discord.DMChannel:
            return [
                f"Reminder for {user.mention} https://discord.com/channels/{target_message.guild.id}/{target_message.channel.id}/{target_message.id}\n> {cached_content}",
                from_channel,
            ]
        else:
            return [
                f"Reminder from https://discord.com/channels/{target_message.guild.id}/{target_message.channel.id}/{target_message.id}\n> {cached_content}",
                from_channel,
            ]

    async def table(
        target_message, user, cached_content, mode_args, created_at, from_channel
    ):
        return f"You tabled a discussion at {created_at}: want to pick that back up?\nDiscussion link: https://discord.com/channels/{target_message.guild.id}/{target_message.channel.id}/{target_message.id}\nContent: {cached_content}"

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


modes = {
    "reminder": commandhandler.Command(
        description="set a reminder", function=ScheduleFunctions.reminder, sync=False
    ),
    "table": commandhandler.Command(
        description="tabled a discussion", function=ScheduleFunctions.table, sync=False
    ),
    "unban": commandhandler.Command(
        description="snoozed a channel", function=ScheduleFunctions.unban, sync=False
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
                    logger.info(f"PMF: Fletcher is not in guild {guild_id}")
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
                if type(todo) is str:
                    await messagefuncs.sendWrappedMessage(todo, user)
                elif type(todo) is list:
                    await messagefuncs.sendWrappedMessage(*todo)
                elif type(todo) is dict:
                    await messagefuncs.sendWrappedMessage(**todo)
                else:
                    raise asyncio.CancelledError()
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
        if type(channel) is discord.DMChannel and 378641129916203019 in [member.id for member in message.channel.members]:
            return
        global conn
        cur = conn.cursor()
        content = "Remind me"
        interval = None
        if args[0].lower() == "in":
            interval = chronos.parse_interval.search(
                message.content.lower().split(" in ", 1)[1]
            )
            target = f"NOW() + '{interval.group(0)}'::interval"
            content = (
                message.content.split(" in ", 1)[1][interval.end(0) :].strip()
                or content
            )
        elif args[0].lower() == "at":
            tz = chronos.get_tz(message=message)
            d = dateparser.search.search_dates(
                message.content,
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
            content = message.content.split(d[0], 1)[1].strip() or content
        else:
            return
        if not target or not interval:
            return
        try:
            cur.execute(
                f"INSERT INTO reminders (userid, guild, channel, message, content, scheduled, trigger_type) VALUES (%s, %s, %s, %s, %s, {target}, 'reminder');",
                [
                    message.author.id,
                    message.guild.id if message.guild else 0,
                    message.channel.id,
                    message.id,
                    content,
                ],
            )
            conn.commit()
            try:
                await message.add_reaction("✅")
            except:
                pass
            return await messagefuncs.sendWrappedMessage(
                f"Setting a reminder at {target}\n> {content}",
                message.channel,
                delete_after=30,
            )
        except InvalidDatetimeFormat:
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
            "trigger": ["!remindme"],
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


async def autounload(ch):
    global reminder_timerhandle
    try:
        reminder_timerhandle.cancel()
    except NameError:
        pass
