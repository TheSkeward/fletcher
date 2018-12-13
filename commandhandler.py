import discord
import messagefuncs
import janissary
import re

client = None
tag_id_as_command = None
class CommandHandler:

    # constructor
    def __init__(self, client):
        self.client = client
        self.commands = []

    def add_command(self, command):
        self.commands.append(command)

    async def reaction_handler(self, reaction):
        global config
        messageContent = str(reaction.emoji)
        for command in self.commands:
            if messageContent.startswith(tuple(command['trigger'])) and (('admin' in command and user.guild_permissions.manage_webhooks) or 'admin' not in command):
                if command['args_num'] == 0:
                    channel = self.client.get_channel(reaction.channel_id)
                    message = await channel.get_message(reaction.message_id)
                    user = await self.client.get_user_info(reaction.user_id)
                    if str(user.id) in config['moderation']['blacklist-user-usage'].split(','):
                        print('Blacklisted command attempt by user')
                        return
                    if command['async']:
                        return await command['function'](message, self.client, [reaction, user])
                        break
                    else:
                        return await message.channel.send(str(command['function'](message, self.client, [reaction, user])))
                        break

    async def command_handler(self, message):
        global config
        global sid
        try:
            if message.channel.category_id is None or message.guild.get_channel(message.channel.category_id).name not in config['moderation']['blacklist-category'].split(','):
                sent_com_score = sid.polarity_scores(message.content)['compound']
                if message.content == "VADER NEUTRAL":
                    sent_com_score = 0
                elif message.content == "VADER GOOD":
                    sent_com_score = 1
                elif message.content == "VADER BAD":
                    sent_com_score = -1
                print("["+str(sent_com_score)+"] "+message.content)
                if sent_com_score <= float(config['moderation']['sent-com-score-threshold']) and message.webhook_id is None and message.guild.name in config['moderation']['guilds'].split(','):
                    await janissary.modreport_function(message, self.client, ("\n[Sentiment Analysis Combined Score "+str(sent_com_score)+'] '+message.content).split(' '))
            else:
                print("[Nil] "+message.content)
        except AttributeError as e:
            print("[Nil] "+message.content)
            pass
        if messagefuncs.extract_identifiers_messagelink.search(message.content):
            if str(message.author.id) not in config['moderation']['blacklist-user-usage'].split(','):
                return await messagefuncs.preview_messagelink_function(message, self.client, None)
        searchString = message.content
        if tag_id_as_command:
            searchString = tag_id_as_command.sub(searchString, '!')
        for command in self.commands:
            if searchString.startswith(tuple(command['trigger'])) and (('admin' in command and message.author.guild_permissions.manage_webhooks) or 'admin' not in command):
                print(command)
                args = message.content.split(' ')
                args = [item for item in args if item]
                args.pop(0)
                if str(message.author.id) in config['moderation']['blacklist-user-usage'].split(','):
                    print('Blacklisted command attempt by user')
                    return
                if command['args_num'] == 0:
                    if command['async']:
                        return await command['function'](message, self.client, args)
                        break
                    else:
                        return await message.channel.send(str(command['function'](message, self.client, args)))
                        break
                else:
                    if len(args) >= command['args_num']:
                        if command['async']:
                            return await command['function'](message, self.client, args)
                            break
                        else:
                            return await message.channel.send(str(command['function'](message, self.client, args)))
                            break
                    else:
                        return await message.channel.send('command "{}" requires {} argument(s) "{}"'.format(command['trigger'][0], command['args_num'], ', '.join(command['args_name'])))
                        break

def help_function(message, client, args):
    global ch
    if len(args) > 0 and args[0] == "verbose":
        helpMessageBody = "\n".join(["`{}`: {}\nArguments ({}): {}".format("` or `".join(command['trigger']), command['description'], command['args_num'], " ".join(command['args_name'])) for command in ch.commands])
    else:
        helpMessageBody = "\n".join(["`{}`: {}".format("` or `".join(command['trigger']), command['description']) for command in ch.commands])
    return helpMessageBody

def autoload(ch):
    global tag_id_as_command
    global client
    ch.add_command({
        'trigger': ['!help'],
        'function': help_function,
        'async': False,
        'args_num': 0,
        'args_name': [],
        'description': 'List commands and arguments'
        })
    tag_id_as_command = re.compile('^(?:Oh)?\s*(?:<@'+str(client.user.id)+'>|Fletch|Fletcher)[, .]*?')
