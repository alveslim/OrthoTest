import flet as ft
from theme import apply_theme
from tela_login import render_login
from tela_participantes import render_participantes
from tela_selecao import render_selecao
from tela_teste import render_teste
from estado import sessao, limpar_sessao

def main(page: ft.Page):
    apply_theme(page)
    page.title = "OrthoTest MVP"
    page.window.width = 390
    page.window.height = 844
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    rotas = {
        "login": lambda: render_login(page, navegar),
        "participantes": lambda: render_participantes(page, navegar),
        "selecao": lambda: render_selecao(page, navegar),
        "teste": lambda: render_teste(page, navegar),
    }

    def navegar(nome_rota: str):
        if nome_rota == "login":
            limpar_sessao()
        elif not sessao["access_token"] or not sessao["consentimento_aceito"]:
            # Bloqueia acesso a qualquer rota interna sem login e sem consentimento
            nome_rota = "login"

        page.clean()
        rotas[nome_rota]()
        page.update()

    navegar("login")

if __name__ == "__main__":
    ft.run(main)