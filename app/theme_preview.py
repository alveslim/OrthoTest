import flet as ft

from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_SECONDARY, apply_theme


def main(page: ft.Page) -> None:
    apply_theme(page)
    page.title = "OrtoCheck — prévia do tema"
    page.padding = 24

    page.add(
        ft.Column(
            controls=[
                ft.Text(
                    "Participantes",
                    theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                ),
                ft.Container(
                    bgcolor=SURFACE,
                    border=ft.Border.all(width=1, color=CARD_BORDER),
                    border_radius=16,
                    padding=20,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "P-014",
                                theme_style=ft.TextThemeStyle.TITLE_LARGE,
                            ),
                            ft.Text(
                                "19 anos · 65 kg · 1,70 m",
                                theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                                color=TEXT_SECONDARY,
                            ),
                            ft.Text(
                                "7 de 16 testes",
                                theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                                color=PRIMARY,
                            ),
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