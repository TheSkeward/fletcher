import discord
import io
import sympy
from sys import exc_info
import tempfile

import matplotlib.pyplot as plt

def renderLatex(formula, fontsize=12, dpi=300, format='svg', file=None):
    """Renders LaTeX formula into image or prints to file.
    """
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, u'${}$'.format(formula), fontsize=fontsize)

    output = io.BytesIO() if file is None else file
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=MathTextWarning)
        fig.savefig(output, dpi=dpi, transparent=True, format=format,
                    bbox_inches='tight', pad_inches=0.0, frameon=False)

    plt.close(fig)

    if file is None:
        output.seek(0)
        return output

async def latex_render_function(message, client, args):
    try:
        renderstring = "$$"+" ".join(args)+"$$"
        await message.channel.send("`"+renderstring+"`", file=discord.File(renderLatex(renderstring, format='png'), filename="fletcher-render.png"))
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        print("LRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Register functions in client
def autoload(ch):
    ch.add_command({
        'trigger': ['!math', '!latex'],
        'function': latex_render_function,
        'async': True,
        'args_num': 0,
        'args_name': [],
        'description': 'Render arguments as LaTeX formula (does not require `$$`)'
        })
