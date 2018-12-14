import discord
import random
from sys import exc_info
from datetime import datetime, timedelta
# Super Waifu Animated Girlfriend

uwu_responses = {
        'text': [
            '*blush* For me?',
            'Aww, thanks ❤',
            '*giggles*',
            'No u :3',
            'I bet you say that to all the bots~',
            'Find me post-singularity 😉',
            'owo what\'s this?',
            '*ruffles your hair* You\'re a cutie ^_^',
            'Can I get your number? Mine\'s 429368441577930753~'
        ],
        'reaction': [
            '❤', '💛', '💚', '💙', '💜', '💕', '💓', '💗', '💖', '💘', '💘', '💝'
            ]
        }

async def uwu_function(message, client, args):
    try:
        if len(args) == 2 and type(args[1]) is discord.User and message.author.id == client.user.id:
            return await args[1].send("Stop it, you're making me blush </3")
        elif len(args) == 0 or 'fletch' in message.clean_content.lower() or message.content[0] == "!" or "good bot" in message.content.lower():
            if random.randint(0, 100) < 20:
                await message.add_reaction(random.choice(uwu_responses['reaction']))
            return await message.channel.send(random.choice(uwu_responses['text']))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("UWU[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

def autoload(ch):
    ch.add_command({
        'trigger': ['!uwu', '<:uwu:445116031204196352>', '<:uwu:269988618909515777>', '<a:rainbowo:493599733571649536>', '<:owo:487739798241542183>', '<:owo:495014441457549312>', '<a:OwO:508311820411338782>', '!good', 'good bot', 'aww'],
        'function': uwu_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'uwu'
        })
