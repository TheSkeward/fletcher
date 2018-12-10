import discord
import io
import sympy
from sys import exc_info
import tempfile

async def latex_render_function(message, client, args):
    try:
        renderstring = "$$"+" ".join(args)+"$$"
        preamble = r'\documentclass[14pt]{article}\usepackage{mathtools}\pagenumbering{gobble}\begin{document}'
        # Unclear how to sandbox this well without a function whitelist :/
        # See service file for sandboxing info
        preview_file = io.BytesIO()
        sympy.preview(renderstring, viewer="BytesIO", output="png", outputbuffer=preview_file, preamble=preamble)
        preview_file.seek(0)
        await message.channel.send("`"+renderstring+"`", file=discord.File(preview_file, filename="fletcher-render.png"))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
