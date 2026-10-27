import flet as ft

PRIMARY = "#1659B2"
BACKGROUND = "#F7F8FC"
SURFACE = "#FFFFFF"
CARD_BORDER = "#DFE6EE"
TEXT_PRIMARY = "#152231"
TEXT_SECONDARY = "#42556D"
WARNING_BACKGROUND = "#FFF2CC"
WARNING_TEXT = "#5C4400"
REVIEW_BACKGROUND = "#FDE8E8"
REVIEW_TEXT = "#8B1E2D"


def apply_theme(page: ft.Page) -> None:
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY,
        use_material3=True,
        text_theme=ft.TextTheme(
            headline_medium=ft.TextStyle(
                size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY
            ),
            title_large=ft.TextStyle(
                size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY
            ),
            body_medium=ft.TextStyle(size=14, color=TEXT_PRIMARY),
            body_small=ft.TextStyle(size=12, color=TEXT_SECONDARY),
        ),
    )
    page.bgcolor = BACKGROUND