from mcipc.rcon import Client
import copy
import secrets
import string
import discord
import asyncio
import ujson
import traceback
import aiohttp
import messagefuncs
import socket
from dataclasses import dataclass
from dacite import from_dict
from sys import exc_info
from typing import List, Dict, Optional, Union

import logging

logger = logging.getLogger("fletcher")

sessions = {}
MAX_LINODES_PER_USER = 11


def check_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
        # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        socket.setdefaulttimeout(2.0)  # seconds (float)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            # print ("Port is open")
            return True
        else:
            # print ("Port is closed/filtered")
            return False
    except:
        pass


@dataclass(kw_only=True)
class Instance:
    id: int
    tags: List[str]
    status: str
    ipv4: List[str]


@dataclass(kw_only=True)
class StackScript:
    @dataclass(kw_only=True)
    class UDF:
        name: str
        label: str
        default: str
        manyof: Optional[str] = None  # comma separated

    id: int
    label: str
    description: str
    images: List[str]
    script: str
    user_defined_fields: List[UDF]

    def is_valid_udf_input(self, ss_data: Dict[str, str]) -> bool:
        return all(
            isinstance(ss_data.get(udf.name), str) for udf in self.user_defined_fields
        ) and all(
            discord.utils.get(self.user_defined_fields, name=key)
            for key in ss_data.keys()
        )

    def __str__(self):
        return f"""
__{self.label} ({self.id})__
*{self.description}*
Parameters: {", ".join((udf.name for udf in self.user_defined_fields))}
```bash
{self.script}
```
"""


class LinodeAPI:
    session: aiohttp.ClientSession
    base_url: str = "https://api.linode.com/v4/linode"
    headers: Dict[str, str]

    def __init__(self, token: str):
        self.session = aiohttp.ClientSession()
        self.headers = {
            "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
            "Authorization": f"Bearer {token}",
        }

    @classmethod
    def url_generator(cls, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return cls.base_url + path

    # 128 characters, max allowed by Linode
    @classmethod
    def generate_password(cls, length: int = 128) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def create_instance_from_stackscript(
        self,
        ss: StackScript,
        ss_data: Dict[str, str],
        authorized_users: List[str] = [],
        created_by: int = 0,
    ):
        if created_by:
            assert (
                len(await self.list_linodes(f"created-by-{created_by}"))
                < MAX_LINODES_PER_USER
            )
        assert ss.is_valid_udf_input(ss_data)
        headers = copy.deepcopy(self.headers)
        request_body: Dict[str, Union[str, int, List[str], Dict[str, str]]] = {
            "image": ss.images[0],
            "root_pass": type(self).generate_password(),
            "authorized_users": authorized_users,
            "tags": [
                "created-with-fletcher",
                f"stackscript-{ss.label}",
                *([f"created-by-{created_by}"] if created_by else []),
            ],
            "region": "us-east",
            "stackscript_data": ss_data,
            "stackscript_id": ss.id,
            "type": ss.description,
        }
        async with self.session.post(
            type(self).url_generator("instances"),
            json=request_body,
            raise_for_status=True,
            headers=headers,
        ) as resp:
            response_body = await resp.json()
            return {
                "request": request_body,
                "response": from_dict(data_class=Instance, data=response_body),
            }

    async def delete_linode(self, instance: Instance):
        headers = copy.deepcopy(self.headers)
        assert instance.id in [i.id for i in await self.list_linodes()]
        async with self.session.post(
            type(self).url_generator(f"instances/{instance.id}/shutdown"),
            raise_for_status=True,
            headers=headers,
        ) as resp:
            return await resp.json()

    async def update_linode_tags(self, instance: Instance, tags: List[str]) -> Dict:
        headers = copy.deepcopy(self.headers)
        assert instance.id in [i.id for i in await self.list_linodes()]
        if "created-with-fletcher" not in tags:
            tags.append("created-with-fletcher")
        async with self.session.put(
            type(self).url_generator(f"instances/{instance.id}"),
            raise_for_status=True,
            headers=headers,
            json={tags: tags},
        ) as resp:
            return await resp.json()

    async def really_delete_linode(self, instance: Instance):
        headers = copy.deepcopy(self.headers)
        assert instance.id in [i.id for i in await self.list_linodes()]
        await self.update_linode_tags(
            instance, ["created-with-fletcher", "deletion-requested"]
        )
        await asyncio.sleep(600)
        assert (
            "deletion-requested"
            in discord.utils.get(await self.list_linodes(), id=instance.id).tags
        )
        async with self.session.delete(
            type(self).url_generator(f"instances/{instance.id}"),
            raise_for_status=True,
            headers=headers,
        ) as resp:
            return await resp.json()

    async def list_linodes(self, tag: str = "created-with-fletcher") -> List[Instance]:
        headers = copy.deepcopy(self.headers)
        async with self.session.get(
            type(self).url_generator("instances"),
            raise_for_status=True,
            headers=headers,
        ) as resp:
            body = await resp.json()
            return [
                from_dict(data_class=Instance, data=i)
                for i in body["data"]
                if tag in i["tags"]
            ]

    async def get_linode(self, id: int) -> Optional[Instance]:
        headers = copy.deepcopy(self.headers)
        async with self.session.get(
            type(self).url_generator(f"instances/{id}"),
            raise_for_status=True,
            headers=headers,
        ) as resp:
            body = await resp.json()
            return from_dict(data_class=Instance, data=body)

    async def list_stackscripts(self, mine: bool = True) -> List[StackScript]:
        headers = copy.deepcopy(self.headers)
        filter_body = {"+order_by": "deployments_total", "+order": "desc", "mine": mine}
        headers["X-Filter"] = ujson.dumps(filter_body)
        async with self.session.get(
            type(self).url_generator("stackscripts"),
            raise_for_status=True,
            headers=headers,
        ) as resp:
            body = await resp.json()
            return [from_dict(data_class=StackScript, data=ss) for ss in body["data"]]


linode_api: LinodeAPI


async def linode_list_ss(message: discord.Message, client, args: List[str]):
    global linode_api
    try:
        ss_list = await linode_api.list_stackscripts()
        ss_list_str = "\n".join([str(ss) for ss in ss_list])
        await messagefuncs.sendWrappedMessage(
            f"""__StackScripts Available__\n{ss_list_str}""",
            target=message.channel,
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LLS[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def linode_create(message: discord.Message, client, args: List[str]):
    global linode_api
    try:
        ss = discord.utils.get(await linode_api.list_stackscripts(), label=args[0])
        assert ss
        ss_data = {
            udf.name: next(
                filter(lambda a: a.startswith(udf.name + "="), args), ""
            ).split("=", 1)[1]
            for udf in ss.user_defined_fields
        }
        instance_creation_data = await linode_api.create_instance_from_stackscript(
            ss, ss_data, ["l1n"], created_by=message.author.id
        )
        instance = instance_creation_data["response"]
        assert isinstance(instance, Instance)
        targetedMessage: discord.Message
        for target in [message.author, client.get_user(382984420321263617)]:
            targetedMessage = await messagefuncs.sendWrappedMessage(
                f"Root password for instance id {instance.id} at {instance.ipv4[0]} is ||{instance_creation_data['request']['root_pass']}||",
                target=target,
            )
        statusMessage = await messagefuncs.sendWrappedMessage(
            f"{ss.label} {instance.status} at {instance.ipv4[0]} <a:hourglass_animated:937514119991541770>",
            target=message.channel,
        )
        try:
            cur = conn.cursor()
            target = f"NOW() + '1 minute'::interval"
            cur.execute(
                f"INSERT INTO reminders (userid, guild, channel, message, content, scheduled, trigger_type) VALUES (%s, %s, %s, %s, %s, {target}, 'reminder');",
                [
                    382984420321263617,
                    0,
                    382984420321263617,
                    targetedMessage.id,
                    f"Consider deleting linode {instance.id}",
                ],
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.debug(e)
            logger.debug(instance_creation_data)
        while instance.status not in ["running", "offline"]:
            await asyncio.sleep(1)
            updated_instance = await linode_api.get_linode(instance.id)
            assert updated_instance
            if instance.status != updated_instance.status:
                await statusMessage.edit(
                    content=f"{ss.label} {instance.status} -> {updated_instance.status} at {instance.ipv4[0]} <a:hourglass_animated:937514119991541770>"
                )
                instance = updated_instance
        if instance.status == "offline":
            await messagefuncs.sendWrappedMessage(
                "Error initializing server - terminating. Try again in 10 minutes.",
                target=message.channel,
            )
            await linode_api.really_delete_linode(instance)
            return
        await statusMessage.edit(
            content=f"{ss.label} {instance.status} at {instance.ipv4[0]} ✅"
        )
        statusMessage = await messagefuncs.sendWrappedMessage(
            f"Initializing port watcher <a:hourglass_animated:937514119991541770>",
            target=message.channel,
        )
        await asyncio.sleep(60)
        ssh_on = False
        mc_on = False
        for _ in range(60):
            if not ssh_on and check_port(instance.ipv4[0], 22):
                ssh_on = True
                await statusMessage.edit(
                    content=f"__Services__\nSSH: On\nMinecraft: {'On' if mc_on else 'Off'}"
                )
            if not mc_on and check_port(instance.ipv4[0], 25565):
                mc_on = True
                await statusMessage.edit(
                    content=f"__Services__\nSSH: {'On' if ssh_on else 'Off'}\nMinecraft: On"
                )
            if ssh_on and mc_on:
                break
            await asyncio.sleep(5)
        await messagefuncs.sendWrappedMessage(
            f"Minecraft is ready {message.author.mention}", target=message.channel
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug(traceback.format_exc())
        logger.error(f"LCR[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
        await message.add_reaction("🚫")


async def minecraft_get_time_function(message, client, args):
    try:
        with Client(
            host=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_host",
                default="34.224.93.95",
            ),
            port=int(
                config.get(
                    guild=message.guild.id,
                    channel=message.channel.id,
                    key="minecraft_rcon-port",
                    default=25575,
                )
            ),
            passwd=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_rcon-password",
                default="",
            ),
        ) as session:
            await messagefuncs.sendWrappedMessage(
                session.time("query daytime"), message.channel
            )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MCGTF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def minecraft_send_say_function(message, client, args):
    try:
        message_text = " ".join(args)
        host = config.get(
            guild=message.guild.id,
            channel=message.channel.id,
            key="minecraft_host",
            default="34.224.93.95",
        )
        port = int(
            config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_rcon-port",
                default=25575,
            )
        )
        if not check_port(host, port):
            return
        with Client(
            host=host,
            port=port,
            passwd=config.get(
                guild=message.guild.id,
                channel=message.channel.id,
                key="minecraft_rcon-password",
                default="",
            ),
        ) as session:
            session.say(f"<{message.author.display_name}> {message_text}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"MCSSF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def autounload(ch):
    global linode_api
    asyncio.create_task(linode_api.session.close())


def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!mcgettime"],
            "function": minecraft_get_time_function,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 0,
            "args_name": [""],
            "description": "Get current time in minecraft",
        }
    )
    ch.add_command(
        {
            "trigger": ["!linode_list_ss"],
            "function": linode_list_ss,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 0,
            "args_name": [""],
            "description": "List StackScripts for calling account",
            "whitelist_guild": [634249282488107028, 843952851050430475],
        }
    )
    ch.add_command(
        {
            "trigger": ["!create_minecraft_server"],
            "function": linode_create,
            "async": True,
            "admin": "server",
            "hidden": False,
            "args_num": 4,
            "args_name": [
                "minecraft-fabric",
                "beroe",
                "0628947c-6067-4409-b24a-36678fb364e8",
                "FabricMC/fabric",
            ],
            "long_run": "channel",
            "description": "Create Minecraft Server.",
            "whitelist_guild": [634249282488107028, 843952851050430475],
        }
    )
    ch.add_command(
        {
            "trigger": ["!minecraftsendsay"],
            "function": minecraft_send_say_function,
            "async": True,
            "admin": False,
            "hidden": True,
            "args_num": 1,
            "args_name": ["tag"],
            "description": "Send message through to minecraft",
        }
    )
    global linode_api
    linode_api = LinodeAPI(
        ch.config.get(section="linode", key="personalAccessToken", default="")
    )
