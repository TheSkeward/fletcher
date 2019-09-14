import asyncio
from datetime import datetime, timedelta
import discord
from sys import exc_info
import textwrap
import text_manipulators

async def addrole_function(message, client, args):
    global config
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            pass # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            roleProperties = {
                    "name": None,
                    "colour": None,
                    "mentionable": True
                    }
            if " with " in argString:
                roleProperties["name"] = argString.split(" with")[0]
                argString = argString.split(" with")[1].lower().replace("color", "colour").replace("pingable", "mentionable")
                it = iter(argString.trim().replace(" and ", "").replace(", ", "").split(" "))
                for prop, val in zip(it, it):
                    if prop == "colour":
                        roleProperties["colour"] = discord.Colour.from_rgb(int(val[0-1]), int(val[2-3]), int(val[4-5]))
                    elif (prop == "mentionable" and val in ["no", "false"]) or (prop == "not" and val == "mentionable"):
                        roleProperties["mentionable"] = False
            else:
                roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                err = "Role already exists!"
                if not role.mentionable or message.channel.permissions_for(message.author).manage_messages:
                    if role in message.author.roles:
                        err = err + " `!revoke "+role.name+" from me` to remove this role from yourself."
                    else:
                        err = err + " `!assign "+role.name+" to me` to add this role to yourself."
                else:
                    if role in message.author.roles:
                        err = err + " An administrator can `!revoke "+role.name+" from @"+str(message.author.id)+"` to remove this role from you."
                    else:
                        err = err + " An administrator can `!assign "+role.name+" to @"+str(message.author.id)+"` to add this role to you."
                return await message.channel.send(err)
            else:
                role = await message.channel.guild.create_role(
                        name   = roleProperties["name"],
                        colour = roleProperties["colour"],
                        mentionable = True,
                        reason="Role added on behalf of "+str(message.author.id))
                await message.channel.send("Role "+role.mention+" successfully created.")
                await role.edit(mentionable=roleProperties["mentionable"])
                if 'snappy' in config['discord'] and config['discord']['snappy']:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("ARF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def assignrole_function(message, client, args):
    global config
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            pass # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            if argString.endswith(" to me"):
                argString = argString[:-6]
            roleProperties = {
                    "name": None
                    }
            roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                if not role.mentionable or message.channel.permissions_for(message.author).manage_messages:
                    if role in message.author.roles:
                        return await message.channel.send("You already have that role, `!revoke "+role.name+" from me` to remove this role from yourself.")
                    else:
                        if 'snappy' in config['discord'] and config['discord']['snappy']:
                            await message.delete()
                        await message.author.add_roles(role, reason="Self-assigned", atomic=False)
                        return await message.channel.send("Role assigned, `!revoke "+role.name+" from me` to remove this role from yourself.")
                else:
                    # TODO unimplemented
                    pass;
                    if role in message.author.roles:
                        err = err + " An administrator can `!revoke "+role.name+" from @"+str(message.author.id)+"` to remove this role from you."
                    else:
                        err = err + " An administrator can `!assign "+role.name+" to @"+str(message.author.id)+"` to add this role to you."
                return await message.channel.send(err)
            else:
                await message.channel.send("Role "+roleProperties["name"]+" does not exist, use the addrole command to create it.")
                if 'snappy' in config['discord'] and config['discord']['snappy']:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("ASRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def revokerole_function(message, client, args):
    global config
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            pass # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            if argString.endswith(" from me"):
                argString = argString[:-8]
            roleProperties = {
                    "name": None
                    }
            roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                if not role.mentionable or message.channel.permissions_for(message.author).manage_messages:
                    if role in message.author.roles:
                        if 'snappy' in config['discord'] and config['discord']['snappy']:
                            await message.delete()
                        await message.author.remove_roles(role, reason="Self-assigned", atomic=False)
                        return await message.channel.send("Role revoked, `!assign "+role.name+" to me` to add this role to yourself.")
                    else:
                        return await message.channel.send("You don't have that role, `!assign "+role.name+" to me` to assign this role to yourself.")
                else:
                    # TODO unimplemented
                    pass;
                    if role in message.author.roles:
                        err = err + " An administrator can `!revoke "+role.name+" from @"+str(message.author.id)+"` to remove this role from you."
                    else:
                        err = err + " An administrator can `!assign "+role.name+" to @"+str(message.author.id)+"` to add this role to you."
                return await message.channel.send(err)
            else:
                await message.channel.send("Role "+roleProperties["name"]+" does not exist, use the addrole command to create it.")
                if 'snappy' in config['discord'] and config['discord']['snappy']:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("RSRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def delrole_function(message, client, args):
    global config
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            pass # Reaction
        else:
            role_list = message.channel.guild.roles
            argString = " ".join(args)
            roleProperties = {
                    "name": None
                    }
            roleProperties["name"] = argString

            role = discord.utils.get(role_list, name=roleProperties["name"])
            if role is not None:
                if message.channel.permissions_for(message.author).manage_messages:
                    await role.delete(reason="On behalf of "+str(message.author))
                    await message.channel.send("Role `@"+roleProperties["name"]+"` deleted.")
                else:
                    await message.channel.send("You do not have permission to delete role `@"+roleProperties["name"]+"`.")
            else:
                err = "Role `@"+roleProperties["name"]+"` does not exist!"
                if message.channel.permissions_for(message.author).manage_messages:
                    err = err + " `!addrole "+role.name+"` to add this role."
                else:
                    err = err + " An administrator can `!addrole "+role.name+"` to add this role."
                await message.channel.send(err)
                if 'snappy' in config['discord'] and config['discord']['snappy']:
                    await message.delete()
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("DRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def modping_function(message, client, args):
    global config
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            pass # Reaction
        else:
            if not message.channel.permissions_for(message.author).manage_messages:
                def gaveled_by_admin_check(reaction, user):
                    return user.guild_permissions.manage_webhooks and str(reaction.emoji) == '<:gavel:430638348189827072>'
                try: 
                    await modreport_function(message, client, ("\nRole ping requested for "+" ".join(args).lstrip("@")).split(' '))
                    reaction, user = await client.wait_for('reaction_add', timeout=6000.0, check=gaveled_by_admin_check)
                except asyncio.TimeoutError:
                    raise Exception('Timed out waiting for approval')
            role_list = message.channel.guild.roles
            role = discord.utils.get(role_list, name=" ".join(args).lstrip("@"))
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
            try:
                await message.remove_reaction('👁‍🗨', args[1])
            except discord.Forbidden as e:
                print("MRF: Forbidden from removing modreport reaction")
                pass
            plaintext = message.content
            report_content = "Mod Report: #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to ".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id)
            automod = False
        else:
            plaintext = " ".join(args)
            report_content = "Mod Report: #{} ({}) https://discordapp.com/channels/{}/{}/{} ".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id)
            automod = True
        if message.channel.is_nsfw():
            report_content = report_content + await text_manipulators.rot13_function(message, client, [plaintext, 'INTPROC'])
        else:
            report_content = report_content + plaintext
        if "Guild "+str(message.guild.id) in config:
            scoped_config = config["Guild "+str(message.guild.id)]
        else:
            raise Exception("No guild-specific configuration for moderation on guild "+str(message.guild))
        if "moderation" in scoped_config and scoped_config["moderation"] == "On":
            if automod:
                users = scoped_config['mod-users'].split(',')
            else:
                users = scoped_config['manual-mod-users'].split(',')
            for user_id in users:
                modmail = await client.get_user(int(user_id)).send(report_content)
                if message.channel.is_nsfw():
                    await modmail.add_reaction('🕜')
        else:
            raise Exception("Moderation disabled on guild "+str(message.guild))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("MRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

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
            except IndexError as e:
                msg = "{}\n<#{}>{}: Bad History".format(msg, channel.id, category_pretty)
                pass
            except discord.Forbidden as e:
                msg = "{}\n<#{}>{}: Forbidden".format(msg, channel.id, category_pretty)
                pass
        msg = '**Channel Activity:**{}'.format(msg)
        msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
        for chunk in msg_chunks:
            await message.channel.send(chunk)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LACF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

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
        'trigger': ['!roleadd', '!addrole'],
        'function': addrole_function,
        'async': True,
        'admin': True,
        'args_num': 1,
        'args_name': [],
        'description': 'Add role (self-assignable by default)'
        })
    ch.add_command({
        'trigger': ['!roledel', '!delrole'],
        'function': delrole_function,
        'async': True,
        'admin': True,
        'args_num': 1,
        'args_name': [],
        'description': 'Delete role'
        })
    ch.add_command({
        'trigger': ['!revoke'],
        'function': revokerole_function,
        'async': True,
        'admin': True,
        'args_num': 1,
        'args_name': [],
        'description': 'Revoke role `!revoke rolename from me`'
        })
    ch.add_command({
        'trigger': ['!assign'],
        'function': assignrole_function,
        'async': True,
        'admin': True,
        'args_num': 1,
        'args_name': [],
        'description': 'Assign role `!assign rolename to me`'
        })
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
        'description': 'Report message to mods. Removed immediately after (if reaction).'
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
