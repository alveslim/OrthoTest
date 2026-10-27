import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY

def render_login(page: ft.Page, navegar):
    page.add(
        ft.Column(
            controls=[
                ft.Divider(height=40, color="transparent"),
                ft.Text("OrthoTest", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.Text("Avaliação Ortopédica Acadêmica", color=TEXT_SECONDARY, size=14),
                ft.Divider(height=20, color="transparent"),
                ft.TextField(label="E-mail", border_color=CARD_BORDER, bgcolor=SURFACE, color=TEXT_PRIMARY),
                ft.TextField(label="Senha", password=True, border_color=CARD_BORDER, bgcolor=SURFACE, color=TEXT_PRIMARY),
                ft.Button(
                    content=ft.Text("Entrar", weight=ft.FontWeight.BOLD),
                    bgcolor=PRIMARY, color="white", width=350,
                    on_click=lambda _: navegar("participantes")
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )