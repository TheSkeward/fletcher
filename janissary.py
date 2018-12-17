from datetime import datetime, timedelta
import discord
from sys import exc_info
import textwrap
import text_manipulators

async def modping_function(message, client, args):
    global config
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            pass # Reaction
        else:
            if message.channel.permissions_for(message.author).manage_messages:
                role_list = message.channel.guild.roles
                role = discord.utils.get(role_list, name=" ".join(args))
                lay_mentionable = role.mentionable
                if not lay_mentionable:
                    await role.edit(mentionable=True)
                mentionPing = await message.channel.send(message.author.name+' pinging '+role.mention)
                if not lay_mentionable:
                    await role.edit(mentionable=False)
                if 'snappy' in config['discord'] and config['discord']['snappy']:
                    mentionPing.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("MPF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def modreport_function(message, client, args):
    global config
    try:
        report_content = None
        plaintext = None
        automod = None
        if len(args) == 2 and type(args[1]) is discord.User:
            await message.remove_reaction('👁‍🗨', args[1])
            plaintext = message.content
            report_content = "Mod Report: #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to ".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id)
            automod = False
        else:
            plaintext = " ".join(args)
            report_content = "Mod Report: #{} ({}) https://discordapp.com/channels/{}/{}/{} ".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id)
            automod = True
        if message.channel.is_nsfw():
            report_content = report_content + await rot13_function(message, client, [plaintext, 'INTPROC'])
        else:
            report_content = report_content + plaintext
        if automod:
            users = config['moderation']['mod-users'].split(',')
        else:
            users = config['moderation']['manual-mod-users'].split(',')
        for user_id in users:
            modmail = await client.get_user(int(user_id)).send(report_content)
            if message.channel.is_nsfw():
                await modmail.add_reaction('🕜')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("MRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def lastactive_channel_function(message, client, args):
    try:
        lastMonth = None
        before = True
        try:
            if args[0]:
                try:
                    lastMonth = datetime.utcnow().date() - timedelta(days=int(args[0]))
                except ValueError:
                    if args[1]:
                        if args[0].startswith("a"):
                            before = False
                        lastMonth = datetime.utcnow().date() - timedelta(days=int(args[1]))
                    pass
        except IndexError:
                    pass
        msg = ""
        for channel in message.channel.guild.text_channels:
            try:
                category_pretty = ""
                if channel.category_id:
                    category_pretty = " [{}]".format(client.get_channel(channel.category_id).name)
                created_at = (await channel.history(limit=1).flatten())[0].created_at
                created_pretty = text_manipulators.pretty_date(created_at)
                if created_pretty:
                    created_pretty = " ({})".format(created_pretty)
                if lastMonth:
                    if (before and lastMonth < created_at.date()) or (not before and lastMonth > created_at.date()):
                        msg = "{}\n<#{}>{}: {}{}".format(msg, channel.id, category_pretty, created_at.isoformat(timespec='minutes'), created_pretty)
                else:
                        msg = "{}\n<#{}>{}: {}{}".format(msg, channel.id, category_pretty, created_at.isoformat(timespec='minutes'), created_pretty)
            except discord.NotFound as e:
                pass
            except discord.Forbidden as e:
                msg = "{}\n<#{}>{}: Forbidden".format(msg, channel.id, category_pretty)
                pass
        msg = '**Channel Activity:**{}'.format(msg)
        msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
        for chunk in msg_chunks:
            await message.channel.send(chunk)
    except Exception as e:
        print(e)

async def lastactive_user_function(message, client, args):
    try:
        lastMonth = None
        before = True
        try:
            if args[0]:
                try:
                    lastMonth = datetime.utcnow().date() - timedelta(days=int(args[0]))
                except ValueError:
                    if args[1]:
                        if args[0].startswith("a"):
                            before = False
                        lastMonth = datetime.utcnow().date() - timedelta(days=int(args[1]))
                    pass
        except IndexError:
                    pass
        if message.guild.large:
            client.request_offline_members(message.guild)
        users = {}
        for m in message.guild.members:
            users[m.id] = datetime.today() + timedelta(days=1)
        for channel in message.channel.guild.text_channels:
            async for message in channel.history(limit=None):
                try:
                    print("[{} <#{}>] <@{}>: {}".format(message.created_at, channel.id, message.author.id, message.content))
                    if message.created_at < users[message.author.id]:
                        users[message.author.id] = message.created_at
                except discord.NotFound as e:
                    pass
                except discord.Forbidden as e:
                    pass
        msg = '**User Activity:**{}'.format(msg)
        for user_id, last_active in users:
            if last_active == datetime.today() + timedelta(days=1):
                last_active = "None"
            else:
                last_active = text_manipulators.pretty_date(last_active)
            msg = "{}\n<@{}>{}: {}".format(msg, user_id, last_active)
        msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
        for chunk in msg_chunks:
            await message.channel.send(chunk)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LSU[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

def autoload(ch):
    ch.add_command({
        'trigger': ['!modping'],
        'function': modping_function,
        'async': True,
        'admin': True,
        'args_num': 1,
        'args_name': [],
        'description': 'Ping unpingable roles (Admin)'
        })
    ch.add_command({
        'trigger': ['!modreport', '👁‍🗨'],
        'function': modreport_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Report message to mods. Removed immediately after.'
        })
    ch.add_command({
        'trigger': ['!lastactive_channel', '!lastactivity_channel', '!lsc'],
        'function': lastactive_channel_function,
        'async': True,
        'admin': True,
        'args_num': 0,
        'args_name': [],
        'description': 'List all available channels and time of last message (Admin)'
        })
    ch.add_command({
        'trigger': ['!lastactive_user', '!lastactivity_user', '!lsu'],
        'function': lastactive_user_function,
        'async': True,
        'admin': True,
        'args_num': 0,
        'args_name': [],
        'description': 'List all available users and time of last message (Admin)'
        })
