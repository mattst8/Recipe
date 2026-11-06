"""Pastel, minimal look shared by every screen (CustomTkinter)."""
import sys
import tkinter

import customtkinter as ctk

BG = "#FBF8F4"        # warm cream background
SURFACE = "#FFFFFF"
INK = "#4A4453"       # soft charcoal text
MUTED = "#8C8597"
LINE = "#E9E3EC"      # hairline borders
FIELD = "#F4F0F7"     # dropdown background

PEACH = "#F9D5C5"
MINT = "#CDEBD8"
LAVENDER = "#DCD3F2"
SKY = "#CFE3F5"
BUTTER = "#F7E8B5"
ROSE = "#F4C7D3"

ACCENT = "#B9A6E3"    # deeper lavender for buttons
DANGER = "#E8A0A0"

RADIUS = 18

if sys.platform == "win32":
    FAMILY = "Segoe UI"
elif sys.platform == "darwin":
    FAMILY = "Helvetica Neue"
else:
    FAMILY = "DejaVu Sans"


def font(size: int = 14, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FAMILY, size=size, weight="bold" if bold else "normal")


def darker(color: str, amount: float = 0.07) -> str:
    """A slightly darker shade, used for hover states."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(max(0, int(c * (1 - amount))) for c in (r, g, b))


_INPUTS = (ctk.CTkButton, ctk.CTkOptionMenu, ctk.CTkSwitch, ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkComboBox)


def make_clickable(widget, command):
    """Make a card and everything on it (except its own buttons and inputs) clickable."""
    def bind(w):
        if isinstance(w, _INPUTS):
            return
        w.bind("<Button-1>", lambda _e: command(), add="+")
        try:
            w.configure(cursor="hand2")
        except (ValueError, Exception):  # noqa: BLE001 - some widgets have no cursor option
            pass
        if isinstance(w, ctk.CTkFrame):
            for child in w.winfo_children():
                if isinstance(child, ctk.CTkBaseClass):
                    bind(child)
    bind(widget)


def card(parent, color: str = SURFACE, pad: int = 16, command=None):
    """A rounded panel. Returns (outer, inner): put content in `inner`."""
    border = 1 if color == SURFACE else 0
    outer = ctk.CTkFrame(parent, fg_color=color, corner_radius=RADIUS, border_width=border, border_color=LINE)
    inner = ctk.CTkFrame(outer, fg_color="transparent")
    inner.pack(fill="x", padx=pad, pady=pad)
    if command:
        hover = darker(color, 0.04)

        def enter(_e):
            outer.configure(fg_color=hover)

        def leave(_e):
            x, y = outer.winfo_pointerxy()
            under = outer.winfo_containing(x, y)
            if under is None or not str(under).startswith(str(outer)):
                outer.configure(fg_color=color)
        # Bind on the underlying tk frame, which also sees the pointer over the card's children.
        tkinter.Frame.bind(outer, "<Enter>", enter, "+")
        tkinter.Frame.bind(outer, "<Leave>", leave, "+")

        def wire():  # runs once the caller has filled the card
            if outer.winfo_exists():
                make_clickable(outer, command)
        outer.after_idle(wire)
    return outer, inner


def label(parent, text: str, size: int = 14, color: str = INK, bold: bool = False, **kw) -> ctk.CTkLabel:
    kw.setdefault("anchor", "w")
    return ctk.CTkLabel(parent, text=text, font=font(size, bold), text_color=color, justify="left", **kw)


def caps(parent, text: str) -> ctk.CTkLabel:
    """Small uppercase section label."""
    return label(parent, text.upper(), 12, MUTED, bold=True)


def pill(parent, text: str, color: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=f"  {text}  ", fg_color=color, corner_radius=11, height=22,
                        font=font(12), text_color=INK)


def button(parent, text: str, command=None, color: str = ACCENT, **kw) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, fg_color=color, hover_color=darker(color),
                         text_color=INK, corner_radius=14, height=44, font=font(15, bold=True), **kw)


def outline_button(parent, text: str, command=None, **kw) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, fg_color="transparent", hover_color=FIELD,
                         border_width=1, border_color=darker(LINE, 0.12), text_color=INK, corner_radius=12,
                         height=36, font=font(13), **kw)


def text_button(parent, text: str, command=None, size: int = 14, **kw) -> ctk.CTkButton:
    kw.setdefault("width", 0)
    return ctk.CTkButton(parent, text=text, command=command, fg_color="transparent", hover_color=FIELD,
                         text_color=INK, corner_radius=12, height=36, font=font(size), **kw)


def entry(parent, value: str = "", placeholder: str = "") -> ctk.CTkEntry:
    e = ctk.CTkEntry(parent, placeholder_text=placeholder or None, height=40, corner_radius=12, fg_color=SURFACE,
                     border_width=1, border_color=LINE, text_color=INK, placeholder_text_color=MUTED, font=font(14))
    if value:
        e.insert(0, value)
    return e


def textbox(parent, value: str = "", height: int = 90) -> ctk.CTkTextbox:
    t = ctk.CTkTextbox(parent, height=height, corner_radius=12, fg_color=SURFACE, border_width=1, border_color=LINE,
                       text_color=INK, font=font(14), wrap="word")
    if value:
        t.insert("1.0", value)
    return t


def text_of(t: ctk.CTkTextbox) -> str:
    return t.get("1.0", "end-1c")


def dropdown(parent, values: list[str], value: str, command=None) -> ctk.CTkOptionMenu:
    return ctk.CTkOptionMenu(parent, values=values, command=command, fg_color=FIELD, button_color=FIELD,
                             button_hover_color=LINE, text_color=INK, dropdown_fg_color=SURFACE,
                             dropdown_text_color=INK, dropdown_hover_color=LAVENDER, corner_radius=12, height=36,
                             font=font(13), dropdown_font=font(13), dynamic_resizing=False, width=90,
                             variable=ctk.StringVar(value=value))


def combobox(parent, values: list[str], value: str) -> ctk.CTkComboBox:
    c = ctk.CTkComboBox(parent, values=values, height=40, corner_radius=12, fg_color=SURFACE, border_width=1,
                        border_color=LINE, button_color=FIELD, button_hover_color=LINE, text_color=INK,
                        dropdown_fg_color=SURFACE, dropdown_text_color=INK, dropdown_hover_color=LAVENDER,
                        font=font(14), dropdown_font=font(13))
    c.set(value)
    return c
