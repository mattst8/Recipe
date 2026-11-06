"""SQLite storage for recipes and settings."""
import os
import sqlite3
import sys
from dataclasses import dataclass, field

PROTEINS = ["Beef", "Chicken", "Pork", "Lamb", "Fish", "Seafood", "Vegetarian", "Vegan"]
CARBS = ["Rice", "Pasta", "Potato", "Noodles", "Bread", "None"]
CUISINES = [
    "American", "Argentinian", "Brazilian", "British", "Caribbean", "Chinese", "Ethiopian", "Filipino",
    "French", "German", "Greek", "Hungarian", "Indian", "Indonesian", "Irish", "Italian", "Japanese",
    "Korean", "Malaysian", "Mexican", "Middle Eastern", "Moroccan", "Persian", "Peruvian", "Polish",
    "Portuguese", "Spanish", "Thai", "Turkish", "Vietnamese",
]


@dataclass
class Recipe:
    id: int | None = None
    name: str = ""
    description: str = ""
    cuisine: str = ""
    protein: str = ""
    carb: str = ""
    ingredients: list[str] = field(default_factory=list)
    method: str = ""
    source: str = ""


def default_db_path() -> str:
    """The user's own app-data folder, e.g. C:\\Users\\<you>\\AppData\\Roaming\\Recipe Randomiser on Windows.
    Set RECIPE_RANDOMISER_DATA to use a different folder."""
    if os.getenv("RECIPE_RANDOMISER_DATA"):
        folder = os.environ["RECIPE_RANDOMISER_DATA"]
    else:
        if sys.platform == "win32":
            base = os.getenv("APPDATA") or os.path.expanduser("~")
        elif sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        else:
            base = os.getenv("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        folder = os.path.join(base, "Recipe Randomiser")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "recipes.db")


class RecipeDB:
    def __init__(self, path: str | None = None):
        self.path = path or default_db_path()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create()

    def _create(self):
        c = self.conn
        c.execute(
            """CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                cuisine TEXT DEFAULT '',
                protein TEXT DEFAULT '',
                carb TEXT DEFAULT '',
                ingredients TEXT DEFAULT '',
                method TEXT DEFAULT '',
                source TEXT DEFAULT ''
            )"""
        )
        c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("DELETE FROM settings WHERE key IN ('api_key', 'model')")  # from the old online AI import
        c.commit()
        if self.count() == 0 and self.get_setting("seeded") != "1":
            self._seed()
            self.set_setting("seeded", "1")

    # ---------- recipes ----------
    @staticmethod
    def _row(r) -> Recipe:
        return Recipe(
            id=r["id"], name=r["name"], description=r["description"], cuisine=r["cuisine"],
            protein=r["protein"], carb=r["carb"],
            ingredients=[i for i in r["ingredients"].split("\n") if i.strip()],
            method=r["method"], source=r["source"],
        )

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]

    def add(self, r: Recipe) -> int:
        cur = self.conn.execute(
            "INSERT INTO recipes (name, description, cuisine, protein, carb, ingredients, method, source)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (r.name.strip(), r.description, r.cuisine.strip().title(), r.protein, r.carb,
             "\n".join(r.ingredients), r.method, r.source),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, r: Recipe):
        self.conn.execute(
            "UPDATE recipes SET name=?, description=?, cuisine=?, protein=?, carb=?, ingredients=?,"
            " method=?, source=? WHERE id=?",
            (r.name.strip(), r.description, r.cuisine.strip().title(), r.protein, r.carb,
             "\n".join(r.ingredients), r.method, r.source, r.id),
        )
        self.conn.commit()

    def delete(self, recipe_id: int):
        self.conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))
        self.conn.commit()

    def get(self, recipe_id: int) -> Recipe | None:
        r = self.conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
        return self._row(r) if r else None

    def search(self, text: str = "", cuisine: str = "", protein: str = "", carb: str = "") -> list[Recipe]:
        sql, args = "SELECT * FROM recipes WHERE 1=1", []
        if text:
            sql += " AND (name LIKE ? OR description LIKE ? OR ingredients LIKE ?)"
            args += [f"%{text}%"] * 3
        for col, val in (("cuisine", cuisine), ("protein", protein), ("carb", carb)):
            if val:
                sql += f" AND {col} = ?"
                args.append(val)
        sql += " ORDER BY name COLLATE NOCASE"
        return [self._row(r) for r in self.conn.execute(sql, args).fetchall()]

    def distinct(self, column: str) -> list[str]:
        assert column in ("cuisine", "protein", "carb")
        rows = self.conn.execute(
            f"SELECT DISTINCT {column} FROM recipes WHERE {column} != '' ORDER BY {column}"
        ).fetchall()
        return [r[0] for r in rows]

    # ---------- settings ----------
    def get_setting(self, key: str, default: str = "") -> str:
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r[0] if r else default

    def set_setting(self, key: str, value: str):
        self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        self.conn.commit()

    # ---------- sample data ----------
    def _seed(self):
        samples = [
            Recipe(name="Chicken Katsu Curry", cuisine="Japanese", protein="Chicken", carb="Rice",
                   description="Crispy panko chicken with a mild, sweet curry sauce over rice.",
                   ingredients=["2 chicken breasts", "100g panko", "1 egg", "Flour", "1 onion", "2 carrots",
                                "2 tbsp curry powder", "500ml chicken stock", "1 tbsp honey", "Rice"],
                   method="Cook onion and carrot, add curry powder, stock and honey, simmer and blend.\n"
                          "Flour, egg and panko the chicken, then fry until golden.\nSlice and serve over rice with sauce."),
            Recipe(name="Spaghetti Bolognese", cuisine="Italian", protein="Beef", carb="Pasta",
                   description="Slow-simmered beef and tomato ragu with spaghetti.",
                   ingredients=["500g beef mince", "1 onion", "2 garlic cloves", "1 carrot", "1 celery stick",
                                "400g chopped tomatoes", "2 tbsp tomato purée", "300g spaghetti"],
                   method="Soften the veg, brown the mince.\nAdd tomatoes and purée, simmer 45 min.\nServe over spaghetti."),
            Recipe(name="Shepherd's Pie", cuisine="British", protein="Lamb", carb="Potato",
                   description="Lamb mince in rich gravy topped with buttery mash.",
                   ingredients=["500g lamb mince", "1 onion", "2 carrots", "1 tbsp Worcestershire sauce",
                                "300ml stock", "800g potatoes", "Butter", "Milk"],
                   method="Brown lamb with veg, add stock and Worcestershire, simmer.\n"
                          "Top with mash and bake at 200°C for 25 min."),
            Recipe(name="Chana Masala", cuisine="Indian", protein="Vegan", carb="Rice",
                   description="Chickpeas in a spiced tomato and onion gravy.",
                   ingredients=["2 tins chickpeas", "1 onion", "3 garlic cloves", "Ginger", "1 tin tomatoes",
                                "1 tsp cumin", "1 tsp garam masala", "Coriander", "Rice"],
                   method="Fry onion, garlic, ginger and spices.\nAdd tomatoes and chickpeas, simmer 20 min.\nServe with rice."),
            Recipe(name="Pad Thai", cuisine="Thai", protein="Seafood", carb="Noodles",
                   description="Stir-fried rice noodles with prawns, egg, peanuts and lime.",
                   ingredients=["200g rice noodles", "200g prawns", "2 eggs", "Beansprouts", "Spring onions",
                                "3 tbsp tamarind paste", "2 tbsp fish sauce", "1 tbsp sugar", "Peanuts", "Lime"],
                   method="Soak noodles.\nStir-fry prawns, push aside and scramble eggs.\n"
                          "Add noodles and sauce, toss with beansprouts. Top with peanuts and lime."),
        ]
        for s in samples:
            self.add(s)
