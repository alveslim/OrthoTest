import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY

def render_selecao(page: ft.Page, navegar):
    cabecalho = ft.Row(
        controls=[
            ft.IconButton(icon="arrow_back_ios", icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("participantes")),
            ft.Text("Testes • P-014", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Container(width=40),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    card_lachman = ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(width=1, color=CARD_BORDER),
        border_radius=12,
        padding=15,
        on_click=lambda _: navegar("teste"),
        content=ft.Row(
            controls=[
                ft.Text("1. Teste de Lachman (Joelho)", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Text("Pendente", color=TEXT_SECONDARY, size=12),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )

    page.add(cabecalho, ft.Text("Progresso: 1 de 4", color=PRIMARY), card_lachman)