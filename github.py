from sys import exc_info
import aiohttp
import discord
import logging
import os

logger = logging.getLogger("fletcher")

base_url = "https://api.github.com"


async def github_search_function(message, client, args):
    try:
        if "Guild " + str(message.guild.id) in config:
            scoped_config = config["Guild " + str(message.guild.id)]
        else:
            raise Exception(
                "No guild-specific configuration for source code management on guild "
                + str(message.guild)
            )
        get_url = "/search/issues"
        async with aiohttp.ClientSession(
            headers={
                "Authorization": "token " + config["github"]["personalAccessToken"]
            }
        ) as session:
            url = base_url + get_url
            async with session.get(
                url,
                params={"q": " ".join(args) + " repo:" + scoped_config["github-repo"]},
            ) as response:
                response_body = await response.json()
                if response_body["total_count"] == 0:
                    return await message.channel.send("No results found.")
                elif response_body["total_count"] <= 5:
                    for issue in response_body["items"]:
                        await message.channel.send(
                            embed=issue_to_embed(issue, issue["user"]["login"])
                        )
                else:
                    for issue in response_body["items"][:5]:
                        await message.channel.send(
                            embed=issue_to_embed(issue, issue["user"]["login"])
                        )
                    await message.channel.send(
                        f"Results truncated, {response_body['total_count']} total responses"
                    )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"GSF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def github_report_function(message, client, args):
    try:
        if "Guild " + str(message.guild.id) in config:
            scoped_config = config["Guild " + str(message.guild.id)]
        else:
            raise Exception(
                "No guild-specific configuration for source code management on guild "
                + str(message.guild)
            )
        post_url = "/repos/" + scoped_config["github-repo"] + "/issues"
        async with aiohttp.ClientSession(
            headers={
                "Authorization": "token " + config["github"]["personalAccessToken"]
            }
        ) as session:
            url = base_url + post_url
            content = "\n".join(message.content.splitlines(True)[1:])
            content = (
                content
                + "\n reported on behalf of "
                + message.author.display_name
                + " via [Fletcher](fletcher.fun) on Discord ("
                + message.guild.name
                + ":"
                + message.channel.name
                + ")"
            )
            title = " ".join(message.content.splitlines()[0].split(" ")[1:])
            async with session.post(
                url, json={"title": title, "body": content}
            ) as response:
                response_body = await response.json()
                await message.channel.send(
                    embed=issue_to_embed(response_body, message.author.display_name)
                )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"GRF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


def issue_to_embed(issue, author_name):
    if not issue["body"]:
        issue["body"] = "*Empty*"
        body_inline = True
    else:
        body_inline = False
        if len(issue["body"]) > 1024:
            issue["body"] = issue["body"][:1023] + "…"
    return (
        discord.Embed(
            title="#" + str(issue["number"]) + ": " + issue["title"],
            url=issue["html_url"],
        )
        .add_field(name="Status", value=issue["state"].capitalize(), inline=True)
        .add_field(name="Content", value=issue["body"], inline=body_inline)
        .set_footer(
            icon_url="https://download.nova.anticlack.com/fletcher/github.favicon.png",
            text=f"On behalf of {author_name}",
        )
    )


def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!ghreport"],
            "function": github_report_function,
            "async": True,
            "args_num": 1,
            "args_name": ["Line 1: Title", "[Line 2: Body]"],
            "description": "GitHub Issue Reporter (if server has repository configured)",
            "long_run": True,
        }
    )
    ch.add_command(
        {
            "trigger": ["!ghsearch"],
            "function": github_search_function,
            "async": True,
            "args_num": 1,
            "args_name": [
                "Query String (https://help.github.com/en/github/searching-for-information-on-github/understanding-the-search-syntax)"
            ],
            "description": "GitHub Issue Search",
            "long_run": True,
        }
    )
