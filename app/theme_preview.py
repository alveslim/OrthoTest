import flet as ft

from theme import (
    PRIMARY,
    SURFACE,
    CARD_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    apply_theme,
)


def main(page: ft.Page) -> None:
    apply_theme(page)
    page.title = "OrtoCheck — prévia do tema"
    page.padding = 24

    page.add(
        ft.Column(
            controls=[
                ft.Text(
                    "Participantes",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                ),
                ft.Container(
                    bgcolor=SURFACE,
                    border=ft.Border.all(width=1, color=CARD_BORDER),
                    border_radius=16,
                    padding=20,
                    content=ft.Column(
                        controls=[
                            ft.Text("P-014", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text("19 anos · 65 kg · 1,70 m", color=TEXT_SECONDARY),
                            ft.Text("7 de 16 testes", color=PRIMARY),
                        ]
                    ),
                ),
                ft.Button(
                    content="Novo participante",
                    bgcolor=PRIMARY,
                    color=ft.Colors.WHITE,
                ),
            ]
        )
    )


if __name__ == "__main__":
    ft.run(main)