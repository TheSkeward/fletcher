import io
import aiohttp
from sys import exc_info
import traceback
import logging

logger = logging.getLogger("fletcher")


async def simple_get_image(url) -> io.BytesIO:
    byte_buffer: io.BytesIO = io.BytesIO()
    try:
        async with aiohttp.ClientSession(
            headers={"User-Agent": "Fletcher/0.1 (operator@noblejury.com)"}
        ) as session:
            logger.debug(url)
            async with session.get(str(url)) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"HttpProcessingError: {resp.status} Retrieving image failed!"
                    )
                resp_buffer = await resp.read()
                byte_buffer = io.BytesIO(resp_buffer)
                assert isinstance(byte_buffer, io.BytesIO)
                assert byte_buffer is not None
    except Exception as e:
        if str(e).startswith("HttpProcessingError"):
            raise e
        if type(e) is aiohttp.InvalidURL:
            raise e
        logger.debug(traceback.format_exc())
        _, _, exc_tb = exc_info()
        assert exc_tb is not None
        logger.error("SGI[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
    return byte_buffer


async def simple_post_image(post_url, image, filename, image_format, field_name="file"):
    try:
        async with aiohttp.ClientSession(
            headers={
                "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
            }
        ) as session:
            logger.debug(f"SPI: {post_url}")
            fd = aiohttp.FormData()
            fd.add_field(
                field_name, image, filename=filename, content_type=image_format
            )
            async with session.post(str(post_url), data=fd) as resp:
                buffer = await resp.text()
                if resp.status != 200:
                    raise Exception(
                        f"HttpProcessingError: {resp.status} Retrieving response failed!\n"
                    )
                return buffer
    except Exception as e:
        _, _, exc_tb = exc_info()
        assert exc_tb is not None
        logger.error("SPI[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
