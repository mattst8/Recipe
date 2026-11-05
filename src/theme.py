"""Pastel, minimal look shared by every screen."""
import flet as ft

BG = "#FBF8F4"        # warm cream background
SURFACE = "#FFFFFF"
INK = "#4A4453"       # soft charcoal text
MUTED = "#8C8597"

PEACH = "#F9D5C5"
MINT = "#CDEBD8"
LAVENDER = "#DCD3F2"
SKY = "#CFE3F5"
BUTTER = "#F7E8B5"
ROSE = "#F4C7D3"

ACCENT = "#B9A6E3"    # deeper lavender for buttons
DANGER = "#E8A0A0"

RADIUS = 18


def app_theme() -> ft.Theme:
    return ft.Theme(color_scheme_seed=ACCENT, use_material3=True)


def title(text: str, size: int = 26) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.W_600, color=INK)


def label(text: str) -> ft.Text:
    return ft.Text(text, size=13, color=MUTED, weight=ft.FontWeight.W_500)


def card(content: ft.Control, color: str = SURFACE, on_click=None, padding: int = 16) -> ft.Container:
    return ft.Container(
        content=content, bgcolor=color, border_radius=RADIUS, padding=padding, on_click=on_click,
        ink=on_click is not None,
        shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.06, INK), offset=ft.Offset(0, 3)),
    )


def pill(text: str, color: str) -> ft.Container:
    return ft.Container(
        ft.Text(text, size=12, color=INK), bgcolor=color, border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
    )


def primary_button(text: str, icon=None, on_click=None, color: str = ACCENT) -> ft.FilledButton:
    return ft.FilledButton(
        text=text, icon=icon, on_click=on_click,
        style=ft.ButtonStyle(bgcolor=color, color=INK, shape=ft.RoundedRectangleBorder(radius=14),
                             padding=ft.padding.symmetric(horizontal=20, vertical=14)),
    )


def text_field(lbl: str, value: str = "", multiline: bool = False, **kw) -> ft.TextField:
    return ft.TextField(
        label=lbl, value=value, multiline=multiline, min_lines=3 if multiline else 1,
        max_lines=12 if multiline else 1, filled=True, bgcolor=SURFACE, border_radius=14,
        border_color=ft.Colors.TRANSPARENT, focused_border_color=ACCENT, color=INK, **kw,
    )


ANY = "Any"


def dd_value(dd: ft.Dropdown) -> str:
    """Selected value, with 'Any'/nothing returned as ''."""
    return "" if dd.value in (None, ANY) else dd.value


def dropdown(lbl: str, options: list[str], value: str = "", any_option: bool = False, on_change=None) -> ft.Dropdown:
    opts = ([ft.dropdown.Option(key=ANY, text=ANY)] if any_option else []) + \
           [ft.dropdown.Option(key=o, text=o) for o in options if o != ANY]
    if any_option and not value:
        value = ANY
    return ft.Dropdown(
        label=lbl, options=opts, value=value or None, on_change=on_change, filled=True, bgcolor=SURFACE,
        border_radius=14, border_color=ft.Colors.TRANSPARENT, expand=True, dense=True,
    )
