import discord
import io
import random
from sys import exc_info

async def randomize_role_function(member, client, config):
    try:
        if type(member) is discord.Member:
            role = member.guild.get_role(int(random.choice(config['randomize_role_list'].split(','))))
            print("RRF: adding role "+str(role)+" to "+str(member))
            await member.add_roles([role], reason='Per Randomize Role Guild setting (see randomize_role_list)', atomic=False)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("RRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Register functions in client
def autoload(ch):
    ch.add_join_handler(
            'randomize_role',
            randomize_role_function
            )
