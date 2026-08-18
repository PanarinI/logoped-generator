# -*- coding: utf-8 -*-
"""Доводка: крыша с признаками, но без опоры; проверка приёма на втором «стоящем» предмете."""
import base64, json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
KEY = open(os.path.expanduser("~/.config/logoped/openai.key")).read().strip()
OUT = os.path.dirname(os.path.abspath(__file__))

STYLE = (
    "Black-and-white line drawing for a children's speech-therapy worksheet. "
    "One single object, isolated, canonical recognizable view, pure white background. "
    "BOLD THICK black outline of uniform weight, roughly 2.5 percent of the image width, "
    "closed and continuous, readable when printed 25 mm wide. "
    "Correct real-life proportions, no cartoon deformation. "
    "No hatching, no shading, no texture fill, no gray tones. "
    "IMPORTANT: keep every feature that tells this object apart from the object it could be "
    "confused with, and draw those features with the same thick line as the outline - "
    "a thick line must never mean a simplified or emptied object. Drop only ornament. "
    "No text, no numbers, no frame, no shadow, "
    "no ground line, no floor, no base, no platform, no surface under the object: "
    "the drawing fades out unfinished at the bottom edge."
)
ITEMS = {
    "крыша_v2": "A pitched house roof shown on its own, three-quarter view: two slopes meeting at a clear ridge line, and a brick chimney drawn as a three-dimensional box with its top opening and one side face visible. Roof tiles indicated by a few bold curved rows spread over the slope. The roof has NO bottom horizontal edge and nothing underneath it: both slopes simply end unfinished at the bottom of the drawing.",
    "крыша_v3": "A pitched house roof shown on its own, straight side view: a wide triangle-like roof with a clear ridge, overlapping rows of large roof tiles drawn with bold lines, and a tall brick chimney with a visible top opening rising from the left slope. The bottom of the roof is not closed by any line and there is no house, no wall and no floor under it: the slopes fade out unfinished.",
    "стол":     "A simple wooden table seen from a three-quarter view: flat rectangular top with visible thickness and four straight legs; the legs fade out unfinished at the bottom, with no floor line and nothing under the table.",
}
def one(kv):
    name, desc = kv
    body = json.dumps({"model": "gpt-image-1", "prompt": f"{desc}\n\n{STYLE}",
                       "n": 1, "size": "1024x1024", "quality": "low", "output_format": "png"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    p = os.path.join(OUT, f"n_{name}.png")
    open(p, "wb").write(base64.b64decode(data["data"][0]["b64_json"]))
    return f"✓ {name} {os.path.getsize(p)//1024} KB"
with ThreadPoolExecutor(max_workers=3) as pool:
    for l in pool.map(one, ITEMS.items()): print(l, flush=True)
