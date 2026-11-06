"""Recipe Randomiser - a pastel recipe book and random meal picker for Windows (CustomTkinter).

Fully offline: the app makes no network connections.

Run:  python src/main.py     (or double-click run.bat on Windows)
"""
import json
import os
import sys
import random
import tkinter
from tkinter import filedialog, messagebox

import customtkinter as ctk

import importer
import theme as t
from db import CARBS, CUISINES, PROTEINS, Recipe, RecipeDB

MAX_MEALS = 10
ANY = "Any"
BLANK = "—"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def asset(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))  # PyInstaller unpacks here
    return os.path.join(base, "assets", name)


class RecipeApp(ctk.CTk):
    def __init__(self, db: RecipeDB | None = None):
        ctk.set_appearance_mode("light")
        super().__init__(fg_color=t.BG)
        self.db = db or RecipeDB()
        self.title("Recipe Randomiser")
        self.geometry("460x860")
        self.minsize(380, 560)
        try:
            self._icon = tkinter.PhotoImage(file=asset("icon.png"))
            self.iconphoto(True, self._icon)
        except tkinter.TclError:
            pass

        self.route = "/"
        self.draft: Recipe | None = None          # recipe waiting for review after an import
        self.import_text = ""
        self.browse = {"text": "", "cuisine": "", "protein": "", "carb": ""}
        self.rnd = {"n": 3, "same": True, "filters": [self._blank_filter() for _ in range(MAX_MEALS)], "results": []}

        self.bar = ctk.CTkFrame(self, fg_color=t.BG, corner_radius=0, height=56)
        # Each screen is rebuilt inside `holder`. (CTkScrollableFrame.destroy() leaves its outer frame
        # behind, so clearing a holder is the reliable way to remove the previous screen.)
        self.holder = ctk.CTkFrame(self, fg_color=t.BG, corner_radius=0)
        self.body = None
        self.page = None
        self._wrapping: list[tuple[ctk.CTkLabel, int]] = []
        self._toast = None
        self._resize_job = None
        self.bind("<Configure>", self._on_resize, add="+")
        self.bind("<Escape>", lambda _e: self.back() if self.route != "/" else None)
        self.go("/")

    # ================================================================ plumbing
    @staticmethod
    def _blank_filter():
        return {"cuisine": "", "protein": "", "carb": ""}

    def go(self, route: str):
        self.route = route
        self.render()

    def back(self):
        r = self.route
        if r.startswith("/recipe/") or r == "/edit/new":
            self.go("/browse")
        elif r.startswith("/edit/"):
            self.go("/recipe/" + r.split("/")[2])
        elif r == "/import/review":
            self.go("/import")
        else:
            self.go("/")

    def render(self):
        for w in self.bar.winfo_children():
            w.destroy()
        for w in self.holder.winfo_children():
            w.destroy()
        self._wrapping = []
        self.bar.pack_forget()
        self.holder.pack_forget()
        if self.route != "/":
            self.bar.pack(side="top", fill="x", padx=8, pady=(6, 0))
        self.holder.pack(side="top", fill="both", expand=True)
        self.body = ctk.CTkScrollableFrame(self.holder, fg_color=t.BG, corner_radius=0,
                                           scrollbar_button_color=t.LINE, scrollbar_button_hover_color=t.MUTED)
        self.body.pack(side="top", fill="both", expand=True)
        self.page = ctk.CTkFrame(self.body, fg_color="transparent")
        self.page.pack(fill="x", padx=14, pady=(4, 28))

        parts = [p for p in self.route.split("/") if p]
        try:
            if not parts:
                self.home_view()
            elif parts[0] == "browse":
                self.browse_view()
            elif parts[0] == "recipe":
                self.detail_view(int(parts[1]))
            elif parts[0] == "edit":
                self.edit_view(None if parts[1] == "new" else int(parts[1]))
            elif parts[0] == "random":
                self.random_view()
            elif parts[0] == "import":
                if parts[1:2] == ["review"] and self.draft:
                    self.edit_view(None, review=True)
                else:
                    self.import_view()
            elif parts[0] == "backup":
                self.backup_view()
            else:
                raise LookupError(self.route)
        except (ValueError, IndexError, LookupError):
            self.go("/")

    def add(self, widget, gap: int = 12):
        widget.pack(fill="x", pady=(0, gap))
        return widget

    def topbar(self, title: str, actions: list[tuple[str, callable]] = ()):
        t.text_button(self.bar, "←", self.back, size=20, width=40).pack(side="left")
        t.label(self.bar, title, 18, bold=True).pack(side="left", padx=(4, 0))
        for text, cmd in reversed(list(actions)):
            t.text_button(self.bar, text, cmd).pack(side="right")

    # Labels that wrap to the window width, and keep doing so when it's resized.
    def wrap_width(self, offset: int) -> int:
        w = self.winfo_width() if self.winfo_width() > 1 else 460
        return max(180, w - offset)

    def text(self, parent, text: str, size: int = 14, color: str = t.INK, bold: bool = False, offset: int = 70):
        lbl = t.label(parent, text, size, color, bold, wraplength=self.wrap_width(offset))
        self._wrapping.append((lbl, offset))
        return lbl

    def _on_resize(self, e):
        if e.widget is not self:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)

        def apply():
            for lbl, offset in self._wrapping:
                if lbl.winfo_exists():
                    lbl.configure(wraplength=self.wrap_width(offset))
        self._resize_job = self.after(120, apply)

    def toast(self, msg: str, color: str = t.MINT):
        if self._toast is not None:
            self._toast.destroy()
        self._toast = ctk.CTkLabel(self, text=f"   {msg}   ", fg_color=color, text_color=t.INK, corner_radius=12,
                                   height=40, font=t.font(14), wraplength=380)
        self._toast.place(relx=0.5, rely=1.0, y=-20, anchor="s")
        self._toast.lift()
        toast = self._toast
        self.after(3200, lambda: toast.winfo_exists() and toast.destroy())

    def options(self, column: str, base: list[str]) -> list[str]:
        extra = [v for v in self.db.distinct(column) if v not in base]
        return sorted(base + extra) if column == "cuisine" else base + extra

    # ================================================================ home
    def home_view(self):
        p = self.page
        ctk.CTkFrame(p, height=18, fg_color="transparent").pack()
        self.add(t.label(p, "What's for dinner?", 28, bold=True), 2)
        n = self.db.count()
        self.add(t.label(p, f"{plural(n, 'recipe')} in your book", 14, t.MUTED), 18)

        hero, inner = t.card(p, t.PEACH, pad=20, command=lambda: self.go("/random"))
        self.add(hero, 14)
        inner.grid_columnconfigure(1, weight=1)
        t.label(inner, "⚄", 38).grid(row=0, column=0, rowspan=2, padx=(0, 14))
        t.label(inner, "Surprise me", 20, bold=True).grid(row=0, column=1, sticky="w")
        t.label(inner, "Pick meals at random", 13, t.MUTED).grid(row=1, column=1, sticky="w")
        t.label(inner, "›", 30).grid(row=0, column=2, rowspan=2)

        grid = ctk.CTkFrame(p, fg_color="transparent")
        self.add(grid)
        grid.grid_columnconfigure((0, 1), weight=1, uniform="tile")
        tiles = [("All recipes", "Browse & filter", "☰", t.MINT, "/browse"),
                 ("Add recipe", "Type one in", "＋", t.LAVENDER, "/edit/new"),
                 ("Import", "Paste a caption", "⇩", t.SKY, "/import"),
                 ("Backup", "Save or restore your recipes", "⇅", t.BUTTER, "/backup")]
        for i, (title, sub, icon, color, route) in enumerate(tiles):
            tile, inner = t.card(grid, color, pad=16, command=lambda r=route: self.go(r))
            tile.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0 if i % 2 == 0 else 7, 7 if i % 2 == 0 else 0),
                      pady=(0, 14))
            t.label(inner, icon, 24).pack(anchor="w")
            t.label(inner, title, 16, bold=True).pack(anchor="w", pady=(4, 0))
            sub_lbl = self.text(inner, sub, 12, t.MUTED, offset=290)
            sub_lbl.pack(anchor="w", fill="x")

    # ================================================================ browse
    def recipe_tile(self, parent, r: Recipe, trailing=None):
        tile, inner = t.card(parent, t.SURFACE, pad=14, command=lambda i=r.id: self.go(f"/recipe/{i}"))
        inner.grid_columnconfigure(0, weight=1)
        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.grid(row=0, column=0, sticky="ew")
        offset = 130 if trailing else 90
        self.text(body, r.name, 16, bold=True, offset=offset).pack(anchor="w", fill="x")
        if r.description:
            desc = r.description if len(r.description) <= 110 else r.description[:107].rstrip() + "…"
            self.text(body, desc, 13, t.MUTED, offset=offset).pack(anchor="w", fill="x", pady=(2, 0))
        tags = [(x, c) for x, c in ((r.cuisine, t.PEACH), (r.protein, t.ROSE), (r.carb, t.BUTTER)) if x]
        if tags:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(anchor="w", pady=(8, 0))
            for x, c in tags:
                t.pill(row, x, c).pack(side="left", padx=(0, 6))
        if trailing:
            trailing(inner).grid(row=0, column=1, padx=(8, 0))
        return tile

    def filter_row(self, parent, values: dict, on_change):
        """Three labelled dropdowns: Country, Protein, Base."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid_columnconfigure((0, 1, 2), weight=1, uniform="f")
        cols = [("Country", "cuisine", self.options("cuisine", CUISINES)),
                ("Protein", "protein", self.options("protein", PROTEINS)),
                ("Base", "carb", self.options("carb", CARBS))]
        for i, (title, key, opts) in enumerate(cols):
            t.label(row, title, 12, t.MUTED).grid(row=0, column=i, sticky="w", padx=(4 if i else 4, 0))
            dd = t.dropdown(row, [ANY] + opts, values[key] or ANY,
                            command=lambda v, k=key: on_change(k, "" if v == ANY else v))
            dd.grid(row=1, column=i, sticky="ew", padx=(0 if i == 0 else 3, 0 if i == 2 else 3))
        return row

    def browse_view(self):
        self.topbar("All recipes", [("＋ Add", lambda: self.go("/edit/new"))])
        p = self.page
        search = self.add(t.entry(p, self.browse["text"], "Search name or ingredient"), 10)
        count = t.label(p, "", 13, t.MUTED)
        results = ctk.CTkFrame(p, fg_color="transparent")

        def refresh():
            for w in results.winfo_children():
                w.destroy()
            self._wrapping = [(l, o) for l, o in self._wrapping if l.winfo_exists()]
            found = self.db.search(**self.browse)
            count.configure(text=plural(len(found), "recipe"))
            for r in found:
                self.recipe_tile(results, r).pack(fill="x", pady=(0, 10))
            if not found:
                msg = "No recipes match. Try clearing a filter." if self.db.count() else "No recipes yet. Add or import one!"
                t.label(results, msg, 14, t.MUTED).pack(anchor="w", pady=20, padx=4)

        def typed(_e=None):
            text = search.get()
            if text != self.browse["text"]:
                self.browse["text"] = text
                refresh()

        def changed(key, value):
            self.browse[key] = value
            refresh()

        search.bind("<KeyRelease>", typed)
        self.add(self.filter_row(p, self.browse, changed), 10)
        self.add(count, 6)
        self.add(results, 0)
        refresh()
        search.focus_set()

    # ================================================================ detail
    def detail_view(self, recipe_id: int):
        r = self.db.get(recipe_id)
        if not r:
            raise LookupError(recipe_id)

        def delete():
            if messagebox.askyesno("Delete recipe?", f"“{r.name}” will be removed for good.", parent=self, icon="warning"):
                self.db.delete(r.id)
                self.toast(f"Deleted {r.name}", t.DANGER)
                self.go("/browse")

        self.topbar("", [("Edit", lambda: self.go(f"/edit/{r.id}")), ("Delete", delete)])
        p = self.page
        self.add(self.text(p, r.name, 26, bold=True, offset=60), 8)
        tags = [(x, c) for x, c in ((r.cuisine, t.PEACH), (r.protein, t.ROSE), (r.carb, t.BUTTER)) if x]
        if tags:
            row = ctk.CTkFrame(p, fg_color="transparent")
            for x, c in tags:
                t.pill(row, x, c).pack(side="left", padx=(0, 6))
            row.pack(anchor="w", pady=(0, 12))
        if r.description:
            self.add(self.text(p, r.description, 15, t.MUTED, offset=60), 14)
        if r.ingredients:
            box, inner = t.card(p)
            self.add(box, 14)
            t.caps(inner, "Ingredients").pack(anchor="w", pady=(0, 8))
            for item in r.ingredients:
                line = ctk.CTkFrame(inner, fg_color="transparent")
                line.pack(fill="x", pady=3)
                ctk.CTkFrame(line, width=8, height=8, corner_radius=4, fg_color=t.ACCENT).pack(side="left", padx=(2, 10))
                self.text(line, item, 14, offset=120).pack(side="left", fill="x", expand=True)
        steps = [s for s in r.method.split("\n") if s.strip()]
        if steps:
            box, inner = t.card(p)
            self.add(box, 14)
            t.caps(inner, "Method").pack(anchor="w", pady=(0, 8))
            for n, step in enumerate(steps, 1):
                line = ctk.CTkFrame(inner, fg_color="transparent")
                line.pack(fill="x", pady=4)
                ctk.CTkLabel(line, text=str(n), width=26, height=26, corner_radius=13, fg_color=t.LAVENDER,
                             text_color=t.INK, font=t.font(12)).pack(side="left", anchor="n", padx=(0, 10))
                self.text(line, step, 14, offset=130).pack(side="left", fill="x", expand=True)
        if r.source:
            self.add(self.text(p, f"Source: {r.source}", 12, t.MUTED, offset=60))

    # ================================================================ add / edit
    def edit_view(self, recipe_id: int | None, review: bool = False):
        if recipe_id is not None:
            r = self.db.get(recipe_id)
            if not r:
                raise LookupError(recipe_id)
        elif review and self.draft:
            r = self.draft
        else:
            r = Recipe()

        self.topbar("Edit recipe" if recipe_id else ("Check import" if review else "New recipe"))
        p = self.page
        if review:
            hint, inner = t.card(p, t.SKY, pad=14)
            self.text(inner, "Have a quick look over what was imported, then save.", 14, offset=100).pack(anchor="w")
            self.add(hint, 14)

        def field(title, widget, gap=12):
            t.label(p, title, 12, t.MUTED).pack(anchor="w", padx=4, pady=(0, 3))
            return self.add(widget, gap)

        name = field("Name *", t.entry(p, r.name), 2)
        name_err = t.label(p, "", 12, t.darker(t.DANGER, 0.25))
        self.add(name_err, 8)
        desc = field("Description - what is this meal?", t.textbox(p, r.description, 70))
        cuisine = field("Country / cuisine - pick one or type your own",
                        t.combobox(p, self.options("cuisine", CUISINES), r.cuisine))

        pair = ctk.CTkFrame(p, fg_color="transparent")
        pair.grid_columnconfigure((0, 1), weight=1, uniform="pc")
        t.label(pair, "Protein", 12, t.MUTED).grid(row=0, column=0, sticky="w", padx=4)
        t.label(pair, "Base", 12, t.MUTED).grid(row=0, column=1, sticky="w", padx=8)
        protein = t.dropdown(pair, [BLANK] + self.options("protein", PROTEINS), r.protein or BLANK)
        carb = t.dropdown(pair, [BLANK] + self.options("carb", CARBS), r.carb or BLANK)
        protein.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        carb.grid(row=1, column=1, sticky="ew", padx=(4, 0))
        self.add(pair)

        ings = field("Ingredients - one per line", t.textbox(p, "\n".join(r.ingredients), 170))
        method = field("Method - one step per line", t.textbox(p, r.method, 170))
        source = field("Source (link, book…)", t.entry(p, r.source))

        def save():
            if not name.get().strip():
                name_err.configure(text="Give it a name")
                name.focus_set()
                return
            rec = Recipe(id=r.id, name=name.get(), description=t.text_of(desc).strip(), cuisine=cuisine.get().strip(),
                         protein="" if protein.get() == BLANK else protein.get(),
                         carb="" if carb.get() == BLANK else carb.get(),
                         ingredients=[l.strip() for l in t.text_of(ings).split("\n") if l.strip()],
                         method=t.text_of(method).strip(), source=source.get().strip())
            if rec.id:
                self.db.update(rec)
            else:
                rec.id = self.db.add(rec)
            self.draft = None
            self.toast(f"Saved {rec.name.strip()}")
            self.go(f"/recipe/{rec.id}")

        self.save_current = save  # used by tests
        row = ctk.CTkFrame(p, fg_color="transparent")
        t.button(row, "✓  Save recipe", save).pack(side="left")
        self.add(row, 0)
        if not r.name:
            name.focus_set()

    # ================================================================ randomiser
    def pick(self, f: dict, exclude: set[int]) -> int | None:
        candidates = [r.id for r in self.db.search(**f) if r.id not in exclude]
        return random.choice(candidates) if candidates else None

    def random_view(self):
        self.topbar("Random meals")
        p, s = self.page, self.rnd

        counter, inner = t.card(p, t.PEACH, pad=10)
        self.add(counter)
        t.label(inner, "How many meals?", 16).pack(side="left", padx=(6, 0))
        plus = t.text_button(inner, "＋", lambda: set_n(1), size=20, width=40)
        plus.pack(side="right")
        n_lbl = t.label(inner, str(s["n"]), 22, bold=True, width=34, anchor="center")
        n_lbl.pack(side="right")
        t.text_button(inner, "－", lambda: set_n(-1), size=20, width=40).pack(side="right")

        same = ctk.CTkSwitch(p, text="Same filters for every meal", font=t.font(14), text_color=t.INK,
                             progress_color=t.ACCENT, fg_color=t.LINE, button_color=t.SURFACE,
                             button_hover_color=t.SURFACE, command=lambda: toggle_same())
        if s["same"]:
            same.select()
        self.add(same)

        filters_box, filters = t.card(p, t.SURFACE, pad=12)
        self.add(filters_box)
        shuffle_row = ctk.CTkFrame(p, fg_color="transparent")
        t.button(shuffle_row, "⚄  Shuffle!", lambda: shuffle(), color=t.PEACH, width=180).pack()
        self.add(shuffle_row, 16)
        results = ctk.CTkFrame(p, fg_color="transparent")
        self.add(results, 0)

        def draw_filters():
            for w in filters.winfo_children():
                w.destroy()
            for i in ([0] if s["same"] else range(s["n"])):
                if not s["same"]:
                    t.caps(filters, f"Meal {i + 1}").pack(anchor="w", pady=(0 if i == 0 else 10, 2))
                self.filter_row(filters, s["filters"][i], lambda k, v, i=i: changed(i, k, v)).pack(fill="x")

        def draw_results():
            for w in results.winfo_children():
                w.destroy()
            self._wrapping = [(l, o) for l, o in self._wrapping if l.winfo_exists()]
            if s["results"]:
                t.caps(results, "Your meals").pack(anchor="w", pady=(0, 8))
            for i, rid in enumerate(s["results"]):
                r = self.db.get(rid) if rid else None
                reroll = (lambda parent, i=i: t.text_button(parent, "↻", lambda: do_reroll(i), size=20, width=40))
                if r:
                    self.recipe_tile(results, r, reroll).pack(fill="x", pady=(0, 10))
                else:
                    box, inner = t.card(results, t.SURFACE, pad=14)
                    inner.grid_columnconfigure(0, weight=1)
                    t.label(inner, f"Meal {i + 1}: no match for these filters", 14, t.MUTED).grid(row=0, column=0, sticky="w")
                    reroll(inner).grid(row=0, column=1)
                    box.pack(fill="x", pady=(0, 10))

        def set_n(delta):
            s["n"] = max(1, min(MAX_MEALS, s["n"] + delta))
            s["results"] = s["results"][: s["n"]]
            n_lbl.configure(text=str(s["n"]))
            if not s["same"]:
                draw_filters()
            draw_results()

        def toggle_same():
            s["same"] = bool(same.get())
            draw_filters()

        def changed(i, key, value):
            if s["same"]:
                for f in s["filters"]:
                    f[key] = value
            else:
                s["filters"][i][key] = value

        def shuffle():
            chosen: list[int | None] = []
            for i in range(s["n"]):
                chosen.append(self.pick(s["filters"][i], {c for c in chosen if c}))
            s["results"] = chosen
            if not any(chosen):
                self.toast("Nothing matches those filters", t.PEACH)
            draw_results()

        def do_reroll(i):
            others = {c for j, c in enumerate(s["results"]) if c and j != i}
            new = self.pick(s["filters"][i], others | ({s["results"][i]} if s["results"][i] else set()))
            if new is None:
                self.toast("No other recipe matches - that's the only one!", t.PEACH)
                return
            s["results"][i] = new
            draw_results()

        self.shuffle, self.reroll, self.set_meals = shuffle, do_reroll, set_n  # used by tests
        draw_filters()
        draw_results()

    # ================================================================ import
    def import_view(self):
        self.topbar("Import a recipe")
        p = self.page
        box, inner = t.card(p, t.MINT, pad=16)
        self.add(box, 14)
        t.caps(inner, "Paste a recipe").pack(anchor="w")
        self.text(inner, "Copy a caption or recipe (on Instagram, tap ⋯ or long-press the caption), then paste it here. "
                         "For a photo or screenshot, copy the text with Google Lens first.",
                  13, t.MUTED, offset=110).pack(anchor="w", fill="x", pady=(4, 8))
        text = t.textbox(inner, self.import_text, 260)

        def paste():
            try:
                clip = self.clipboard_get()
            except tkinter.TclError:
                self.toast("The clipboard is empty", t.PEACH)
                return
            text.delete("1.0", "end")
            text.insert("1.0", clip)
            self.import_text = clip

        t.outline_button(inner, "Paste from clipboard", paste).pack(anchor="w", pady=(0, 8))
        text.pack(fill="x")
        text.bind("<KeyRelease>", lambda _e: setattr(self, "import_text", t.text_of(text)))
        t.label(inner, "Where it's from (optional)", 12, t.MUTED).pack(anchor="w", padx=4, pady=(10, 3))
        source = t.entry(inner, "", "e.g. Instagram link or account name")
        source.pack(fill="x")

        def convert():
            txt = t.text_of(text).strip()
            if not txt:
                self.toast("Paste some recipe text first", t.PEACH)
                return
            self.draft = importer.parse_text(txt, source=source.get().strip())
            self.import_text = ""
            self.go("/import/review")

        self.convert = convert  # used by tests
        row = ctk.CTkFrame(p, fg_color="transparent")
        t.button(row, "✦  Convert to recipe", convert, color=t.PEACH).pack()
        self.add(row, 0)
        text.focus_set()

    # ================================================================ backup
    def export_json(self) -> str:
        recs = self.db.search()
        return json.dumps([{k: v for k, v in r.__dict__.items() if k != "id"} for r in recs], indent=2, ensure_ascii=False)

    def restore_from(self, raw: str):
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("not a recipe backup")
        existing = {r.name.lower() for r in self.db.search()}
        added = 0
        for d in data:
            name = str(d.get("name", "Untitled"))
            if name.lower() in existing:
                continue
            ings = d.get("ingredients") or []
            self.db.add(Recipe(name=name, description=d.get("description", ""), cuisine=d.get("cuisine", ""),
                               protein=d.get("protein", ""), carb=d.get("carb", ""),
                               ingredients=ings if isinstance(ings, list) else str(ings).split("\n"),
                               method=d.get("method", ""), source=d.get("source", "")))
            existing.add(name.lower())
            added += 1
        self.toast(f"Added {plural(added, 'recipe')} (duplicates skipped)")

    def backup_view(self):
        self.topbar("Backup & restore")
        p = self.page

        def export_file():
            path = filedialog.asksaveasfilename(parent=self, title="Save recipe backup", defaultextension=".json",
                                                initialfile="recipes_backup.json", filetypes=[("Recipe backup", "*.json")])
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.export_json())
                self.toast("Backup saved")

        def copy():
            self.clipboard_clear()
            self.clipboard_append(self.export_json())
            self.toast("Backup copied - paste it into a note or email")

        def restore_file():
            path = filedialog.askopenfilename(parent=self, title="Choose a backup", filetypes=[("Recipe backup", "*.json")])
            if path:
                try:
                    with open(path, encoding="utf-8") as f:
                        self.restore_from(f.read())
                except (OSError, ValueError, AttributeError) as ex:
                    self.toast(f"Couldn't read that backup ({ex.__class__.__name__})", t.DANGER)

        def restore_clip():
            try:
                self.restore_from(self.clipboard_get())
            except (tkinter.TclError, ValueError, AttributeError):
                self.toast("The clipboard doesn't contain a recipe backup", t.DANGER)

        for title, blurb, color, buttons in [
            ("Back up", "Save all your recipes to a file, or copy them to paste into an email or note.", t.MINT,
             [("Export to file", export_file), ("Copy to clipboard", copy)]),
            ("Restore", "Add recipes from a backup. Recipes that already exist (same name) are skipped.", t.BUTTER,
             [("Restore from file", restore_file), ("Restore from clipboard", restore_clip)]),
        ]:
            box, inner = t.card(p, color, pad=16)
            self.add(box, 14)
            t.caps(inner, title).pack(anchor="w")
            self.text(inner, blurb, 13, offset=110).pack(anchor="w", fill="x", pady=(4, 10))
            for text, cmd in buttons:
                t.outline_button(inner, text, cmd, width=200).pack(anchor="w", pady=(0, 6))

        self.add(self.text(p, f"Your recipes are stored in:\n{self.db.path}", 11, t.MUTED, offset=60))


def main():
    RecipeApp().mainloop()


if __name__ == "__main__":
    main()
