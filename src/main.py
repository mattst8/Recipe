"""Recipe Randomiser - a Flet app for Windows and Android.

Fully offline: the app makes no network connections.

Run on a computer:   flet run            (or: python main.py)
Run on your phone:   flet run --android  (scan the QR code with the Flet app)
Build installers:    flet build apk   /   flet build windows
"""
import json
import random

import flet as ft

import importer
from db import CARBS, CUISINES, PROTEINS, Recipe, RecipeDB
from theme import (ACCENT, BG, BUTTER, DANGER, INK, LAVENDER, MINT, MUTED, PEACH, ROSE, SKY, SURFACE,
                   app_theme, card, dd_value, dropdown, label, pill, primary_button, text_field, title)

MAX_MEALS = 10
OTHER = "Other…"


class RecipeApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = RecipeDB()
        self.draft: Recipe | None = None          # recipe waiting for review after an import
        self.import_text = ""
        self.browse = {"text": "", "cuisine": "", "protein": "", "carb": ""}
        self.rnd = {"n": 3, "same": True, "filters": [self._blank_filter() for _ in range(MAX_MEALS)], "results": []}
        self._picker_handler = None

        page.title = "Recipe Randomiser"
        page.theme = app_theme()
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = BG
        page.window.width, page.window.height = 440, 880       # phone-shaped window on Windows
        page.window.min_width, page.window.min_height = 360, 600

        self.picker = ft.FilePicker(on_result=self._on_pick)
        page.overlay.append(self.picker)
        page.on_route_change = self.route_change
        page.on_view_pop = self.view_pop
        page.go(page.route or "/")

    # ================================================================ plumbing
    @staticmethod
    def _blank_filter():
        return {"cuisine": "", "protein": "", "carb": ""}

    def toast(self, msg: str, color: str = MINT):
        self.page.open(ft.SnackBar(ft.Text(msg, color=INK), bgcolor=color, behavior=ft.SnackBarBehavior.FLOATING))

    def _on_pick(self, e: ft.FilePickerResultEvent):
        if self._picker_handler:
            self._picker_handler(e)

    def view(self, route: str, heading: str, controls: list, actions=None, fab=None, scroll=True) -> ft.View:
        return ft.View(
            route=route,
            controls=controls,
            appbar=ft.AppBar(title=ft.Text(heading, color=INK, weight=ft.FontWeight.W_600),
                             bgcolor=BG, color=INK, elevation=0, actions=actions or []),
            bgcolor=BG,
            padding=ft.padding.symmetric(horizontal=18, vertical=8),
            scroll=ft.ScrollMode.AUTO if scroll else None,
            floating_action_button=fab,
            spacing=14,
        )

    def route_change(self, e=None):
        r = self.page.route
        parts = [p for p in r.split("/") if p]
        stack = [self.home_view()]
        try:
            if parts[:1] == ["browse"]:
                stack.append(self.browse_view())
            elif parts[:1] == ["recipe"]:
                stack += [self.browse_view(), self.detail_view(int(parts[1]))]
            elif parts[:1] == ["edit"]:
                stack.append(self.browse_view())
                if parts[1] != "new":
                    stack.append(self.detail_view(int(parts[1])))
                stack.append(self.edit_view(None if parts[1] == "new" else int(parts[1])))
            elif parts[:1] == ["random"]:
                stack.append(self.random_view())
            elif parts[:1] == ["import"]:
                stack.append(self.import_view())
                if parts[1:2] == ["review"]:
                    stack.append(self.edit_view(None, route=r))
            elif parts[:1] == ["settings"]:
                stack.append(self.settings_view())
        except (ValueError, IndexError, LookupError):
            stack = [self.home_view()]
        self.page.views.clear()
        self.page.views.extend([v for v in stack if v is not None])
        self.page.update()

    def view_pop(self, e):
        if len(self.page.views) > 1:
            self.page.views.pop()
            self.page.go(self.page.views[-1].route)

    # ================================================================ home
    def home_view(self) -> ft.View:
        def tile(text, sub, icon, color, route):
            return ft.Container(
                card(ft.Column([ft.Icon(icon, color=INK, size=30), ft.Text(text, size=17, weight=ft.FontWeight.W_600, color=INK),
                                ft.Text(sub, size=12, color=MUTED)], spacing=6),
                     color=color, on_click=lambda _: self.page.go(route), padding=18),
                col={"xs": 6, "md": 4})

        n = self.db.count()
        return ft.View(
            route="/", bgcolor=BG, padding=ft.padding.only(left=18, right=18, top=40, bottom=18),
            scroll=ft.ScrollMode.AUTO, spacing=18,
            controls=[
                title("What's for dinner?", 30),
                ft.Text(f"{n} recipe{'s' if n != 1 else ''} in your book", color=MUTED),
                card(ft.Row([ft.Icon(ft.Icons.CASINO_OUTLINED, color=INK, size=36),
                             ft.Column([ft.Text("Surprise me", size=20, weight=ft.FontWeight.W_600, color=INK),
                                        ft.Text("Pick meals at random", color=MUTED, size=13)], spacing=2, expand=True),
                             ft.Icon(ft.Icons.CHEVRON_RIGHT, color=INK)]),
                     color=PEACH, on_click=lambda _: self.page.go("/random"), padding=22),
                ft.ResponsiveRow([
                    tile("All recipes", "Browse & filter", ft.Icons.MENU_BOOK_OUTLINED, MINT, "/browse"),
                    tile("Add recipe", "Type one in", ft.Icons.ADD_CIRCLE_OUTLINE, LAVENDER, "/edit/new"),
                    tile("Import", "Paste a caption", ft.Icons.DOWNLOAD_OUTLINED, SKY, "/import"),
                    tile("Backup", "Move recipes between devices", ft.Icons.TUNE, BUTTER, "/settings"),
                ], spacing=14, run_spacing=14),
            ],
        )

    # ================================================================ browse
    def _options(self, column: str, base: list[str]) -> list[str]:
        extra = [v for v in self.db.distinct(column) if v not in base]
        return sorted(base + extra) if column == "cuisine" else base + extra

    def recipe_tile(self, r: Recipe, trailing: ft.Control | None = None) -> ft.Container:
        pills = [pill(t, c) for t, c in ((r.cuisine, PEACH), (r.protein, ROSE), (r.carb, BUTTER)) if t]
        body = ft.Column([
            ft.Text(r.name, size=16, weight=ft.FontWeight.W_600, color=INK),
            *([ft.Text(r.description, size=13, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)]
              if r.description else []),
            ft.Row(pills, spacing=6, wrap=True),
        ], spacing=6, expand=True)
        return card(ft.Row([body] + ([trailing] if trailing else []), vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    on_click=lambda _, i=r.id: self.page.go(f"/recipe/{i}"))

    def browse_view(self) -> ft.View:
        results = ft.ListView(spacing=10, expand=True, padding=ft.padding.only(bottom=80))
        count = label("")

        def refresh(_=None):
            self.browse.update(text=search.value or "", cuisine=dd_value(cuisine), protein=dd_value(protein), carb=dd_value(carb))
            found = self.db.search(**self.browse)
            results.controls = [self.recipe_tile(r) for r in found] or \
                [ft.Container(ft.Text("No recipes match. Try clearing a filter.", color=MUTED), padding=20)]
            count.value = f"{len(found)} recipe{'s' if len(found) != 1 else ''}"
            self.page.update()

        search = text_field("Search name or ingredient", self.browse["text"], prefix_icon=ft.Icons.SEARCH, on_change=refresh)
        cuisine = dropdown("Country", self._options("cuisine", CUISINES), self.browse["cuisine"], True, refresh)
        protein = dropdown("Protein", self._options("protein", PROTEINS), self.browse["protein"], True, refresh)
        carb = dropdown("Base", self._options("carb", CARBS), self.browse["carb"], True, refresh)

        found = self.db.search(**self.browse)
        results.controls = [self.recipe_tile(r) for r in found] or \
            [ft.Container(ft.Text("No recipes yet - add or import one!", color=MUTED), padding=20)]
        count.value = f"{len(found)} recipe{'s' if len(found) != 1 else ''}"

        return self.view("/browse", "All recipes",
                         [search, ft.Row([cuisine, protein, carb], spacing=8), count, results],
                         fab=ft.FloatingActionButton(icon=ft.Icons.ADD, bgcolor=LAVENDER, foreground_color=INK,
                                                     on_click=lambda _: self.page.go("/edit/new")),
                         scroll=False)

    # ================================================================ detail
    def detail_view(self, recipe_id: int) -> ft.View:
        r = self.db.get(recipe_id)
        if not r:
            raise LookupError

        def confirm_delete(_):
            def do_delete(_):
                self.page.close(dlg)
                self.db.delete(r.id)
                self.toast(f"Deleted {r.name}", DANGER)
                self.page.go("/browse")
            dlg = ft.AlertDialog(
                title=ft.Text("Delete recipe?"), content=ft.Text(f"“{r.name}” will be removed for good."),
                actions=[ft.TextButton("Cancel", on_click=lambda _: self.page.close(dlg)),
                         ft.TextButton("Delete", on_click=do_delete, style=ft.ButtonStyle(color=ft.Colors.RED_300))])
            self.page.open(dlg)

        pills = [pill(t, c) for t, c in ((r.cuisine, PEACH), (r.protein, ROSE), (r.carb, BUTTER)) if t]
        ingredients = ft.Column([
            ft.Row([ft.Container(width=7, height=7, bgcolor=ACCENT, border_radius=4),
                    ft.Text(i, color=INK, expand=True, selectable=True)], spacing=10) for i in r.ingredients
        ], spacing=6)
        steps = [s for s in r.method.split("\n") if s.strip()]
        method = ft.Column([
            ft.Row([ft.Container(ft.Text(str(n), size=12, color=INK), bgcolor=LAVENDER, border_radius=12,
                                 width=24, height=24, alignment=ft.alignment.center),
                    ft.Text(s, color=INK, expand=True, selectable=True)], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.START)
            for n, s in enumerate(steps, 1)
        ], spacing=10)

        controls = [title(r.name), ft.Row(pills, spacing=6, wrap=True)]
        if r.description:
            controls.append(ft.Text(r.description, color=MUTED, size=15))
        if r.ingredients:
            controls.append(card(ft.Column([label("INGREDIENTS"), ingredients], spacing=10), color=SURFACE))
        if steps:
            controls.append(card(ft.Column([label("METHOD"), method], spacing=10), color=SURFACE))
        if r.source:
            controls.append(ft.Text(f"Source: {r.source}", size=12, color=MUTED, selectable=True))

        return self.view(f"/recipe/{r.id}", "", controls, actions=[
            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color=INK, tooltip="Edit",
                          on_click=lambda _: self.page.go(f"/edit/{r.id}")),
            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=INK, tooltip="Delete", on_click=confirm_delete),
        ])

    # ================================================================ add / edit
    def edit_view(self, recipe_id: int | None, route: str | None = None) -> ft.View:
        if recipe_id is not None:
            r = self.db.get(recipe_id)
            if not r:
                raise LookupError
        elif route and self.draft:
            r = self.draft
        else:
            r = Recipe()

        name = text_field("Name *", r.name)
        desc = text_field("Description - what is this meal?", r.description, multiline=True)
        cuisine_opts = self._options("cuisine", CUISINES) + [OTHER]
        cuisine = dropdown("Country / cuisine", cuisine_opts, r.cuisine)
        cuisine_other = text_field("Type the country or cuisine", hint_text="e.g. Sri Lankan", visible=False)

        def cuisine_changed(_):
            cuisine_other.visible = cuisine.value == OTHER
            self.page.update()
        cuisine.on_change = cuisine_changed
        protein = dropdown("Protein", self._options("protein", PROTEINS), r.protein)
        carb = dropdown("Base", self._options("carb", CARBS), r.carb)
        ings = text_field("Ingredients - one per line", "\n".join(r.ingredients), multiline=True)
        method = text_field("Method - one step per line", r.method, multiline=True)
        source = text_field("Source (link, book…)", r.source)

        def save(_):
            if not (name.value or "").strip():
                name.error_text = "Give it a name"
                self.page.update()
                return
            country = (cuisine_other.value or "") if cuisine.value == OTHER else (cuisine.value or "")
            rec = Recipe(id=r.id, name=name.value, description=desc.value or "", cuisine=country,
                         protein=protein.value or "", carb=carb.value or "",
                         ingredients=[l.strip() for l in (ings.value or "").split("\n") if l.strip()],
                         method=(method.value or "").strip(), source=source.value or "")
            if rec.id:
                self.db.update(rec)
            else:
                rec.id = self.db.add(rec)
            self.draft = None
            self.toast(f"Saved {rec.name}")
            self.page.go(f"/recipe/{rec.id}")

        heading = "Edit recipe" if recipe_id else ("Check import" if route else "New recipe")
        hint = [card(ft.Text("Have a quick look over what was imported, then save.", color=INK), color=SKY)] if route else []
        return self.view(route or f"/edit/{recipe_id or 'new'}", heading, hint + [
            name, desc, cuisine, cuisine_other, ft.Row([protein, carb], spacing=8), ings, method, source,
            ft.Container(primary_button("Save recipe", ft.Icons.CHECK, save), padding=ft.padding.only(top=6, bottom=30)),
        ])

    # ================================================================ randomiser
    def random_view(self) -> ft.View:
        body = ft.Column(spacing=14)
        self._render_random(body)
        return self.view("/random", "Random meals", [body])

    def _pick(self, f: dict, exclude: set[int]) -> int | None:
        candidates = [r.id for r in self.db.search(**f) if r.id not in exclude]
        return random.choice(candidates) if candidates else None

    def _render_random(self, body: ft.Column):
        s = self.rnd
        rerender = lambda: (self._render_random(body), self.page.update())
        cuisines = self._options("cuisine", CUISINES)
        proteins = self._options("protein", PROTEINS)
        carbs = self._options("carb", CARBS)

        def set_n(delta):
            s["n"] = max(1, min(MAX_MEALS, s["n"] + delta))
            s["results"] = s["results"][: s["n"]]
            rerender()

        def toggle_same(e):
            s["same"] = e.control.value
            rerender()

        def filter_row(i: int):
            f = s["filters"][i]

            def changed(e, key):
                val = dd_value(e.control)
                if s["same"]:
                    for ff in s["filters"]:
                        ff[key] = val
                else:
                    f[key] = val
            return ft.Row([
                dropdown("Country", cuisines, f["cuisine"], True, lambda e: changed(e, "cuisine")),
                dropdown("Protein", proteins, f["protein"], True, lambda e: changed(e, "protein")),
                dropdown("Base", carbs, f["carb"], True, lambda e: changed(e, "carb")),
            ], spacing=6)

        def shuffle(_):
            chosen: list[int | None] = []
            for i in range(s["n"]):
                chosen.append(self._pick(s["filters"][i], {c for c in chosen if c}))
            s["results"] = chosen
            if not any(chosen):
                self.toast("Nothing matches those filters", PEACH)
            rerender()

        def reroll(i):
            others = {c for j, c in enumerate(s["results"]) if c and j != i}
            new = self._pick(s["filters"][i], others | ({s["results"][i]} if s["results"][i] else set()))
            if new is None:
                self.toast("No other recipe matches - that's the only one!", PEACH)
                return
            s["results"][i] = new
            rerender()

        counter = card(ft.Row([
            ft.Text("How many meals?", color=INK, size=16, expand=True),
            ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=INK, on_click=lambda _: set_n(-1)),
            ft.Text(str(s["n"]), size=22, weight=ft.FontWeight.W_600, color=INK, width=30, text_align=ft.TextAlign.CENTER),
            ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color=INK, on_click=lambda _: set_n(1)),
        ]), color=PEACH, padding=12)

        same = ft.Switch(label="Same filters for every meal", value=s["same"], on_change=toggle_same,
                         active_color=ACCENT)

        if s["same"]:
            filters = [filter_row(0)]
        else:
            filters = [ft.Column([label(f"MEAL {i + 1}"), filter_row(i)], spacing=6) for i in range(s["n"])]

        results = []
        for i, rid in enumerate(s["results"]):
            r = self.db.get(rid) if rid else None
            reroll_btn = ft.IconButton(ft.Icons.REFRESH, icon_color=INK, tooltip="Pick another",
                                       on_click=lambda _, i=i: reroll(i))
            if r:
                results.append(self.recipe_tile(r, reroll_btn))
            else:
                results.append(card(ft.Row([ft.Text(f"Meal {i + 1}: no match for these filters", color=MUTED, expand=True),
                                            reroll_btn]), color=SURFACE))

        body.controls = [
            counter, same, card(ft.Column(filters, spacing=12), color=SURFACE, padding=12),
            ft.Row([primary_button("Shuffle!", ft.Icons.CASINO_OUTLINED, shuffle, PEACH)], alignment=ft.MainAxisAlignment.CENTER),
            *([label("YOUR MEALS")] if results else []), *results,
            ft.Container(height=30),
        ]

    # ================================================================ import
    def import_view(self) -> ft.View:
        text = text_field("Recipe text / caption", self.import_text, multiline=True,
                          on_change=lambda e: setattr(self, "import_text", e.control.value or ""))
        source = text_field("Where it's from (optional)", hint_text="e.g. Instagram link or account name")

        def paste(_):
            text.value = self.import_text = self.page.get_clipboard() or ""
            self.page.update()

        def convert(_):
            txt = (text.value or "").strip()
            if not txt:
                self.toast("Paste some recipe text first", PEACH)
                return
            self.draft = importer.parse_text(txt, source=(source.value or "").strip())
            self.import_text = ""
            self.page.go("/import/review")

        return self.view("/import", "Import a recipe", [
            card(ft.Column([
                label("PASTE A RECIPE"),
                ft.Text("Copy a caption or recipe (on Instagram: ⋯ → Copy, or long-press the caption), "
                        "then paste it here. For a photo or screenshot, use Google Lens → Copy text first.",
                        size=12, color=MUTED),
                ft.Row([ft.TextButton("Paste from clipboard", icon=ft.Icons.CONTENT_PASTE, on_click=paste)]),
                text, source,
            ], spacing=10), color=MINT),
            ft.Row([primary_button("Convert to recipe", ft.Icons.AUTO_AWESOME, convert, PEACH)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=30),
        ])

    # ================================================================ settings
    def settings_view(self) -> ft.View:
        def export_json():
            recs = self.db.search()
            return json.dumps([{k: v for k, v in r.__dict__.items() if k != "id"} for r in recs], indent=2, ensure_ascii=False)

        def export(_):
            def handler(e: ft.FilePickerResultEvent):
                if e.path:
                    path = e.path if e.path.endswith(".json") else e.path + ".json"
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(export_json())
                    self.toast("Backup saved")
            self._picker_handler = handler
            if self.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
                self.page.set_clipboard(export_json())
                self.toast("Backup copied to clipboard - paste it into a note or email")
            else:
                self.picker.save_file(dialog_title="Save recipe backup", file_name="recipes_backup.json",
                                      allowed_extensions=["json"])

        def restore_from(raw: str):
            data = json.loads(raw)
            existing = {r.name.lower() for r in self.db.search()}
            added = 0
            for d in data:
                if str(d.get("name", "")).lower() in existing:
                    continue
                ings = d.get("ingredients") or []
                self.db.add(Recipe(name=str(d.get("name", "Untitled")), description=d.get("description", ""),
                                   cuisine=d.get("cuisine", ""), protein=d.get("protein", ""), carb=d.get("carb", ""),
                                   ingredients=ings if isinstance(ings, list) else str(ings).split("\n"),
                                   method=d.get("method", ""), source=d.get("source", "")))
                added += 1
            self.toast(f"Added {added} recipe{'s' if added != 1 else ''} (duplicates skipped)")

        def restore_file(_):
            def handler(e: ft.FilePickerResultEvent):
                if e.files:
                    try:
                        with open(e.files[0].path, encoding="utf-8") as f:
                            restore_from(f.read())
                    except Exception as ex:  # noqa: BLE001
                        self.toast(f"Couldn't read backup: {ex}", DANGER)
            self._picker_handler = handler
            self.picker.pick_files(dialog_title="Choose a backup", allowed_extensions=["json"],
                                   file_type=ft.FilePickerFileType.CUSTOM)

        def restore_clip(_):
            try:
                restore_from(self.page.get_clipboard() or "")
            except Exception:  # noqa: BLE001
                self.toast("Clipboard doesn't contain a recipe backup", DANGER)

        return self.view("/settings", "Backup & restore", [
            card(ft.Column([
                label("BACKUP & SYNC"),
                ft.Text("Move recipes between your PC and phone.", size=13, color=INK),
                ft.Row([ft.OutlinedButton("Export", icon=ft.Icons.UPLOAD_OUTLINED, on_click=export),
                        ft.OutlinedButton("Restore file", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=restore_file),
                        ft.OutlinedButton("Restore from clipboard", icon=ft.Icons.CONTENT_PASTE, on_click=restore_clip)],
                       wrap=True),
            ], spacing=10), color=MINT),
            ft.Text(f"Database: {self.db.path}", size=11, color=MUTED, selectable=True),
        ])


def main(page: ft.Page):
    RecipeApp(page)


if __name__ == "__main__":
    ft.app(main)
