import discord
import io
import sympy
from sys import exc_info
import tempfile

async def latex_render_function(message, client, args):
    try:
        renderstring = "$$"+" ".join(args)+"$$"
        # Unclear how to sandbox this well without a function whitelist :/
        # See service file for sandboxing info
        preview_file = io.BytesIO()
        preview(renderstring, viewer="BytesIO", output="png", outputbuffer=preview_file)
        await message.channel.send("`"+renderstring+"`", file=preview_file)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
