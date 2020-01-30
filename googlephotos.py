import aiohttp
import discord
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import io
import logging
import random
from sys import exc_info

logger = logging.getLogger("fletcher")


def authorize_googlephotos_function(message=None, client=None, args=None):
    global config
    global state
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {"web": config["google-photos"]},
        ["https://www.googleapis.com/auth/photoslibrary.readonly"],
    )

    # Indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required.
    flow.redirect_uri = "https://novalinium.com/breksta-oauth"

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type="offline",
        prompt="consent",
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes="true",
    )
    logger.warning(
        "Head to this URL, then use the `!photos_login` command with the resulting URL as the parameter: "
        + authorization_url
    )
    return authorization_url


def login_googlephotos_function(message=None, client=None, args=None):
    global config
    global gphotos
    global state
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {"web": config["google-photos"]},
        ["https://www.googleapis.com/auth/photoslibrary.readonly"],
        state=state,
    )
    flow.redirect_uri = "https://novalinium.com/breksta-oauth"
    flow.fetch_token(authorization_response=args[0])
    credentials = flow.credentials
    freeze = f"""```
[google-photos]
token = {credentials.token}
refresh_token = {credentials.refresh_token}
token_uri = {credentials.token_uri}
client_id = {credentials.cleint_id}
client_secret = {credentials.client_secret}
scopes = {credentials.scopes}
```"""
    logger.warning(freeze)
    gphotos = build("photoslibrary", "v1", credentials=credentials)
    return freeze


def listalbums_function(message, client, args):
    global gphotos
    try:
        return "\n".join(
            [
                f'{album.get("title")} ({album.get("id")}) <{album.get("productUrl")}>'
                for album in gphotos.albums().list().execute()["albums"]
            ]
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"LAF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def lesbaru_function(message, client, args):
    global config
    global gphotos
    global lesbaru_list
    try:
        for counter in range(5):
            try:
                image = lesbaru_list.pop()
                fullSizeImage = f'{image.get("baseUrl")}=w{image.get("mediaMetadata").get("width")}-h{image.get("mediaMetadata").get("height")}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(fullSizeImage) as resp:
                        buffer = io.BytesIO(await resp.read())
                        if resp.status != 200:
                            raise Exception(
                                "HttpProcessingError: "
                                + str(resp.status)
                                + " Retrieving image failed!"
                            )
                        await message.channel.send(
                            files=[discord.File(buffer, image.get("filename"))]
                        )
                        break
            except (
                ValueError,
                BrokenPipeError,
                IndexError,
                AttributeError,
                Exception,
            ) as e:
                # Retry!
                exc_type, exc_obj, exc_tb = exc_info()
                logger.debug(f"TCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                logger.debug(f"TCF: Refreshing lesbaru_list, counter is at {counter}")
                lesbaru_list = list(
                    gphotos.mediaItems()
                    .search(body={"albumId": config["google-photos"]["lesbaru"]})
                    .execute()
                    .get("mediaItems")
                )
                random.shuffle(lesbaru_list)
                continue
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


async def twilestia_function(message, client, args):
    global config
    global gphotos
    global twilestia_list
    try:
        for counter in range(5):
            try:
                image = twilestia_list.pop()
                fullSizeImage = f'{image.get("baseUrl")}=w{image.get("mediaMetadata").get("width")}-h{image.get("mediaMetadata").get("height")}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(fullSizeImage) as resp:
                        buffer = io.BytesIO(await resp.read())
                        if resp.status != 200:
                            raise Exception(
                                "HttpProcessingError: "
                                + str(resp.status)
                                + " Retrieving image failed!"
                            )
                        await message.channel.send(
                            files=[discord.File(buffer, image.get("filename"))]
                        )
                        break
            except (
                ValueError,
                BrokenPipeError,
                IndexError,
                AttributeError,
                Exception,
            ) as e:
                # Retry!
                exc_type, exc_obj, exc_tb = exc_info()
                logger.debug(f"TCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")
                logger.debug(f"TCF: Refreshing twilestia_list, counter is at {counter}")
                twilestia_list = list(
                    gphotos.mediaItems()
                    .search(body={"albumId": config["google-photos"]["twilestia"]})
                    .execute()
                    .get("mediaItems")
                )
                random.shuffle(twilestia_list)
                continue
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error(f"TCF[{exc_tb.tb_lineno}]: {type(e).__name__} {e}")


def autoload(ch):
    global config
    global gphotos
    global twilestia_list
    global lesbaru_list
    ch.add_command(
        {
            "trigger": ["!twilestia"],
            "function": twilestia_function,
            "async": True,
            "admin": False,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "Return a random twilestia image (ˢʰᶦᵖᶦᵗˡᶦᵏᵉᶠᵉᵈᵉˣ)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!lesbaru"],
            "function": lesbaru_function,
            "async": True,
            "admin": False,
            "hidden": False,
            "args_num": 0,
            "args_name": [],
            "description": "Return a random Lesbian Subaru ad",
        }
    )
    ch.add_command(
        {
            "trigger": ["!photos_list_albums", "!pla"],
            "function": listalbums_function,
            "async": False,
            "admin": "global",
            "long_run": True,
            "hidden": True,
            "args_num": 0,
            "args_name": [],
            "description": "Google Photos Album List",
        }
    )
    ch.add_command(
        {
            "trigger": ["!photos_login"],
            "function": login_googlephotos_function,
            "async": False,
            "admin": "global",
            "args_num": 1,
            "args_name": [],
            "description": "Log onto Google Photos (Admin)",
        }
    )
    if "refresh_token" not in config["google-photos"]:
        return authorize_googlephotos_function()
    try:
        gphotos.albums().list().execute()["albums"]
    except Exception:
        gphotos = build(
            "photoslibrary",
            "v1",
            credentials=google.oauth2.credentials.Credentials(
                config["google-photos"]["token"],
                refresh_token=config["google-photos"]["refresh_token"],
                token_uri=config["google-photos"]["token_uri"],
                client_id=config["google-photos"]["client_id"],
                client_secret=config["google-photos"]["client_secret"],
            ),
        )
    try:
        logger.debug("GPAL: length(lesbaru_list)=" + str(len(twilestia_list)))
    except Exception:
        lesbaru_list = []
    try:
        logger.debug("GPAL: length(twilestia_list)=" + str(len(twilestia_list)))
    except Exception:
        twilestia_list = []
