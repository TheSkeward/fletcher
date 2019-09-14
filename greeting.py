import asyncio
import discord
import io
import random
from sys import exc_info
from datetime import datetime, timedelta
# global conn set by reload_function

async def restorerole_function(member, client, config):
    try:
        global conn
        cur = conn.cursor()
        cur.execute("SELECT nickname, roles FROM permaRoles WHERE userid = %s AND guild = %s;", [member.id, member.guild.id])
        roles = cur.fetchone()
        if roles is not None:
            name = roles[0]
            roles = roles[1]
            cur.execute("DELETE FROM permaRoles WHERE userid = %s AND guild = %s;", [member.id, member.guild.id])
        conn.commit()
        if roles is None:
            return
        # Silently drop deleted roles
        roles = list(filter(None, [member.guild.get_role(role) for role in roles]))
        print("RPR: Restoring roles {} for {} in {}".format(",".join([str(role) for role in roles]), member.id, member.guild.id))
        await member.edit(nick=name, roles=roles, reason='Restoring Previous Roles')
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("RPR[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def saverole_function(member, client, config):
    try:
        global conn
        if len(member.roles):
            roles = [role.id for role in member.roles]
            print("SRF: Storing roles {} for {} in {}".format(",".join([str(role) for role in roles]), member.id, member.guild.id))
            cur = conn.cursor()
            cur.execute("INSERT INTO permaRoles (userid, guild, roles, updated, nickname) VALUES (%s, %s, %s, %s, %s);", [member.id, member.guild.id, [role.id for role in member.roles], datetime.now(), member.display_name])
            conn.commit()
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("SRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def lockout_function(member, client, config):
    try:
        if type(member) is discord.Member:
            for category, channels in member.guild.by_category():
                if category is not None:
                    print("LOF: "+str(member)+" from category "+str(category)+" in "+str(member.guild))
                    await category.set_permissions(member, read_messages=False, read_message_history=False, send_messages=False, reason="Lockout policy for new members")
                else:
                    for channel in channels:
                        print("LOF: "+str(member)+" from non-category channel "+str(channel)+" in "+str(member.guild))
                        await channel.set_permissions(member, read_messages=False, read_message_history=False, send_messages=False, reason="Lockout policy for new members")
            await member.send(config["lockout_message"])
            await member.send("If you would like access to this guild, reply to this message with `I agree` to indicate that you have read the rules and conditions. If not, do nothing and you will be automatically removed in "+config["lockout_timeout"]+" seconds.")
            def check(m):
                return m.content == 'I agree' and type(m.channel) is discord.DMChannel and m.channel.recipient == member
            try: 
                msg = await client.wait_for('message', timeout=float(config["lockout_timeout"]), check=check)
            except asyncio.TimeoutError:
                await member.send('Timed out waiting for agreement to rules. You have been automatically kicked from the server.')
                await member.kick(reason='Failed to agree to rules in timely manner.')
            else:
                await member.send('Thank you for your cooperation! Granting you member permissions. Please note that this server may have additional roles that restrict channels.')
                for category, channels in member.guild.by_category():
                    if category is not None:
                        print("LOF: "+str(member)+" from category "+str(category)+" in "+str(member.guild))
                        await category.set_permissions(member, None, reason="Lockout policy for new members (agreed to rules)")
                    else:
                        for channel in channels:
                            print("LOF: "+str(member)+" from non-category channel "+str(channel)+" in "+str(member.guild))
                            await channel.set_permissions(member, None, reason="Lockout policy for new members (agreed to rules)")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LOF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def randomize_role_function(member, client, config):
    try:
        if type(member) is discord.Member:
            role = member.guild.get_role(int(random.choice(config['randomize_role_list'].split(','))))
            print("RRF: adding role "+str(role)+" to "+str(member))
            await member.add_roles(role, reason='Per Randomize Role Guild setting (see randomize_role_list)', atomic=False)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("RRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def printhello_reload_function(guild, client, config):
    print("PHRF: Hello to guild "+guild.name+" at "+str(datetime.utcnow())+"!")

async def chanban_join_function(member, client, config):
    print('CBJF: '+str(member)+' '+str(config['chanban_younger_than'])+' '+str(member.guild.get_channel(int(config['chanban_channel'])).name))
    await member.guild.get_channel(int(config['chanban_channel'])).set_permissions(member, read_messages=False, send_messages=False, embed_links=False)

async def chanban_reload_function(guild, client, config):
    channel = guild.get_channel(int(config['chanban_channel']))
    print('CBRF: '+str(config['chanban_younger_than'])+' '+channel.name)
    now = datetime.utcnow()
    age_of_consent = timedelta(seconds=int(config['chanban_younger_than']))
    younglings = [member for member in guild.members if now - member.joined_at < age_of_consent]
    member_overrides = [member for (member, permissions) in channel.overwrites if isinstance(member, discord.Member)]
    for member in younglings:
        if member not in member_overrides:
            print('CBRF: Banning '+str(member))
            await channel.set_permissions(member, read_messages=False, send_messages=False, embed_links=False)
    for member in member_overrides:
        permissions = channel.overwrites_for(member)
        if now - member.joined_at > age_of_consent and permissions.read_messages == False and permissions.send_messages == False and permissions.embed_links == False:
            print('CBRF: Unbanning '+str(member))
            await channel.set_permissions(member, overwrite=None)

# Register functions in client
def autoload(ch):
    ch.add_remove_handler(
            'save_roles',
            saverole_function
            )
    ch.add_join_handler(
            'restore_roles',
            restorerole_function
            )
    ch.add_join_handler(
            'lockout',
            lockout_function
            )
    ch.add_join_handler(
            'randomize_role',
            randomize_role_function
            )
    ch.add_reload_handler(
            'printhello',
            printhello_reload_function
            )
    ch.add_join_handler(
            'chanban',
            chanban_join_function
            )
    ch.add_reload_handler(
            'chanban',
            chanban_reload_function
            )
