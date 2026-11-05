"""Turn Instagram captions, pasted text and photos into Recipe objects.

Three routes:
  * parse_text()            - offline, rule-based. Works on any pasted caption/recipe text.
  * ai_extract()            - optional, uses the Claude API (text or photo) for much better results.
  * fetch_instagram_caption - best-effort grab of a public post's caption from its link.
"""
import base64
import json
import os
import re
import ssl
import urllib.request

from db import CARBS, PROTEINS, Recipe

try:  # bundled CA certs - Android's Python has no system cert store
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover
    _SSL = ssl.create_default_context()

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-5-5"

# ------------------------------------------------------------------ guessing
_PROTEIN_WORDS = {
    "Chicken": ["chicken", "thigh", "drumstick"],
    "Beef": ["beef", "steak", "mince", "brisket"],
    "Pork": ["pork", "bacon", "chorizo", "sausage", "ham", "pancetta"],
    "Lamb": ["lamb", "mutton"],
    "Fish": ["salmon", "cod", "tuna", "haddock", "fish", "mackerel", "sea bass"],
    "Seafood": ["prawn", "shrimp", "mussel", "squid", "crab", "scallop", "lobster"],
    "Vegetarian": ["halloumi", "paneer", "feta", "cheese", "egg"],
    "Vegan": ["tofu", "tempeh", "chickpea", "lentil", "bean"],
}
_CARB_WORDS = {
    "Rice": ["rice", "risotto", "arborio", "basmati", "jasmine"],
    "Pasta": ["pasta", "spaghetti", "penne", "linguine", "fusilli", "tagliatelle", "lasagne", "macaroni", "orzo", "rigatoni", "gnocchi"],
    "Potato": ["potato", "chips", "fries", "mash"],
    "Noodles": ["noodle", "ramen", "udon", "soba"],
    "Bread": ["bread", "naan", "tortilla", "wrap", "pitta", "bun", "flatbread", "toast"],
}
_CUISINE_WORDS = {
    "Italian": ["parmesan", "basil", "risotto", "pasta", "pesto", "mozzarella"],
    "Mexican": ["tortilla", "taco", "burrito", "jalapeño", "jalapeno", "chipotle", "enchilada", "salsa"],
    "Indian": ["garam masala", "curry", "tikka", "dal", "paneer", "naan", "turmeric"],
    "Chinese": ["soy sauce", "hoisin", "five spice", "szechuan", "sichuan", "chow mein", "wok"],
    "Japanese": ["miso", "mirin", "teriyaki", "katsu", "ramen", "udon"],
    "Thai": ["fish sauce", "lemongrass", "thai", "pad thai", "galangal"],
    "Korean": ["gochujang", "kimchi", "bulgogi"],
    "Greek": ["feta", "tzatziki", "oregano", "gyros"],
    "British": ["pie", "roast", "gravy", "worcestershire"],
}


def _guess(text: str, table: dict[str, list[str]]) -> str:
    low = text.lower()
    best, best_score = "", 0
    for key, words in table.items():
        score = sum(low.count(w) for w in words)
        if score > best_score:
            best, best_score = key, score
    return best


# ------------------------------------------------------------------ offline parser
_ING_HDR = re.compile(r"^\W*(ingredients?|you(?:'ll)? need|shopping list)\b.*$", re.I)
_METHOD_HDR = re.compile(r"^\W*(method|instructions?|directions?|steps?|how to make( it)?|recipe|preparation)\b\W*$", re.I)
_BULLET = re.compile(r"^(?:[\s\-–•*·▪▫◦✅✔🔸🔹️]+|\s*(?:step\s*)?\d{1,2}\s*[.):]\s+)+", re.I)
_HASHTAG = re.compile(r"(#\w+\s*)+$")


def _clean(line: str) -> str:
    line = _HASHTAG.sub("", line).strip()
    return _BULLET.sub("", line).strip() if line else line


def parse_text(text: str, source: str = "") -> Recipe:
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    lines = [l for l in lines if not re.fullmatch(r"\s*(#\w+\s*)+", l)]  # drop hashtag-only lines
    non_empty = [l for l in lines if l.strip()]
    name = _clean(non_empty[0])[:80] if non_empty else "Imported recipe"

    ing_i = next((i for i, l in enumerate(lines) if _ING_HDR.match(l.strip())), None)
    met_i = next((i for i, l in enumerate(lines) if _METHOD_HDR.match(l.strip()) and (ing_i is None or i > ing_i)), None)

    desc_lines, ingredients, method_lines = [], [], []
    if ing_i is not None:
        title_i = lines.index(non_empty[0]) if non_empty else 0
        desc_lines = [_clean(l) for l in lines[title_i + 1:ing_i] if l.strip()]
        end = met_i if met_i is not None else len(lines)
        block = lines[ing_i + 1:end]
        if met_i is None:  # no method header: ingredients end at first blank line
            stop = next((i for i, l in enumerate(block) if not l.strip() and i > 0), len(block))
            method_lines = block[stop:]
            block = block[:stop]
        ingredients = [_clean(l) for l in block if _clean(l)]
        if met_i is not None:
            method_lines = lines[met_i + 1:]
    else:
        desc_lines = [_clean(l) for l in non_empty[1:3]]
        method_lines = non_empty[3:]

    method = "\n".join(_clean(l) for l in method_lines if _clean(l))
    everything = text
    return Recipe(
        name=name,
        description=" ".join(d for d in desc_lines if d)[:300],
        cuisine=_guess(everything, _CUISINE_WORDS),
        protein=_guess("\n".join(ingredients) or everything, _PROTEIN_WORDS),
        carb=_guess("\n".join(ingredients) or everything, _CARB_WORDS),
        ingredients=ingredients,
        method=method,
        source=source,
    )


# ------------------------------------------------------------------ Instagram
def fetch_instagram_caption(url: str, timeout: int = 10) -> str:
    """Best effort: public posts expose the caption in og:description.
    Instagram often blocks or requires login, so callers should fall back to
    asking the user to paste the caption (Share > Copy link / copy text)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; facebookexternalhit/1.1)",
        "Accept-Language": "en-GB,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
        html = resp.read().decode("utf-8", "ignore")
    m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"', html) or \
        re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="og:description"', html)
    if not m:
        raise ValueError("Couldn't read the caption - paste it in instead.")
    import html as htmllib
    caption = htmllib.unescape(m.group(1))
    # og:description looks like: '123 likes, 4 comments - user on date: "caption..."'
    q = re.search(r':\s*"(.*)"\s*\.?$', caption, re.S)
    return (q.group(1) if q else caption).replace("\\n", "\n")


# ------------------------------------------------------------------ Claude API
_PROMPT = f"""Extract the recipe from this {{what}} and reply with ONLY a JSON object, no other text:
{{{{"name": str, "description": "one or two sentences describing the dish",
"cuisine": "country/style e.g. Italian", "protein": one of {PROTEINS},
"carb": one of {CARBS}, "ingredients": [str, ...], "method": "numbered steps separated by newlines"}}}}
If something is missing, make a sensible guess; use "" if impossible."""

_MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}


def ai_extract(api_key: str, text: str | None = None, image_path: str | None = None,
               model: str = DEFAULT_MODEL, source: str = "", timeout: int = 60) -> Recipe:
    if not api_key:
        raise ValueError("Add an API key in Settings to use AI import.")
    content = []
    if image_path:
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in _MEDIA:
            raise ValueError("Use a JPG, PNG, WEBP or GIF image.")
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        content.append({"type": "image", "source": {"type": "base64", "media_type": _MEDIA[ext], "data": data}})
    what = "photo" if image_path else "text"
    prompt = _PROMPT.format(what=what)
    if text:
        prompt += "\n\n---\n" + text
    content.append({"type": "text", "text": prompt})

    body = json.dumps({"model": model or DEFAULT_MODEL, "max_tokens": 2000,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        raise ValueError(f"API error {e.code}: {detail}") from None
    reply = "".join(b.get("text", "") for b in payload.get("content", []))
    return recipe_from_json(reply, source)


def recipe_from_json(reply: str, source: str = "") -> Recipe:
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        raise ValueError("The AI reply didn't contain a recipe.")
    d = json.loads(m.group(0))
    ings = d.get("ingredients") or []
    if isinstance(ings, str):
        ings = [i for i in ings.split("\n") if i.strip()]
    protein = d.get("protein", "")
    carb = d.get("carb", "")
    return Recipe(
        name=str(d.get("name", "")).strip() or "Imported recipe",
        description=str(d.get("description", "")),
        cuisine=str(d.get("cuisine", "")).strip().title(),
        protein=protein if protein in PROTEINS else "",
        carb=carb if carb in CARBS else "",
        ingredients=[str(i).strip() for i in ings if str(i).strip()],
        method=str(d.get("method", "")),
        source=source,
    )
