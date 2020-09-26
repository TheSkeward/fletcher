import aiohttp
import discord
import logging
from git import Repo
from io import StringIO
from lxml import html
import os
from sys import exc_info

logger = logging.getLogger("fletcher")

# rorepo is a Repo instance pointing to the git-python repository.
# For all you know, the first argument to Repo is a path to the repository
# you want to work with
class VersionInfo:
    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.repo = Repo(dir_path)
        assert not self.repo.bare

    def latest_commit_log(self):
        return list(self.repo.iter_commits("master", max_count=1))[0].message.strip()


def whereami_function(message, client, args):
    global config
    scoped_config = None
    if "Guild " + str(message.guild.id) in config:
        scoped_config = config["Guild " + str(message.guild.id)]
    return scoped_config.get("whereami", f"{message.guild.name} ({message.guild.id})")


def status_function(message, client, args):
    global versioninfo
    return "Not much, just " + VersionInfo().latest_commit_log() + ". How about you?"


# From aiohttp Client Reference docs
async def fetch(client, url):
    request_headers = {"User-Agent": ("Fletcher/0.1 (operator@noblejury.com)")}
    async with client.get(url, headers=request_headers) as resp:
        assert resp.status == 200
        return await resp.text()


async def buglist_function(message, client, args):
    try:
        if len(args) == 0:
            return await messagefuncs.sendWrappedMessage(
                "Tracker available at https://todo.sr.ht/~nova/fletcher/, specify issue number for details.",
                message.client,
            )
        source_url = f"https://todo.sr.ht/~nova/fletcher/{args[0]}"
        async with aiohttp.ClientSession() as session:
            request_body = await fetch(session, source_url)
            # The HTML on this page does not lend itself to parsing :( Might be worth contributing a patch to upstream, if for no other reason than to get OpenGraph tags working (https://git.sr.ht/~sircmpwn/todo.sr.ht)
            root = html.document_fromstring(request_body)
            # -18 to chop " -- sr.ht todo"
            embed = (
                discord.Embed(title=root.xpath("//title")[0].text[:-18], url=source_url)
                .add_field(
                    name="Status",
                    value=root.xpath('//dt[.="Status"]/following-sibling::dd/strong')[
                        0
                    ].text.strip(),
                    inline=True,
                )
                .add_field(
                    name="Submitter",
                    value=root.xpath('//dt[.="Submitter"]/following-sibling::dd/a')[
                        0
                    ].text.strip(),
                    inline=True,
                )
                .add_field(
                    name="Updated",
                    value=root.xpath('//dt[.="Updated"]/following-sibling::dd/span')[
                        0
                    ].text.strip(),
                    inline=True,
                )
                .set_footer(
                    icon_url="https://download.lin.anticlack.com/fletcher/sr.ht.favicon.png",
                    text="On behalf of {}".format(message.author.display_name),
                )
            )
        if args[-1] == "INTPROC":
            return embed
        else:
            await messagefuncs.sendWrappedMessage(target=message.channel, embed=embed)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("BLF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!issue", "!todo"],
            "function": buglist_function,
            "async": True,
            "args_num": 0,
            "args_name": ["Issue # from the tracker"],
            "description": "Show Fletcher issue and todo information",
        }
    )
    ch.add_command(
        {
            "trigger": ["!whereami"],
            "function": whereami_function,
            "async": False,
            "hidden": True,
            "args_num": 0,
            "args_name": [],
            "description": "Tell user where they are",
        }
    )
    ch.add_command(
        {
            "trigger": ["!status"],
            "function": status_function,
            "async": False,
            "args_num": 0,
            "args_name": [],
            "description": "Tell user about the status",
        }
    )


async def autounload(ch):
    pass
