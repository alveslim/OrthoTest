import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY

def render_participantes(page: ft.Page, navegar):
    cabecalho = ft.Row(
        controls=[
            ft.Text("Participantes", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.IconButton(icon="logout", icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("login")),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    card_p014 = ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(width=1, color=CARD_BORDER),
        border_radius=16,
        padding=20,
        on_click=lambda _: navegar("selecao"),
        content=ft.Column(
            controls=[
                ft.Text("P-014", theme_style=ft.TextThemeStyle.TITLE_LARGE),
                ft.Text("19 anos · 65 kg · 1,70 m", theme_style=ft.TextThemeStyle.BODY_MEDIUM, color=TEXT_SECONDARY),
                ft.Text("1 de 4 testes", theme_style=ft.TextThemeStyle.BODY_MEDIUM, color=PRIMARY),
            ]
        ),
    )

    page.add(
        cabecalho,
        card_p014,
        ft.Button(content="Novo participante", bgcolor=PRIMARY, color=ft.Colors.WHITE, width=350),
    )