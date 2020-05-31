import os
import discord
import copy
import configparser
import logging

logger = logging.getLogger("fletcher")

class FletcherConfig:
    config_dict = None
    def __init__(self, base_config_path=os.getenv("FLETCHER_CONFIG", "./.fletcherrc")):
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(base_config_path)
        config = {s: {k: self.normalize(v, key=k) for k, v in dict(config.items(s)).items()} for s in config.sections()}
        self.config_dict = config

        if os.path.isdir(config.get("extra", {}).get("rc-path", "/unavailable")):
            for file_name in os.listdir(config.get("extra", {}).get("rc-path")):
                if file_name.isdigit():
                    guild_config = configparser.ConfigParser()
                    guild_config.optionxform = str
                    guild_config.read(f'{config["extra"]["rc-path"]}/{file_name}')
                    for section_name, section in guild_config.items():
                        if section_name == "DEFAULT":
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
                        for k, v in guild_config.items(section_name):
                            if k.startswith("SECTION_"):
                                k = k.split("_", 2)[1:]
                                subsection_key = k[0]
                                k = k[1]
                                if subsection_key not in config[section_key]:
                                    config[section_key][subsection_key] = {}
                                config[section_key][subsection_key][k] = self.normalize(v, key=k)
                            else:
                                config[section_key][k] = self.normalize(v, key=k)
        self.config_dict = config
        self.defaults = {
                "database": {
                    "engine": "postgres",
                    "user": "fletcher_user",
                    "tablespace": "fletcher",
                    "host": "localhost"
                    },
                "discord": {
                    "botNavel": "ƒ",
                    "botLogName": "fletcher",
                    "globalAdminIsServerAdmin": True,
                    "profile": False
                    },
                "nickmask": {
                    "conflictbots": [431544605209788416],
                    }
                }
        self.guild_defaults = {
                "synchronize": False,
                "sync-deletions": True,
                "sync-edits": True
                }
        self.channel_defaults = {
                "synchronize": False
                }

    def clone(self):
        return copy.deepcopy(self)

    def normalize_booleans(self, value, strict=False):
        if type(value) is bool:
            return value
        elif str(value).lower().strip() in ["on", "true", "yes"]:
            return True
        elif str(value).lower().strip() in ["off", "false", "no"]:
            return False
        elif strict:
            return None
        else:
            return value

    def normalize_numbers(self, value, strict=False):
        if type(value) in [int, float]:
            return value
        elif str(value).isdigit():
            return int(value)
        elif str(value).isnumeric():
            return float(value)
        elif strict:
            return None
        else:
            return value

    def str_to_array(self, string, delim=",", strip=True, filter_function=None.__ne__):
        array = string.split(delim)
        if strip:
            array = map(str.strip, array)
        if all(str(el).isnumeric() for el in array):
            array = map(int, array)
        return list(filter(filter_function, array))

    def normalize_array(self, value, strict=False):
        if type(value) is list:
            return value
        elif ", " in value or value.startswith(" ") or value.endswith(" "):
            return self.str_to_array(value,strip=True) or []
        elif "," in value:
            return self.str_to_array(value,strip=False) or []
        elif strict:
            return None
        else:
            return value

    def normalize(self, value, key=""):
        if type(value) is dict:
            return {k: self.normalize(v) for k, v in value.items()}
        elif type(value) is list:
            return [self.normalize(v) for v in value]
        elif "list" in key:
            return [self.normalize(v) for v in self.normalize_array(value)]
        else:
            return self.normalize_numbers(self.normalize_booleans(value, strict=False), strict=False)

    def __getitem__(self, key):
        return self.get(key=key)

    def get(self, key=None, default=None, section=None, guild=None, channel=None, use_category_as_channel_fallback=True, use_guild_as_channel_fallback=True):
        if guild is None and channel:
            if type(channel) in [discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]:
                guild = channel.guild
            else:
                raise ValueError("Guild was not specified and cannot be inferred from channel")
        if hasattr(guild, "id"):
            guild = guild.id
        if hasattr(channel, "id"):
            channel = channel.id
        if guild and channel and self.client.get_guild(guild).get_channel(channel).category_id:
            category = self.client.get_guild(guild).get_channel(channel).category_id
        else:
            category = None
        if   key is     None and section is     None and guild is     None and channel is     None:
            value = self.config_dict or self.defaults
        elif key is not None and section is     None and guild is     None and channel is     None:
            value = self.config_dict.get(key, self.defaults.get(key))
        elif key is     None and section is not None and guild is     None and channel is     None:
            value = self.config_dict.get(section, self.defaults.get(section, {}))
        elif key is not None and section is not None and guild is     None and channel is     None:
            value = self.config_dict.get(section, {}).get(key, None)
            if value is None:
                value = self.defaults.get(section, {}).get(key, None)
        elif key is     None and section is     None and guild is not None and channel is     None:
            value = self.config_dict.get(f"Guild {guild:d}", self.guild_defaults)
        elif key is not None and section is     None and guild is not None and channel is     None:
            value = self.config_dict.get(f"Guild {guild:d}", {}).get(key, None)
            if value is None:
                value = self.guild_defaults.get(key, None)
        elif key is     None and section is not None and guild is not None and channel is     None:
            value = self.config_dict.get(f"Guild {guild:d}", {}).get(section, None)
            if value is None:
                value = self.guild_defaults.get(section, {})
        elif key is not None and section is not None and guild is not None and channel is     None:
            value = self.config_dict.get(f"Guild {guild:d}", {}).get(section, {}).get(key, None)
            if value is None:
                value = self.guild_defaults.get(section, {}).get(key, None)
        elif key is     None and section is     None and guild is     None and channel is not None:
            raise ValueError("Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]")
        elif key is not None and section is     None and guild is     None and channel is not None:
            raise ValueError("Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]")
        elif key is     None and section is not None and guild is     None and channel is not None:
            raise ValueError("Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]")
        elif key is not None and section is not None and guild is     None and channel is not None:
            raise ValueError("Guild was not specified and cannot be inferred from channel [This code should be unreachable, something has gone terribly wrong]")
        elif key is not None and section is     None and guild is not None and channel is not None:
            value = self.config_dict.get(f"Guild {guild:d} - {channel:d}", {}).get(key, None)
            if not value and use_category_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d} - {category:d}").get(key, None)
            if not value and use_guild_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d}", {}).get(key, None)
            if not value:
                value = self.channel_defaults.get(key, None)
            if not value and use_guild_as_channel_fallback:
                value = self.guild_defaults.get(key, None)
        elif key is     None and section is not None and guild is not None and channel is not None:
            value = self.config_dict.get(f"Guild {guild:d} - {channel:d}", {}).get(section, None)
            if not value and use_category_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d} - {category:d}").get(section, None)
            if not value and use_guild_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d}", {}).get(section, None)
            if not value:
                value = self.channel_defaults.get(section, None)
            if not value and use_guild_as_channel_fallback:
                value = self.guild_defaults.get(section, None)
            if not value:
                value = {}
        elif key is not None and section is not None and guild is not None and channel is not None:
            value = self.config_dict.get(f"Guild {guild:d} - {channel:d}", {}).get(section, {}).get(key, None)
            if not value and use_category_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d} - {category:d}").get(section, {}).get(key, None)
            if not value and use_guild_as_channel_fallback:
                value = self.config_dict.get(f"Guild {guild:d}", {}).get(section, {}).get(key, None)
            if not value:
                value = self.channel_defaults.get(section, {}).get(key, None)
            if not value and use_guild_as_channel_fallback:
                value = self.guild_defaults.get(section, {}).get(key, None)
        if value is None or value == {} and default:
            value = default
        return value

    def __contains__(key):
        if   type(key) in [discord.Guild]:
            return f"Guild {guild.id:d}" in self.config_dict
        elif type(key) in [discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]:
            return f"Guild {key.guild.id:d} - {key.id:d}" in self.config_dict
        elif type(key) in [discord.DMChannel]:
            return f"Guild 0 - {key.recipient.id:d}" in self.config_dict
        else:
            return key in self.config_dict or key in self.defaults
