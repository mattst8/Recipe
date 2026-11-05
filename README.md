# Recipe Randomiser 🍽️

A pastel, minimal recipe book and random meal picker, built with Python + Flet.
The same code runs on **Windows** and **Android**.

**Fully offline.** The app never connects to the internet. There is no online import, no API keys,
no accounts and no analytics. The Android build has no internet permission, so the phone itself blocks network access.

## Features
- **Recipe book**: add, edit, delete. Each recipe has a name, description, country/cuisine,
  protein (Beef, Chicken, Pork, Lamb, Fish, Seafood, Vegetarian, Vegan), base (Rice, Pasta,
  Potato, Noodles, Bread, None), ingredients, method and source.
- **Browse**: search by name/ingredient and filter by country, protein and base.
- **Random meals**: pick 1–10 meals with no repeats. Use one set of filters for every meal,
  or switch it off to set filters per meal (e.g. Meal 1 = Chicken + Rice, Meal 2 = any Pasta).
  Reroll any single meal.
- **Import**: paste any recipe or caption (e.g. copied from Instagram). It's split into
  ingredients and method, and the protein, base and cuisine are guessed. For a photo or screenshot,
  use Google Lens on the phone ("Copy text") and paste the text. Every import opens a review screen before saving.
- **Backup & sync**: export recipes to JSON and restore them on another device.
  On Android, export copies to the clipboard; on Windows it saves a file.

Five sample recipes are added on first launch so the randomiser works straight away. Delete them whenever you like.

## Project layout
```
Recipe/
├── pyproject.toml      # dependencies + build settings
└── src/
    ├── main.py         # all screens
    ├── db.py           # SQLite storage
    ├── importer.py     # offline text parser
    ├── theme.py        # pastel colours and shared widgets
    └── assets/icon.png
```

## 1. Run it on Windows (development)
Install Python 3.12 from python.org, then in a terminal inside the project folder (the repo root):
```
python -m venv .venv
.venv\Scripts\activate
pip install "flet[all]==0.28.3" "fastapi<0.120"
flet run
```

## 2. Try it on your Android phone instantly (no build)
1. Install the **Flet** app from the Google Play Store.
2. Make sure the phone and PC are on the same Wi-Fi.
3. On the PC run `flet run --android` and scan the QR code with the Flet app.

The app runs live from your PC, which is good for testing. Recipes are stored on the PC while you do this.

## 3. Build a real Android APK (sideload)
On the Windows PC (with the venv active):
```
flet build apk
```
The first build downloads Flutter, the Android SDK and a JDK automatically. That can take 20–30 minutes and several GB of disk space; later builds are much faster.

The APK appears in `build\apk\`. To install it:
1. Copy `app-release.apk` to the phone (USB, Google Drive, email…).
2. Open it on the phone. Allow "Install unknown apps" for your file manager or browser when asked.
3. Done. Recipes are stored privately on the phone.

Tip: phones are usually arm64. To get a smaller APK, run `flet build apk --arch arm64-v8a`.

## 4. Build a Windows app
This must be built on Windows. First install **Visual Studio 2022 Community** with the
*"Desktop development with C++"* workload, and turn on **Developer Mode** in Windows Settings. Then run:
```
flet build windows
```
The app is in `build\windows\`. Copy the whole folder anywhere and run `Recipe Randomiser.exe`.

## Keeping it offline
- **Android**: `pyproject.toml` turns off the internet permission. After installing, check under
  Settings → Apps → Recipe Randomiser → Permissions: no network access should be listed.
- **Windows**: Windows doesn't have per-app permissions, but the app contains no networking code.
  Its two halves talk over `localhost` on your PC only. For a hard guarantee, add an outbound
  block rule in Windows Defender Firewall for `Recipe Randomiser.exe` (loopback is unaffected).
- Building the app (`flet build`) and `pip install` do download tools; only the finished app is offline.

## Moving recipes between PC and phone
- **PC → phone**: Backup → Export (saves a `.json` file). Put the file on the phone, then Backup → Restore file.
- **Phone → PC**: Backup → Export (copies the backup to the clipboard). Paste it into an email or note, copy it on the PC, then Backup → Restore from clipboard.

Recipes that already exist (same name) are skipped.

## Notes
- The app is pinned to Flet 0.28.3, the stable API it was written against.
  Flet 1.0 renamed several things (`ft.app` → `ft.run`, `ElevatedButton` → `Button`, and others),
  so don't upgrade without updating the code.
- `fastapi<0.120` is needed because newer FastAPI removed an option that Flet 0.28.3 uses
  for its web server (`flet run --web` and `flet run --android` crash without it).
