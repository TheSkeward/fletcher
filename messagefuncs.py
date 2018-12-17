import discord
import io
import re
from sys import exc_info
def expand_guild_name(guild, prefix='', suffix=':', global_replace=False):
    # TODO refactor into config file
    acro_mapping = [ ('acn', 'a compelling narrative'), ('ACN', 'a compelling narrative') ]
    for k, v in acro_mapping:
        new_guild = guild.replace(prefix+k+suffix, prefix+v+suffix)
        if not global_replace:
            return new_guild

extract_identifiers_messagelink = re.compile('https://discordapp.com/channels/(\d+)/(\d+)/(\d+)', re.IGNORECASE)
async def teleport_function(message, client, args):
    global config
    try:
        if args[0] == "to":
            args.pop(0)
        fromChannel = message.channel
        if str(fromChannel.id) in config['teleport']['fromchannel-ban'].split(',') and not message.author.guild_permissions.manage_webhooks:
            print('Forbidden teleport')
            await fromChannel.send('Portals out of this channel have been disabled.', delete_after=60)
            return
        targetChannel = args[0].strip()
        channelLookupBy = "Name"
        toChannel = None
        toGuild = None
        if targetChannel.startswith('<#'):
            targetChannel = targetChannel[2:-1].strip()
            channelLookupBy = "ID"
        elif targetChannel.startswith('#'):
            targetChannel= targetChannel[1:].strip()
        print('Target Channel '+channelLookupBy+': '+targetChannel)
        if channelLookupBy == "Name":
            if ":" not in targetChannel:
                toChannel = discord.utils.get(fromChannel.guild.text_channels, name=targetChannel)
            else:
                targetChannel = expand_guild_name(targetChannel)
                toTuple = targetChannel.split(":")
                toGuild = discord.utils.get(client.guilds, name=toTuple[0].replace("_", " "))
                toChannel = discord.utils.get(toGuild.text_channels, name=toTuple[1])
        elif channelLookupBy == "ID":
            toChannel = client.get_channel(int(targetChannel))
        if fromChannel.id == toChannel.id:
            print('[WARNING] Attempt to open overlapping portal')
            return await fromChannel.send('You cannot open an overlapping portal! Access denied.')
        print('Opening From '+str(fromChannel))
        fromMessage = await fromChannel.send('Opening Portal To <#{}> ({})'.format(toChannel.id, toChannel.guild.name))
        try:
            print('Opening To '+str(toChannel))
            toMessage = await toChannel.send('Opening Portal To <#{}> ({})'.format(fromChannel.id, fromChannel.guild.name))
        except discord.Forbidden as e:
            print('[WARNING] Portal collaped half-open!')
            return await fromMessage.edit(content='Failed to open portal due to missing permissions! Access denied.')
        print('Editing From')
        embedTitle = "Portal opened to #{}".format(toChannel.name)
        if toGuild:
            embedTitle = embedTitle+" ({})".format(toChannel.guild.name)
        embedPortal = discord.Embed(title=embedTitle, description="https://discordapp.com/channels/{}/{}/{} {}".format(toChannel.guild.id, toChannel.id, toMessage.id, " ".join(args[1:]))).set_footer(icon_url="https://download.lin.anticlack.com/fletcher/blue-portal.png",text="On behalf of {}".format(message.author.nick or message.author))
        tmp = await fromMessage.edit(content=None,embed=embedPortal)
        print('Editing To')
        embedTitle = "Portal opened from #{}".format(fromChannel.name)
        if toGuild:
            embedTitle = embedTitle+" ({})".format(fromChannel.guild.name)
        embedPortal = discord.Embed(title=embedTitle, description="https://discordapp.com/channels/{}/{}/{} {}".format(fromChannel.guild.id, fromChannel.id, fromMessage.id, " ".join(args[1:]))).set_footer(icon_url="https://download.lin.anticlack.com/fletcher/orange-portal.png",text="On behalf of {}".format(message.author.nick or message.author))
        tmp = await toMessage.edit(content=None,embed=embedPortal)
        print('Portal Opened')
        try:
            if 'snappy' in config['discord'] and config['discord']['snappy']:
                await message.delete()
            return
        except discord.Forbidden:
            print("Couldn't delete portal request message")
        return 'Portal opened on behalf of {} to {}'.format(message.author, args[0])
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("TPF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def preview_messagelink_function(message, client, args):
    try:
        in_content = None
        if args is not None and args[0].isdigit():
            in_content = await messagelink_function(message, client, [args[0], 'INTPROC'])
        else:
            in_content = message.content
        # 'https://discordapp.com/channels/{}/{}/{}'.format(message.channel.guild.id, message.channel.id, message.id)
        urlParts = extract_identifiers_messagelink.search(in_content).groups()
        if len(urlParts) == 3:
            guild_id = int(urlParts[0])
            channel_id = int(urlParts[1])
            message_id = int(urlParts[2])
            guild = client.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            target_message = await channel.get_message(message_id)
            # created_at is naîve, but specified as UTC by Discord API docs
            sent_at = target_message.created_at.strftime("%B %d, %Y %I:%M%p UTC")
            content = target_message.content
            if content == "":
                content = "*No Text*"
            if message.guild and message.guild.id == guild_id and message.channel.id == channel_id:
                content = "Message from {} sent at {}:\n{}".format(target_message.author.name, sent_at, content)
            elif message.guild and message.guild.id == guild_id:
                content = "Message from {} sent in <#{}> at {}:\n{}".format(target_message.author.name, channel_id, sent_at, content)
            else:
                content = "Message from {} sent in #{} ({}) at {}:\n{}".format(target_message.author.name, channel.name, guild.name, sent_at, content)
            attachments = []
            if len(target_message.attachments) > 0:
                plural = ""
                if len(target_message.attachments) > 1:
                    plural = "s"
                content = content + "\n "+str(len(target_message.attachments))+" file"+plural+" attached"
                if target_message.channel.is_nsfw() and not message.channel.is_nsfw():
                    content = content + " from an R18 channel."
                    for attachment in target_message.attachments:
                        content = content + "\n• <"+attachment.url+">"
                else:
                    for attachment in target_message.attachments:
                        print("Syncing "+attachment.filename)
                        attachment_blob = io.BytesIO()
                        await attachment.save(attachment_blob)
                        attachments.append(discord.File(attachment_blob, attachment.filename))

            if args is not None and args[0].isdigit():
                content = content + "\n[Source](<https://discordapp.com/channels/{}/{}/{}>)".format(guild_id, channel_id, message_id)
            # TODO 🔭 to preview?
            return await message.channel.send(content, files=attachments)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("PMF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        # better for there to be no response in that case

async def messagelink_function(message, client, args):
    global config
    try:
        msg = None
        for channel in message.channel.guild.text_channels:
            try:
                msg = await channel.get_message(int(args[0]))
                break
            except discord.Forbidden as e:
                pass
            except discord.NotFound as e:
                pass
        if msg and not (len(args) == 2 and args[1] == 'INTPROC'):
            await message.channel.send('Message link on behalf of {}: https://discordapp.com/channels/{}/{}/{}'.format(message.author, msg.channel.guild.id, msg.channel.id, msg.id))
            if 'snappy' in config['discord'] and config['discord']['snappy']:
                await message.delete()
            return
        elif msg:
            return 'https://discordapp.com/channels/{}/{}/{}'.format(msg.channel.guild.id, msg.channel.id, msg.id)
        else:
            return await message.channel.send('Message not found', delete_after=60)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("MLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def bookmark_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            print("bookmarking via reaction")
            if str(args[0].emoji) == "🔖":
                return await args[1].send("Bookmark to conversation in #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to {}".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id, message.content))
            elif str(args[0].emoji) == "🔗":
                return await args[1].send("https://discordapp.com/channels/{}/{}/{}".format(message.channel.guild.id, message.channel.id, message.id))
        else:
            print("bookmarking via command")
            await message.author.send("Bookmark to conversation in #{} ({}) https://discordapp.com/channels/{}/{}/{} {}".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id, " ".join(args)))
            return await message.add_reaction('✅')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("BMF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Register this module's commands
def autoload(ch):
    ch.add_command({
        'trigger': ['!teleport', '!portal'],
        'function': teleport_function,
        'async': True,
        'args_num': 1,
        'args_name': ['string'],
        'description': 'Create a link bridge to another channel'
        })
    ch.add_command({
        'trigger': ['!message'],
        'function': messagelink_function,
        'async': True,
        'args_num': 1,
        'args_name': ['string'],
        'description': 'Create a link to the message with ID `!message XXXXXX`'
        })
    ch.add_command({
        'trigger': ['!preview'],
        'function': preview_messagelink_function,
        'async': True,
        'args_num': 1,
        'args_name': ['string'],
        'description': 'Retrieve message body by link (used internally to unwrap message links in chat)'
        })
    ch.add_command({
        'trigger': ['!bookmark', '🔖', '🔗'],
        'function': bookmark_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'DM the user a bookmark to the current place in conversation',
        })
