import asyncio
import discord
import io
import random
from sys import exc_info

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

# Register functions in client
def autoload(ch):
    ch.add_join_handler(
            'lockout',
            lockout_function
            )
    ch.add_join_handler(
            'randomize_role',
            randomize_role_function
            )
