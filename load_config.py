import configparser
import copy
import logging
from typing import Dict, Union, Iterable, cast
import os
import discord

logger = logging.getLogger("fletcher")


class FletcherConfig:
    config_dict: Dict

    def __init__(self, base_config_path=os.getenv("FLETCHER_CONFIG", "./.fletcherrc")):
        configparse = configparser.ConfigParser()
        configparse.optionxform = str # type: ignore[attr-defined]
        self.client = None
        configparse.read(base_config_path)
        config: Dict[str, Union[Dict, Iterable, int, float, str]]  = {
            s: {k: self.normalize(v, key=k) for k, v in dict(configparse.items(s)).items()}
            for s in configparse.sections()
        }
        self.config_dict = config
        extra_section = config.get("extra", {})
        assert isinstance(extra_section, Dict)
        rc_path = str(extra_section.get("rc-path", "/unavailable"))
        if os.path.isdir(rc_path):
            for file_name in os.listdir(rc_path):
                if file_name.isdigit():
                    guild_config = configparser.ConfigParser()
                    guild_config.optionxform = str # type: ignore[attr-defined]
                    guild_config.read(f'{rc_path}/{file_name}')
                    for section_name in guild_config.keys():
                        if section_name.lower() in ["default", "general"]:
                            section_key = f"Guild {file_name}"
                        else:
                            section_key = f"Guild {file_name} - {section_name}"
                        logger.debug(f"RM: Adding section for {section_key}")
                        if section_key in config:
                            logger.info(
                                f"FC: Duplicate section definition for {section_key}, duplicate keys may be overwritten"
                            )
                        else:
                            config[section_key] = {}
                        section = cast(dict, config[section_key])
                        for k, v in guild_config.items(section_name):
                            section = cast(dict, config[section_key])
                            if k.startswith("SECTION_"):
                                subsection_key, k = k.split("_", 2)[1:]
                                subsection = section.get(subsection_key)
                                if not subsection:
                                    section[subsection_key] = {}
                                subsection = section.get(subsection_key)
                                assert isinstance(subsection, dict)
                                subsection[k] = self.normalize(
                                    v, key=k
                                )
                            else:
                                section[k] = self.normalize(v, key=k)
        self.config_dict = config
        self.defaults = {
            "database": {
                "engine": "postgres",
                "user": "fletcher_user",
                "tablespace": "fletcher",
                "host": "localhost",
            },
            "discord": {
                "botNavel": "ƒ",
                "botLogName": "fletcher",
                "globalAdminIsServerAdmin": True,
                "profile": False,
                "snappy": False,
            },
            "nickmask": {
                "conflictbots": [431544605209788416],
            },
        }
        self.guild_defaults = {
            "synchronize": False,
            "sync-deletions": True,
            "sync-edits": True,
            "blacklist-commands": [],
            "color-role-autocreate": True,
            "teleports": "embed",
            "snappy": False,
            "automod-blacklist-category": [],
        }
        self.channel_defaults = {"synchronize": False}

    def clone(self):
        return copy.deepcopy(self)

    def normalize_booleans(self, value: Union[str, bool]) -> Union[str, bool]:
        if isinstance(value, bool):
            return value
        if str(value).lower().strip() in ["on", "true", "yes"]:
            return True
        if str(value).lower().strip() in ["off", "false", "no"]:
            return False
        return value

    def normalize_numbers(self, value: Union[str, int, float]) -> Union[str, int, float]:
        if isinstance(value, (int, float)):
            return value
        if str(value).isdigit():
            return int(value)
        if str(value).isnumeric():
            return float(value)
        return value

    def str_to_array(self, string: str, delim=",", strip=True, filter_function=None.__ne__):
        array = string.split(delim)
        if strip:
            array = map(str.strip, array)
        if all(str(el).isnumeric() for el in array):
            array = map(int, array)
        return list(filter(filter_function, array))

    def normalize_array(self, value: Union[list, str]) -> list:
        if isinstance(value, list):
            return value
        if ", " in value or value.startswith(" ") or value.endswith(" "):
            return self.str_to_array(value, strip=True) or []
        if "," in value:
            return self.str_to_array(value, strip=False) or []
        return [value]

    def normalize(self, value: Union[dict, list, str, int, float], key: str="") -> Union[Dict, Iterable, float, int, str]:
        if isinstance(value, dict):
            return {k: self.normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.normalize(v) for v in value]
        if isinstance(value, str) and "list" in key:
            return [self.normalize(v) for v in self.normalize_array(value)]
        return self.normalize_numbers(
            self.normalize_booleans(str(value))
        )

    def __getitem__(self, key):
        return self.get(key=key)

    def __setitem__(self, key, item):
        self.config_dict[key] = item
        return self.config_dict[key]

    def get(
        self,
        key=None,
        default=None,
        section=None,
        guild=None,
        channel=None,
        use_category_as_channel_fallback=True,
        use_guild_as_channel_fallback=True,
    ):
        if guild is None and channel:
            if isinstance(
                channel,
                (
                    discord.TextChannel,
                    discord.VoiceChannel,
                    discord.CategoryChannel,
                ),
            ):
                guild = channel.guild
            else:
                guild = 0
        if isinstance(guild, discord.Guild):
            guild = guild.id
        if hasattr(channel, "id"):
            channel = channel.id
        if (
            guild
            and channel
            and self.client
            and self.client.get_guild(guild)
            and self.client.get_guild(guild).get_channel(channel)
            and self.client.get_guild(guild).get_channel(channel).category_id
        ):
            category = self.client.get_guild(guild).get_channel(channel).category_id
        else:
            category = None
        value = None
        if key is None and section is None and guild is None and channel is None:
            value = self.config_dict or self.defaults
        elif key is not None and section is None and guild is None and channel is None:
            value = self.config_dict.get(key, self.defaults.get(key))
        elif key is None and section is not None and guild is None and channel is None:
            value = self.config_dict.get(section, self.defaults.get(section, {}))
        elif (
            key is not None
            and section is not None
            and guild is None
            and channel is None
        ):
            value = self.config_dict.get(section, {}).get(key, None)
            if value is None:
                value = self.defaults.get(section, {}).get(key, None)
        elif key is None and section is None and guild is not None and channel is None:
            value = self.config_dict.get(f"Guild {guild:d}", self.guild_defaults)
        elif (
            key is not None
            and section is None
            and guild is not None
            and channel is None
        ):
            value = self.config_dict.get(f"Guild {guild:d}", {}).get(key, None)
            if value is None:
                value = self.guild_defaults.get(key, None)
        elif (
            key is None
            and section is not None
            and guild is not None
            and channel is None
        ):
            value = self.config_dict.get(f"Guild {guild:d}", {}).get(section, None)
            if value is None:
                value = self.guild_defaults.get(section, {})
        elif (
            key is not None
            and section is not None
            and guild is not None
            and channel is None
        ):
            value = (
                self.config_dict.get(f"Guild {guild:d}", {})
                .get(section, {})
                .get(key, None)
            )
            if value is None:
                value = self.guild_defaults.get(section, {}).get(key, None)
        elif key is None and section is None and guild is None and channel is not None:
            raise ValueError(
                "Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]"
            )
        elif (
            key is not None
            and section is None
            and guild is None
            and channel is not None
        ):
            raise ValueError(
                "Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]"
            )
        elif (
            key is None
            and section is not None
            and guild is None
            and channel is not None
        ):
            raise ValueError(
                "Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]"
            )
        elif (
            key is not None
            and section is not None
            and guild is None
            and channel is not None
        ):
            raise ValueError(
                "Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]"
            )
        elif (
            key is None
            and section is None
            and guild is not None
            and channel is not None
        ):
            value = self.config_dict.get(f"Guild {guild:d} - {channel:d}", {})
            if value is {} and use_category_as_channel_fallback and category:
                value = self.config_dict.get(f"Guild {guild:d} - {category:d}", {})
            if value is {} and use_guild_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d}", {})
            if value is {}:
                value = self.channel_defaults
        elif (
            key is not None
            and section is None
            and guild is not None
            and channel is not None
        ):
            value = self.config_dict.get(f"Guild {guild:d} - {channel:d}", {}).get(
                key, None
            )
            if value is None and use_category_as_channel_fallback and category:
                value = self.config_dict.get(f"Guild {guild:d} - {category:d}", {}).get(
                    key, None
                )
            if value is None and use_guild_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d}", {}).get(key, None)
            if value is None:
                value = self.channel_defaults.get(key, None)
            if value is None and use_guild_as_channel_fallback:
                value = self.guild_defaults.get(key, None)
        elif (
            key is None
            and section is not None
            and guild is not None
            and channel is not None
        ):
            value = self.config_dict.get(f"Guild {guild:d} - {channel:d}", {}).get(
                section, None
            )
            if value is None and use_category_as_channel_fallback and category:
                value = cast(dict, self.config_dict.get(f"Guild {guild:d} - {category:d}")).get(
                    section, None
                )
            if value is None and use_guild_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d}", {}).get(section, None)
            if value is None:
                value = self.channel_defaults.get(section, None)
            if value is None and use_guild_as_channel_fallback:
                value = self.guild_defaults.get(section, None)
            if value is None:
                value = {}
        elif (
            key is not None
            and section is not None
            and guild is not None
            and channel is not None
        ):
            value = (
                self.config_dict.get(f"Guild {guild:d} - {channel:d}", {})
                .get(section, {})
                .get(key, None)
            )
            if value is None and use_category_as_channel_fallback and category:
                value = (
                    cast(dict, self.config_dict.get(f"Guild {guild:d} - {category:d}"))
                    .get(section, {})
                    .get(key, None)
                )
            if value is None and use_guild_as_channel_fallback:
                value = (
                    self.config_dict.get(f"Guild {guild:d}", {})
                    .get(section, {})
                    .get(key, None)
                )
            if value is None:
                value = cast(dict, self.channel_defaults.get(section, {})).get(key, None)
            if value is None and use_guild_as_channel_fallback:
                value = self.guild_defaults.get(section, {}).get(key, None)
        if value is None or value == {} and default:
            value = default
        return value

    def __contains__(self, key):
        if isinstance(key, discord.Guild):
            return f"Guild {key.id:d}" in self.config_dict
        if isinstance(
            key,
            (
                discord.TextChannel,
                discord.VoiceChannel,
                discord.CategoryChannel,
            ),
        ):
            return f"Guild {key.guild.id:d} - {key.id:d}" in self.config_dict
        if isinstance(key, discord.DMChannel) and key.recipient is not None:
            return f"Guild 0 - {key.recipient.id:d}" in self.config_dict
        return key in self.config_dict or key in self.defaults


def expand_target_list(targets, guild):
    try:
        inputs = list(targets)
    except TypeError:
        inputs = [targets]
    targets = set()
    for target in inputs:
        if isinstance(target, str):
            if target.startswith("r:"):
                try:
                    members = guild.get_role(int(target[2:])).members
                except ValueError:
                    role = discord.utils.get(guild.roles, name=target[2:])
                    members = role.members if role else []
                targets.update(set(members))
            elif target.startswith("c:"):
                try:
                    channel = guild.get_channel(int(target[2:]))
                except ValueError:
                    channel = discord.utils.get(guild.text_channels, name=target[2:])
                targets.add(channel)
            else:
                try:
                    targets.add(guild.get_member(int(target)))
                except ValueError:
                    logger.info("Misconfiguration: could not expand {target}")
        else:
            # ID asssumed to be targets
            targets.add(guild.get_member(int(target)))
    targets.discard(None)
    return targets
