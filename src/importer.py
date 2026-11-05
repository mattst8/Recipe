"""Turn pasted recipe text (e.g. an Instagram caption) into a Recipe.

Fully offline: rule-based parsing only. This app makes no network connections.
"""
import re

from db import Recipe

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
