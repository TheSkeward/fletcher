import discord
import traceback
from jinja2 import Template
import subprocess
from functools import partial
from inspect import getsourcefile
import os.path as path
import sys

file = getsourcefile(lambda: 0)
assert file is not None
current_dir = path.dirname(path.abspath(file))
sys.path.insert(0, current_dir[: current_dir.rfind(path.sep)])
import load_config
from datetime import datetime, time, timedelta
import pytz
import boto3

today = datetime.today()
today = today.replace(
    year=int(sys.argv[1]), month=int(sys.argv[2]), day=int(sys.argv[3])
)
midnight = datetime.combine(today, time(0, 0))
midnight_2 = midnight + timedelta(days=1, minutes=1)
utc_dt = midnight.astimezone(pytz.utc)

config = load_config.FletcherConfig()
s3 = boto3.resource(
    "s3",
    region_name="us-east-1",
    aws_access_key_id=config.get(section="aws", key="access_key_id"),
    aws_secret_access_key=config.get(section="aws", key="secret_access_key"),
)

client = discord.Client()

# token from https://discordapp.com/developers
token = config.get(section="discord", key="botToken")


def convert_to_html_safe(text):
    markdown_to_html = subprocess.Popen(
        ["node", current_dir + "/markdown_to_html.js"],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    markdown_to_html.stdin.write(text.encode("utf8"))
    markdown_to_html.stdin.close()
    return markdown_to_html.stdout.read().decode("utf8")


def sizeof_fmt(num: int, suffix="B"):
    if not isinstance(num, int):
        return ""
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} {suffix}"


def channel_config_endpoint(
    config: load_config.FletcherConfig,
    guild: discord.Guild,
    channel: discord.TextChannel,
):
    endpoint = config.get(
        guild=guild.id,
        channel=channel.id,
        key="logging-endpoint",
        use_guild_as_channel_fallback=True,
        use_category_as_channel_fallback=True,
    )
    if not endpoint and channel.category:
        endpoint = config.get(
            guild=guild.id, channel=channel.category.id, key="logging-endpoint"
        )
    return endpoint


preamble = Template(open(current_dir + "/templates/preamble.template", "r").read())
preamble.globals["md_to_html"] = convert_to_html_safe
postamble = Template(open(current_dir + "/templates/postamble.template", "r").read())
message_group = Template(
    open(current_dir + "/templates/message_group.template", "r").read()
)
message_group.globals["md_to_html"] = convert_to_html_safe
message_group.globals["sizeof_fmt"] = sizeof_fmt
message_group.globals["ord"] = ord
message_group.globals["hex"] = hex


@client.event
async def on_ready():
    for guild in filter(lambda g: config.get(guild=g.id), client.guilds):
        for channel in filter(
            partial(channel_config_endpoint, config, guild),
            guild.text_channels,
        ):
            try:
                context = {
                    "guild": guild,
                    "channel": channel,
                    "message_count": 0,
                    "after": midnight,
                }
                log_today = preamble.render(**context)
                print(f"#{channel.name} {midnight}-{midnight_2}")
                async for message in channel.history(
                    after=midnight, before=midnight_2, limit=None
                ):
                    context["message_count"] += 1
                    # "{} {}:{} {} <{}>: {}\n".format(
                    #     message.id,
                    #     message.guild.name,
                    #     message.channel.name,
                    #     message.created_at,
                    #     message.author.display_name,
                    #     message.content,
                    # )
                    # for attachment in message.attachments:
                    #     log_today += "{} Attachment: {}\n".format(
                    #         message.id, attachment.url
                    #     )
                    context["clean_html_content"] = convert_to_html_safe(
                        message.clean_content
                    )
                    reactions = {}
                    for reaction in message.reactions:
                        reactions[reaction] = ", ".join(
                            [user.display_name async for user in reaction.users()]
                        )
                        # async for user in reaction.users():
                        #     log_today += "{} from {}\n".format(str(reaction), str(user))
                    # TODO(nova): better markdown support
                    # TODO(nova): better embed support https://github.com/Tyrrrz/DiscordChatExporter/blob/master/DiscordChatExporter.Core/Discord/Data/Embeds/YouTubeVideoEmbedProjection.cs
                    try:
                        log_today += message_group.render(
                            message=message, reactions=reactions, **context
                        )
                    except Exception as e:
                        print(e)
                        print(traceback.format_exc())
                        log_today += (
                            f"<div>Error rendering message ID {message.id}</div>"
                        )
                log_today += postamble.render(**context)
                print(
                    f'fletcher-logs/{guild.id}/{channel.id}/{midnight.strftime("%d-%m-%y")}.html { context["message_count"] }'
                )
                s3.Object(
                    channel_config_endpoint(config, guild, channel),
                    f'fletcher-logs/{guild.id}/{channel.id}/{midnight.strftime("%d-%m-%y")}.html',
                ).put(
                    Body=log_today,
                    ContentType="text/html",
                )
            except discord.Forbidden:
                print(
                    "Not enough permissions to retrieve logs for {}:{}".format(
                        guild.name, channel.name
                    )
                )
                pass
    await client.close()


client.run(token)
