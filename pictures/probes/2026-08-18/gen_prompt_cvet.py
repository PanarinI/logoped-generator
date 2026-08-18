# -*- coding: utf-8 -*-
"""Проба цвета: там, где ч/б не различает. Слова взяты из картотеки."""
import base64, json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
KEY = open(os.path.expanduser("~/.config/logoped/openai.key")).read().strip()
OUT = os.path.dirname(os.path.abspath(__file__))

STYLE = (
    "Line drawing for a children's speech-therapy worksheet. "
    "One single object, isolated, canonical recognizable view, pure white background. "
    "BOLD THICK black outline of uniform weight, roughly 2.5 percent of the image width, "
    "closed and continuous, readable when printed 25 mm wide. "
    "FLAT SOLID COLOUR fills in the object's true natural colours, poster style: "
    "no gradients, no shading, no highlights, no texture, no outlines in colour. "
    "The black outline stays fully visible on top of every colour fill. "
    "Use as few colours as possible - only those that tell this object apart from "
    "the object it could be confused with. Keep every distinguishing feature and draw "
    "it with the same thick black line; drop ornament only. "
    "Correct real-life proportions, no cartoon deformation. "
    "No text, no numbers, no frame, no shadow, "
    "no ground line, no floor, no base, no platform, no surface under the object: "
    "the drawing fades out unfinished at the bottom edge."
)
ITEMS = {
    "борщ_ц":    "A bowl of borscht: deep beetroot-red soup in a plain white bowl seen three-quarter from above, a dollop of white sour cream in the middle and a spoon resting in the bowl. The soup colour is the point: it must read as beetroot-red, not brown.",
    "помидор_ц": "A single ripe tomato, front view: bright red round fruit with a small green star-shaped stalk on top.",
    "лимон_ц":   "A single lemon, side view: bright yellow oval fruit with the two typical pointed ends and a small green leaf at the stalk.",
    "свёкла_ц":  "A single beetroot: deep purple-red round root with a pale tapering tail at the bottom and green leaves with red stems growing from the top.",
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
    return f"✓ {name}"
with ThreadPoolExecutor(max_workers=4) as pool:
    for l in pool.map(one, ITEMS.items()): print(l, flush=True)
