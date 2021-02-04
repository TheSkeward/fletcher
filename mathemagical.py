from sys import exc_info
import discord
import io
import logging
import matplotlib.pyplot as plt
import messagefuncs
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


async def latex_render_function(message, client, args):
    global config
    try:
        renderstring = message.content.split(" ", 1)[1]
        if message.content.split(" ", 1)[0] == "!math":
            renderstring = f"$${renderstring}$$"
        if "math" in config and "extra-packages" in config["math"]:
            preamble = (
                r"\usepackage{"
                + r"}\usepackage{".join(config["math"]["extra-packages"].split(","))
                + r"}"
            )
        else:
            preamble = ""
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
            exc_type, exc_obj, exc_tb = exc_info()
            logger.debug("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
            await messagefuncs.sendWrappedMessage(
                    "||```tex\n" + renderstring.replace('\\\\', '\\') + "```||",
                    message.channel,
                    files=[
                        discord.File(
                            renderLatex(renderstring.replace('\\\\', '\\'), format="png", preamble=preamble),
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


async def autounload(ch):
    pass
