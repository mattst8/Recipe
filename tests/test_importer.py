"""Checks for the offline importer's guesses. Run with:  python tests/test_importer.py  (or pytest)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from importer import guess_carb, guess_protein, parse_text  # noqa: E402

CASES = [  # ingredients, expected protein, expected base
    ("200g rice noodles\n200g prawns\n2 eggs\nbeansprouts\n2 tbsp fish sauce", "Seafood", "Noodles"),
    ("200g spaghetti\n150g pancetta\n3 eggs\n50g parmesan", "Pork", "Pasta"),
    ("1 aubergine (eggplant)\na bunch of coriander\ntoasted sesame seeds\n1 tin chickpeas\nrice", "Vegan", "Rice"),
    ("2 chicken breasts\n100g panko\n1 egg\n500ml chicken stock\nrice", "Chicken", "Rice"),
    ("1 tin chickpeas\n400ml coconut milk\nspinach\nnaan", "Vegan", "Bread"),
    ("paneer\nbutter\ncream\nbasmati rice", "Vegetarian", "Rice"),
    ("salmon fillets\n2 tbsp rice vinegar\nsoy sauce\negg noodles", "Fish", "Noodles"),
    ("500g beef mince\nminced garlic\npotatoes\nbreadcrumbs", "Beef", "Potato"),
    ("1 tin butter beans\n2 sweet potatoes\ncumin", "Vegan", "Potato"),
    ("tofu\npeanut butter\nrice paper\nlettuce", "Vegan", ""),
]


def test_guesses():
    for text, protein, carb in CASES:
        assert (guess_protein(text), guess_carb(text)) == (protein, carb), text


def test_parse_caption():
    r = parse_text("Garlic Prawn Linguine 🍤\nQuick dinner\n\nIngredients:\n• 250g linguine\n• 200g prawns\n"
                   "• 3 garlic cloves\n\nMethod\n1. Boil pasta\n2. Fry prawns\n\n#pasta #dinner")
    assert r.name == "Garlic Prawn Linguine 🍤"
    assert r.ingredients == ["250g linguine", "200g prawns", "3 garlic cloves"]
    assert r.method == "Boil pasta\nFry prawns"
    assert (r.protein, r.carb, r.cuisine) == ("Seafood", "Pasta", "Italian")


if __name__ == "__main__":
    test_guesses()
    test_parse_caption()
    print("All importer checks passed")
