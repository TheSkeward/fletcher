from sys import exc_info
import discord
import io
import logging
import matplotlib.pyplot as plt
import messagefuncs
import subprocess
import sympy
import tempfile

logger = logging.getLogger("fletcher")


def renderLatex(formula, fontsize=12, dpi=300, format="svg", file=None, preamble=""):
    """Renders LaTeX formula into image or prints to file."""
    plt.rc("text", usetex=True)
    plt.rc("text.latex", preamble=preamble)
    plt.rc("font", family="serif")
    fig = plt.figure(figsize=(0.01, 0.01), frameon=True)
    fig.text(
        0,
        0,
        formula,
        fontsize=fontsize,
        verticalalignment="center_baseline",
        clip_on=True,
    )
    plt.tight_layout()

    output = io.BytesIO() if file is None else file
    fig.savefig(
        output,
        dpi=dpi,
        transparent=False,
        format=format,
        bbox_inches="tight",
        pad_inches=None,
    )

    plt.close(fig)

    if file is None:
        output.seek(0)
        return output


async def latex_render_function(message, client, args, extrapackages=[]):
    global config
    try:
        try:
            renderstring = message.content.split(" ", 1)[1]
        except:
            return await messagefuncs.sendWrappedMessage(
                "Please specify string to render as LaTeX",
                message.channel,
                delete_after=30,
            )
        if message.content.split(" ", 1)[0] == "!math":
            renderstring = f"$${renderstring}$$"
        if "math" in config and "extra-packages" in config["math"]:
            preamble = (
                r"\usepackage{"
                + r"}\usepackage{".join(config["math"]["extra-packages"].split(","))
                + r"}\usepackage{".join(extrapackages)
                + r"}"
            )
        else:
            preamble = "\\usepackage[utf8]{inputenc}"
        try:
            await messagefuncs.sendWrappedMessage(
                "||```tex\n" + renderstring + "```||",
                message.channel,
                files=[
                    discord.File(
                        renderLatex(renderstring, format="png", preamble=preamble),
                        filename="fletcher-render.png",
                    )
                ],
            )
        except RuntimeError as e:
            renderstringSlashed = (
                renderstring.replace("\\\\\\\\", "quadslash")
                .replace("\\", "\\\\")
                .replace("quadslash", "\\\\\\\\")
            )
            exc_type, exc_obj, exc_tb = exc_info()
            logger.debug("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
            await messagefuncs.sendWrappedMessage(
                "||```tex\n" + renderstringSlashed + "```||",
                message.channel,
                files=[
                    discord.File(
                        renderLatex(
                            renderstringSlashed,
                            format="png",
                            preamble=preamble,
                        ),
                        filename="fletcher-render.png",
                    )
                ],
            )
    except RuntimeError as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.debug("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
        await message.add_reaction("🚫")
        await messagefuncs.sendWrappedMessage(
            f"Error rendering LaTeX: {e}", message.author
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

async def tengwar_render_function(message, client, args):
    try:
        command = ['perl', './ptt/ptt.pl', '-oq', './ptt/es.ptm']
        p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        tengwar = p.communicate(input=' '.join(args).encode())[0]
        await latex_render_function(message, client, tengwar.split(" "), extrapackages=['tengwarscript'])
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Register functions in client
def autoload(ch):
    ch.add_command(
        {
            "trigger": ["!math", "!latex"],
            "function": latex_render_function,
            "async": True,
            "args_num": 0,
            "long_run": True,
            "args_name": [],
            "description": "Render arguments as LaTeX formula (does not require `$$` in `!math` mode)",
        }
    )
    ch.add_command(
        {
            "trigger": ["!tengwar"],
            "function": tengwar_render_function,
            "async": True,
            "args_num": 0,
            "long_run": True,
            "args_name": [],
            "description": "Render arguments as Tengwar via LaTeX (tengwarscript package)",
        }
    )


async def autounload(ch):
    pass
