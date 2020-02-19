import asyncio
import discord
import logging
import messagefuncs
import re
from sys import exc_info
import textwrap
import ujson

# global conn set by reload_function

logger = logging.getLogger("fletcher")

schedule_extract_channelmention = re.compile("(?:<#)(\d+)")


async def table_exec_function():
    try:
        global ch
        client = ch.client
        global conn
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        now = cur.fetchone()[0]
        cur.execute(
            "SELECT userid, guild, channel, message, content, created, trigger_type FROM reminders WHERE %s > scheduled;",
            [now],
        )
        tabtuple = cur.fetchone()
        modes = {
            "table": "tabled a discussion",
            "unban": "snoozed a channel",
            "overwrite": "snoozed a single channel and kept the overwrite intact",
        }
        while tabtuple:
            user = client.get_user(tabtuple[0])
            guild_id = tabtuple[1]
            channel_id = tabtuple[2]
            message_id = tabtuple[3]
            created = tabtuple[5]
            created_at = created.strftime("%B %d, %Y %I:%M%p UTC")
            content = tabtuple[4]
            mode = tabtuple[6].split(" ", 1)
            if len(mode) == 1:
                mode = mode[0]
            else:
                mode_args = mode[1]
                mode = mode[0]
            mode_desc = modes[mode]
            guild = client.get_guild(guild_id)
            if guild is None:
                logger.info("PMF: Fletcher is not in guild ID " + str(guild_id))
                await user.send(
                    "You {} in a server that Fletcher no longer services, so this request cannot be fulfilled. The content of the command is reproduced below: {}".format(
                        mode_desc, content
                    )
                )
                completed.append(tabtuple[:3])
                tabtuple = cur.fetchone()
                continue
            from_channel = guild.get_channel(channel_id)
            target_message = None
            try:
                target_message = await from_channel.fetch_message(message_id)
                # created_at is naîve, but specified as UTC by Discord API docs
                content = target_message.content
            except (discord.NotFound, AttributeError) as e:
                pass
            if mode == "unban":
                if target_message:
                    args = target_message.content.split()[1:]
                else:
                    args = content.split()[1:]
                if target_message and len(target_message.channel_mentions) > 0:
                    channels = target_message.channel_mentions
                elif args[0].strip()[-2:] == ":*":
                    guild = discord.utils.get(
                        client.guilds,
                        name=messagefuncs.expand_guild_name(args[0])
                        .strip()[:-2]
                        .replace("_", " "),
                    )
                    channels = guild.text_channels
                else:
                    channel = messagefuncs.xchannel(args[0].strip(), guild)
                    if channel is None and target_message:
                        channel = target_message.channel
                    elif channel is None:
                        channel = from_channel
                    channels = [channel]
                channel_names = ""
                for channel in channels:
                    permissions = channel.overwrites_for(user)
                    if (
                        permissions.read_messages == False
                        and permissions.send_messages == False
                        and permissions.embed_links == False
                    ):
                        await channel.set_permissions(
                            user,
                            overwrite=None,
                            reason="Unban triggered by schedule obo " + user.name,
                        )
                        channel_names += f"{guild.name}:{channel.name}, "
                channel_names = channel_names[:-2]
                if args[0].strip()[-2:] == ":*":
                    channel_names = channels[0].guild.name
                await user.send(
                    f"Unban triggered by schedule for {channel_names} (`!part` to leave channel permanently)"
                )
            elif mode == "overwrite":
                if target_message:
                    args = target_message.content.split()[1:]
                else:
                    args = content.split()[1:]
                if target_message and len(target_message.channel_mentions) > 0:
                    channels = target_message.channel_mentions
                elif args[0].strip()[-2:] == ":*":
                    guild = discord.utils.get(
                        client.guilds,
                        name=messagefuncs.expand_guild_name(args[0])
                        .strip()[:-2]
                        .replace("_", " "),
                    )
                    channels = guild.text_channels
                else:
                    channel = messagefuncs.xchannel(args[0].strip(), guild)
                    if channel is None and target_message:
                        channel = target_message.channel
                    elif channel is None:
                        channel = from_channel
                    channels = [channel]
                channel_names = ""
                for channel in channels:
                    permissions = channel.overwrites_for(user)
                    if (
                        permissions.read_messages == False
                        and permissions.send_messages == False
                        and permissions.embed_links == False
                    ):
                        overwrite = discord.PermissionOverwrite()
                        overwrite.update(**{o[0]: o[1] for o in ujson.loads(mode_args)})
                        try:
                            await channel.set_permissions(
                                user,
                                overwrite=overwrite,
                                reason="Permission overwrite triggered by schedule obo "
                                + user.name,
                            )
                            channel_names += f"{guild.name}:{channel.name}, "
                        except discord.Forbidden as e:
                            logger.warning(
                                f"TXF: Forbidden to overwrite permissions for {user} in {channel} ({guild})! Bailing out."
                            )
                            channel_names += f"{guild.name}:{channel.name} (failed to overwrite for this channel, Fletcher may not have sufficient permissions), "
                channel_names = channel_names[:-2]
                if args[0].strip()[-2:] == ":*":
                    channel_names = channels[0].guild.name
                await user.send(
                    f"Permission overwrite triggered by schedule for {channel_names} (`!part` to leave channel permanently)"
                )
            elif mode == "table":
                await messagefuncs.sendWrappedMessage(
                    f"You tabled a discussion at {created_at}: want to pick that back up?\nDiscussion link: https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}\nContent: {content}",
                    user,
                )
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
        logger.error("TXF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def table_function(message, client, args):
    try:
        if len(args) == 3 and type(args[1]) is discord.Member:
            if str(args[0].emoji) == "🏓":
                global conn
                cur = conn.cursor()
                interval = "1 day"
                cur.execute(
                    "INSERT INTO reminders (userid, guild, channel, message, content, scheduled) VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '"
                    + interval
                    + "');",
                    [
                        args[1].id,
                        message.guild.id,
                        message.channel.id,
                        message.id,
                        message.content,
                    ],
                )
                conn.commit()
                return await args[1].send(
                    "Tabling conversation in #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to {} for {}".format(
                        message.channel.name,
                        message.channel.guild.name,
                        message.channel.guild.id,
                        message.channel.id,
                        message.id,
                        message.content,
                        interval,
                    )
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
    global reminder_timerhandle
    try:
        reminder_timerhandle.cancel()
    except NameError:
        pass
    reminder_timerhandle = asyncio.create_task(table_exec_function())
