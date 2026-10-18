import flet as ft

PRIMARY = "#1659B2"
BACKGROUND = "#F7F8FC"
SURFACE = "#FFFFFF"
CARD_BORDER = "#DFE6EE"
TEXT_PRIMARY = "#152231"
TEXT_SECONDARY = "#42556D"


def apply_theme(page: ft.Page) -> None:
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY,
        use_material3=True,
    )
    page.bgcolor = BACKGROUND