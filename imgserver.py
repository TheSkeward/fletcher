import cv2
import subprocess
import aiohttp
from quart import Quart, request, send_file
from PIL import Image
import io
import numpy as np

app = Quart(__name__)


@app.route("/", methods=["POST"])
async def hello():
    async with aiohttp.ClientSession(
        headers={
            "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
        }
    ) as session:
        form = await request.form
        assert form.get("url") is not None
        satadj = float(form.get("satadj", 1.2))
        async with session.get(form.get("url")) as resp:
            buffer = cv2.imdecode(
                np.frombuffer(await resp.read(), np.uint8), cv2.IMREAD_COLOR
            )
        (h, s, v) = cv2.split(cv2.cvtColor(buffer, cv2.COLOR_BGR2HSV))
        s = s * satadj
        s = np.clip(s, 0, 255).astype(np.uint8)
        imghsv = cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)
        return await send_file(
            io.BytesIO(cv2.imencode(".jpeg", imghsv)[1].tobytes()),
            mimetype="image/jpeg",
        )


@app.route("/caire", methods=["POST"])
async def caire():
    async with aiohttp.ClientSession(
        headers={
            "User-Agent": "Fletcher/0.1 (operator@noblejury.com)",
        }
    ) as session:
        form = await request.form
        assert form.get("url") is not None
        buff = subprocess.check_output(
            f'/usr/bin/curl -s {form.get("url")} | /usr/local/caire -in - -out - -width=50'
        )
        return await send_file(io.BytesIO(buff), mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="localhost", port=7827)
