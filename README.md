# Recipe Randomiser

A pastel, minimal recipe book and random meal picker for Windows, written in Python with
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

**Fully offline.** The app never connects to the internet: no online import, no accounts, no API keys
and no analytics. Your recipes stay in a file on your own PC.

## Features
- **Recipe book**: add, edit and delete recipes. Each one has a name, description, country/cuisine,
  protein (Beef, Chicken, Pork, Lamb, Fish, Seafood, Vegetarian, Vegan), base (Rice, Pasta, Potato,
  Noodles, Bread, None), ingredients, method and source.
- **Browse**: search by name or ingredient and filter by country (30 built in, or type your own),
  protein and base.
- **Random meals**: pick 1–10 meals with no repeats. Use one set of filters for every meal, or switch
  it off to set filters per meal (for example Meal 1 = Chicken + Rice, Meal 2 = any Pasta).
  Reroll any single meal with ↻.
- **Import**: paste any recipe or caption (for example copied from Instagram). It's split into
  ingredients and method, and the protein, base and cuisine are guessed. For a photo or screenshot,
  copy the text with Google Lens first. Every import opens a review screen before saving.
- **Backup & restore**: export your recipes to a file or the clipboard, and restore them later or on
  another PC. Recipes that already exist (same name) are skipped.

Five sample recipes are added on first launch so the randomiser works straight away. Delete them whenever you like.

## Run it on Windows
1. Install **Python 3.12 or 3.13** from https://www.python.org/downloads/ and tick
   **"Add python.exe to PATH"** in the installer.
2. Unzip this folder and double-click **`run.bat`**.

The first run takes a minute while it installs CustomTkinter into a private `.venv` folder. After that,
`run.bat` opens the app straight away.

Prefer a terminal? In this folder run:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\main.py
```
If the app ever closes without a message, run `.venv\Scripts\python src\main.py` to see the error.

## Make a standalone app (.exe)
Double-click **`build_exe.bat`**. It installs PyInstaller and builds
`dist\Recipe Randomiser\Recipe Randomiser.exe`. Copy the whole `dist\Recipe Randomiser` folder
anywhere you like (or make a desktop shortcut to the .exe). The finished app doesn't need Python.

## Where your recipes are kept
In `%APPDATA%\Recipe Randomiser\recipes.db` (for example
`C:\Users\<you>\AppData\Roaming\Recipe Randomiser\recipes.db`). The Backup screen shows the exact path.
Every change is saved straight away, and `run.bat` and the .exe use the same file, so your recipes are
kept when you close the app, update it or switch between the two.

## Keeping it offline
The app contains no networking code. For a hard guarantee, add an outbound block rule for the app in
Windows Defender Firewall. Only installing Python packages (`run.bat`'s first run and `build_exe.bat`)
uses the internet.

## Project layout
```
Recipe/
├── run.bat             # set up (first time) and start the app
├── build_exe.bat       # build a standalone Windows app
├── requirements.txt
├── src/
│   ├── main.py         # all screens
│   ├── theme.py        # pastel colours and shared widgets
│   ├── db.py           # SQLite storage
│   ├── importer.py     # offline text parser
│   └── assets/icon.png
└── tests/
    └── test_importer.py  # run: python tests/test_importer.py
```
