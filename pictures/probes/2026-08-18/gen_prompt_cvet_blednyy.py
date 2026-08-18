# -*- coding: utf-8 -*-
"""Гипотеза: различение несёт ЛИНИЯ, цвет только усиливает — тогда один файл живёт в обоих режимах печати."""
import base64, json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
KEY = open(os.path.expanduser("~/.config/logoped/openai.key")).read().strip()
OUT = os.path.dirname(os.path.abspath(__file__))

STYLE = (
    "Line drawing for a children's speech-therapy worksheet. "
    "One single object, isolated, canonical view, pure white background. "
    "BOLD THICK black outline, uniform weight, about 2.5 percent of image width, readable at 25 mm. "
    "PALE LIGHT colour fills only, like a light watercolour wash: soft, desaturated, well below "
    "the darkness of the black line, no gradients, no shading, no dark areas anywhere. "
    "CRITICAL: everything that identifies the object must be drawn with the THICK BLACK LINE, "
    "not with colour - the drawing has to stay fully recognisable when the colour is removed "
    "and only the black lines remain. Colour merely reinforces what the line already says. "
    "Correct proportions, no cartoon deformation, no text, no frame, no shadow, "
    "no ground line, no floor, no base: the drawing fades out unfinished at the bottom."
)
ITEMS = {
    "борщ_п":    "A bowl of borscht seen three-quarter from above: a plain white bowl, a spoon resting in it, a dollop of sour cream in the middle, and thin strips of beetroot and shredded cabbage floating in the soup drawn as clear separate black lines. The soup itself is a pale beetroot-pink wash.",
    "помидор_п": "A single ripe tomato, front view, with a small star-shaped stalk on top; the round body carries two or three soft black contour lines showing its ribbed sides, and a black line marks the small dimple where the stalk sits. The body is a pale red wash.",
}
def one(kv):
    name, desc = kv
    body = json.dumps({"model": "gpt-image-1", "prompt": f"{desc}\n\n{STYLE}",
                       "n": 1, "size": "1024x1024", "quality": "low", "output_format": "png"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r: data = json.load(r)
    p = os.path.join(OUT, f"n_{name}.png")
    open(p, "wb").write(base64.b64decode(data["data"][0]["b64_json"]))
    return f"✓ {name}"
with ThreadPoolExecutor(max_workers=2) as pool:
    for l in pool.map(one, ITEMS.items()): print(l, flush=True)
