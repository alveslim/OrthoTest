import flet as ft
from theme import apply_theme
from tela_login import render_login
from tela_participantes import render_participantes
from tela_selecao import render_selecao
from tela_teste import render_teste
from estado import sessao, limpar_sessao, tentar_restaurar_sessao
from tela_resumo_ia import render_resumo_ia
from tela_dashboard import render_dashboard

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
        "dashboard": lambda: render_dashboard(page, navegar),
        "resumo_ia": lambda: render_resumo_ia(page, navegar)
    }

    def navegar(nome_rota: str):
        if nome_rota == "login":
            limpar_sessao()
        elif not sessao["access_token"]:
            # Bloqueia acesso a qualquer rota interna sem login
            nome_rota = "login"

        page.clean()
        try:
            rotas[nome_rota]()
        except Exception as exc:  # nunca deixar a tela em branco: mostra o erro e oferece voltar
            page.clean()
            page.add(
                ft.Text("Não foi possível abrir esta tela.", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"{type(exc).__name__}: {exc}", size=12),
                ft.Button(content=ft.Text("Voltar ao início"), on_click=lambda _: navegar("participantes")),
            )
        page.update()

    # Já entrou antes neste aparelho? Abre direto (funciona sem internet).
    navegar("participantes" if tentar_restaurar_sessao() else "login")

if __name__ == "__main__":
    ft.run(main)