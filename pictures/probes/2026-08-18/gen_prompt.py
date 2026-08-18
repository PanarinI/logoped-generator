# -*- coding: utf-8 -*-
"""Проба 08-18: тот же стиль D, но ТОЛСТАЯ линия + низ не стоит на опоре."""
import base64, json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

KEY = open(os.path.expanduser("~/.config/logoped/openai.key")).read().strip()
OUT = os.path.dirname(os.path.abspath(__file__))

STYLE = (
    "Black-and-white line drawing for a children's speech-therapy worksheet. "
    "One single object, isolated, canonical recognizable view, pure white background. "
    "BOLD THICK black outline of uniform weight, roughly 2.5 percent of the image width, "
    "closed and continuous, no gaps, so the drawing stays readable when printed 25 mm wide. "
    "Correct real-life proportions, no cartoon deformation, no faces or eyes on inanimate objects. "
    "No hatching, no shading, no texture, no gray tones, no fills. "
    "Interior lines kept to the necessary minimum: only the features that tell this object "
    "apart from the object it could be confused with. Omit fine ornamental detail entirely. "
    "No text, no numbers, no arrows, no frame, no border, no shadow, "
    "no ground line, no floor, no base, no platform, no surface under the object: "
    "the drawing simply fades out unfinished at the bottom."
)

ITEMS = {
    "борщ":     "A bowl of beetroot soup seen from a three-quarter view, with a spoon resting in it and a dollop of sour cream on the surface; the bowl is deep and wide.",
    "грузовик": "A truck seen from the side: a separate high cargo box behind a distinctly smaller cab, two wheels; the cargo box and the cab are clearly separate volumes.",
    "катер":    "A small motorboat seen from the side: low open hull, a small windshield and a compact cabin, an outboard motor at the stern; no sails, no masts, no tall superstructure.",
    "крыша":    "A pitched house roof on its own: two slopes meeting at a ridge, a chimney on one slope, roof tiles suggested by only a few lines near the ridge; the roof is shown alone, with nothing under it and no horizontal line at its bottom edge.",
    "врач":     "A doctor standing, front view, full figure: open medical coat, a stethoscope around the neck, simple face; the coat is clearly a medical coat.",
    "горка":    "A children's playground slide seen from the side: a ladder with steps on the left, a platform on top, a wide smooth slide surface curving down to the right.",
    "рак":      "A crayfish seen from above: broad body, two large front claws, several pairs of legs, a fan-shaped tail; the claws are large and unmistakable.",
    "тигр":     "A tiger standing, side view, full body: strong body, thick tail, rounded ears, a few bold stripes on the body drawn as simple thick lines.",
}

def one(name_desc):
    name, desc = name_desc
    body = json.dumps({
        "model": "gpt-image-1",
        "prompt": f"{desc}\n\n{STYLE}",
        "n": 1, "size": "1024x1024", "quality": "low", "output_format": "png",
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
        path = os.path.join(OUT, f"n_{name}.png")
        open(path, "wb").write(base64.b64decode(data["data"][0]["b64_json"]))
        usage = data.get("usage", {})
        return f"✓ {name}  {os.path.getsize(path)//1024} KB  tokens={usage.get('total_tokens','?')}"
    except urllib.error.HTTPError as e:
        return f"✗ {name}  HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return f"✗ {name}  {type(e).__name__}: {e}"

with ThreadPoolExecutor(max_workers=4) as pool:
    for line in pool.map(one, ITEMS.items()):
        print(line, flush=True)
