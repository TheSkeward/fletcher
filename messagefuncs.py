from sys import exc_info
import discord
import exceptions
import io
import logging
import re
import textwrap

logger = logging.getLogger('fletcher')

def expand_guild_name(guild, prefix='', suffix=':', global_replace=False, case_sensitive=False):
    global config
    acro_mapping = config.get('discord-guild-expansions', { 'acn': 'a compelling narrative', 'ACN': 'a compelling narrative', 'EAC': 'EA Corner', 'D': 'Doissetep', 'bocu': 'Book of Creation Undone', 'abcal': 'Abandoned Castle'})
    new_guild = guild
    for k, v in acro_mapping.items():
        regex = re.compile(f'{prefix}{k}{suffix}|^{k}$', re.IGNORECASE)
        new_guild = regex.sub(prefix+v+suffix, new_guild)
        if not global_replace and new_guild != guild:
            logger.debug(f'Replacement found {k} -> {v}')
            return new_guild.replace('_', ' ')
    return new_guild.replace('_', ' ')



def xchannel(targetChannel, currentGuild):
    global ch
    channelLookupBy = 'Name'
    toChannel = None
    toGuild = None
    if targetChannel.startswith('<#'):
        targetChannel = targetChannel[2:-1].strip()
        channelLookupBy = 'ID'
    elif targetChannel.startswith('#'):
        targetChannel = targetChannel[1:].strip()
    logger.debug(f'XC: Channel Identifier {channelLookupBy}:{targetChannel}')
    if channelLookupBy == 'Name':
        if ':' not in targetChannel:
            toChannel = discord.utils.get(currentGuild.text_channels, name=targetChannel)
            toGuild = currentGuild
        else:
            targetChannel = expand_guild_name(targetChannel)
            toTuple = targetChannel.split(':')
            toGuild = discord.utils.get(ch.client.guilds, name=toTuple[0])
            if not toGuild:
                raise exceptions.DirectMessageException("Can't disambiguate channel name if in DM")
            toChannel = discord.utils.get(toGuild.text_channels, name=toTuple[1])
    elif channelLookupBy == 'ID':
        toChannel = ch.client.get_channel(int(targetChannel))
        toGuild = toChannel.guild
    return toChannel

async def sendWrappedMessage(msg, target, files=[]):
    msg_chunks = textwrap.wrap(msg, 2000, replace_whitespace=False)
    last_chunk = msg_chunks.pop()
    for chunk in msg_chunks:
        await target.send(chunk)
    await target.send(last_chunk, files=files)


extract_identifiers_messagelink = re.compile('(?<!<)https://(?:ptb\.)?discordapp.com/channels/(\d+)/(\d+)/(\d+)', re.IGNORECASE)
async def teleport_function(message, client, args):
    global config
    try:
        if args[0] == "to":
            args.pop(0)
        fromChannel = message.channel
        fromGuild = message.guild
        if str(fromChannel.id) in config['teleport']['fromchannel-ban'].split(',') and not message.author.guild_permissions.manage_webhooks:
            await fromChannel.send('Portals out of this channel have been disabled.', delete_after=60)
            raise Exception('Forbidden teleport')
        toChannelName = args[0].strip()
        toChannel = xchannel(toChannelName, fromGuild)
        if toChannel is None:
            await fromChannel.send('Could not find channel {}, please check for typos.'.format(toChannelName))
            raise Exception('Attempt to open portal to nowhere')
        toGuild = toChannel.guild
        if fromChannel.id == toChannel.id:
            await fromChannel.send('You cannot open an overlapping portal! Access denied.')
            raise Exception('Attempt to open overlapping portal')
        if not toChannel.permissions_for(toGuild.get_member(message.author.id)).send_messages:
            await fromChannel.send('You do not have permission to post in that channel! Access denied.')
            raise Exception('Attempt to open portal to forbidden channel')
        logger.debug('Entering in '+str(fromChannel))
        fromMessage = await fromChannel.send('Opening Portal To <#{}> ({})'.format(toChannel.id, toGuild.name))
        try:
            logger.debug('Exiting in '+str(toChannel))
            toMessage = await toChannel.send('Portal Opening From <#{}> ({})'.format(fromChannel.id, fromGuild.name))
        except discord.Forbidden as e:
            await fromMessage.edit(content='Failed to open portal due to missing permissions! Access denied.')
            raise Exception('Portal collaped half-open!')
        embedTitle = "Portal opened to #{}".format(toChannel.name)
        if toGuild != fromGuild:
            embedTitle = embedTitle+" ({})".format(toGuild.name)
        if toChannel.name == "hell":
            inPortalColor = ["red", discord.Colour.from_rgb(194,0,11)]
        else:
            inPortalColor = ["blue", discord.Colour.from_rgb(62,189,236)]
        behest = localizeName(message.author, fromGuild)
        embedPortal = discord.Embed(title=embedTitle, description="https://discordapp.com/channels/{}/{}/{} {}".format(toGuild.id, toChannel.id, toMessage.id, " ".join(args[1:])), color=inPortalColor[1]).set_footer(icon_url="https://download.lin.anticlack.com/fletcher/"+inPortalColor[0]+"-portal.png",text="On behalf of {}".format(behest))
        if config['teleport']['embeds'] == "on":
            tmp = await fromMessage.edit(content=None,embed=embedPortal)
        else:
            tmp = await fromMessage.edit(content="**{}** <https://discordapp.com/channels/{}/{}/{}>\nOn behalf of {}\n{}".format(embedTitle, toGuild.id, toChannel.id, toMessage.id, behest, " ".join(args[1:])))
        embedTitle = "Portal opened from #{}".format(fromChannel.name)
        behest = localizeName(message.author, toGuild)
        if toGuild != fromGuild:
            embedTitle = embedTitle+" ({})".format(fromGuild.name)
        embedPortal = discord.Embed(title=embedTitle, description="https://discordapp.com/channels/{}/{}/{} {}".format(fromGuild.id, fromChannel.id, fromMessage.id, " ".join(args[1:])), color=discord.Colour.from_rgb(194,64,11)).set_footer(icon_url="https://download.lin.anticlack.com/fletcher/orange-portal.png",text="On behalf of {}".format(behest))
        if config['teleport']['embeds'] == "on":
            tmp = await toMessage.edit(content=None,embed=embedPortal)
        else:
            tmp = await toMessage.edit(content="**{}** <https://discordapp.com/channels/{}/{}/{}>\nOn behalf of {}\n{}".format(embedTitle, fromGuild.id, fromChannel.id, fromMessage.id, behest, " ".join(args[1:])))
        try:
            if 'snappy' in config['discord'] and config['discord']['snappy']:
                await message.delete()
            return
        except discord.Forbidden:
            raise Exception("Couldn't delete portal request message")
        return 'Portal opened on behalf of {} to {}'.format(message.author, args[0])
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("TPF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

extract_links = re.compile('(?<!<)((https?|ftp):\/\/|www\.)(\w.+\w\W?)', re.IGNORECASE)
async def preview_messagelink_function(message, client, args):
    try:
        in_content = None
        if args is not None and len(args) >= 1 and args[0].isdigit():
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
            if guild is None:
                logger.warning("PMF: Fletcher is not in guild ID "+str(guild_id))
                return
            channel = guild.get_channel(channel_id)
            target_message = await channel.fetch_message(message_id)
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
            if target_message.channel.is_nsfw() and not message.channel.is_nsfw():
                content = extract_links.sub(r'<\g<0>>', content)
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
                        logger.debug("Syncing "+attachment.filename)
                        attachment_blob = io.BytesIO()
                        await attachment.save(attachment_blob)
                        attachments.append(discord.File(attachment_blob, attachment.filename))

            if args is not None and len(args) >= 1 and args[0].isdigit():
                content = content + f'\nSource: https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}'
            # TODO 🔭 to preview?
            return await sendWrappedMessage(content, message.channel, files=attachments)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("PMF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        # better for there to be no response in that case

async def messagelink_function(message, client, args):
    global config
    try:
        msg = None
        for channel in message.channel.guild.text_channels:
            try:
                msg = await channel.fetch_message(int(args[0]))
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
        logger.error("MLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def bookmark_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User:
            if str(args[0].emoji) == "🔖":
                return await sendWrappedMessage("Bookmark to conversation in #{} ({}) https://discordapp.com/channels/{}/{}/{} via reaction to {}".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id, message.content), args[1])
            elif str(args[0].emoji) == "🔗":
                return await args[1].send("https://discordapp.com/channels/{}/{}/{}".format(message.channel.guild.id, message.channel.id, message.id))
        else:
            await message.author.send("Bookmark to conversation in #{} ({}) https://discordapp.com/channels/{}/{}/{} {}".format(message.channel.name, message.channel.guild.name, message.channel.guild.id, message.channel.id, message.id, " ".join(args)))
            return await message.add_reaction('✅')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("BMF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def paste_function(message, client, args):
    try:
        async for historical_message in message.author.history(oldest_first=False, limit=10):
            if historical_message.author == client.user:
                paste_content = historical_message.content
                attachments = []
                if len(historical_message.attachments) > 0:
                    for attachment in historical_message.attachments:
                        logger.debug("Syncing "+attachment.filename)
                        attachment_blob = io.BytesIO()
                        await attachment.save(attachment_blob)
                        attachments.append(discord.File(attachment_blob, attachment.filename))
                paste_message = await message.channel.send(paste_content, files=attachments)
                await preview_messagelink_function(paste_message, client, args)
                return
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("PF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def subscribe_function(message, client, args):
    global ch
    try:
        guild_config = ch.scope_config(guild=message.guild, mutable=True)
        if not guild_config.get('subscribe'):
            guild_config['subscribe'] = {}
        if not guild_config['subscribe'].get(message.id):
            guild_config['subscribe'][message.id] = []
        if len(args) == 2 and type(args[1]) is discord.User:
            cur = conn.cursor()
            if args[2] != 'remove':
                cur.execute("INSERT INTO user_preferences (user_id, guild_id, key, value) VALUES (%s, %s, 'subscribe', %s);", [args[1].id, message.guild.id, message.id])
                conn.commit()
                guild_config['subscribe'][message.id].append(args[1].id)
                args[1].send(f'Subscribed to notifications from https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}')
            else:
                cur.execute("DELETE FROM user_preferences WHERE user_id = %s AND guild_id = %s AND key = 'subscribe' AND value = %s;", [args[1].id, message.guild.id, message.id])
                conn.commit()
                guild_config['subscribe'][message.id].remove(args[1].id)
                args[1].send(f'Unsubscribed from notifications for https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}')
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SUBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def localizeName(user, guild):
    localized = guild.get_member(user.id)
    if localized is None:
        localizeName = user.name
    else:
        localized = localized.display_name
    return localized

sanitize_font = re.compile(r'[^❤A-Za-z0-9 /]')

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
        'long_run': True,
        'args_name': ['string'],
        'description': 'Retrieve message body by link (used internally to unwrap message links in chat)'
        })
    ch.add_command({
        'trigger': ['🔖', '🔗', '!bookmark'],
        'function': bookmark_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'DM the user a bookmark to the current place in conversation',
        })
    ch.add_command({
        'trigger': ['!paste'],
        'function': paste_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Paste last copied link',
        })
    ch.add_command({
        'trigger': ['📡'],
        'function': subscribe_function,
        'async': True,
        'remove': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Subscribe to reaction notifications on this message',
        })
