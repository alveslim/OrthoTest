import flet as ft
from theme import apply_theme
from tela_login import render_login
from tela_participantes import render_participantes
from tela_selecao import render_selecao
from tela_teste import render_teste
def main(page: ft.Page):
    apply_theme(page)
    page.title = "OrthoTest MVP"
    page.window.width = 390
    page.window.height = 844
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Dicionário de rotas simples para não usar ifs gigantes
    rotas = {
        "login": lambda: render_login(page, navegar),
        "participantes": lambda: render_participantes(page, navegar),
        "selecao": lambda: render_selecao(page, navegar),
        "teste": lambda: render_teste(page, navegar),
    }

    def navegar(nome_rota: str):
        page.clean()
        rotas[nome_rota]()
        page.update()

    navegar("login")

if __name__ == "__main__":
    ft.run(main)