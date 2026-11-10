import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, REVIEW_TEXT
from estado import MODO_DEMO, autenticar_usuario, situacao_rede

def render_login(page: ft.Page, navegar):
    email_input = ft.TextField(
        label="E-mail institucional",
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
    )
    senha_input = ft.TextField(
        label="Senha",
        password=True,
        can_reveal_password=True,
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
    )

    aviso_demo = ft.Container(
        visible=MODO_DEMO, bgcolor="#FFF2CC", border_radius=8, padding=8,
        content=ft.Text("MODO DEMONSTRAÇÃO: qualquer e-mail e senha entram e nada é gravado. "
                        "Para uso real, remova MODO_DEMO do .env.", size=12, color="#5C4400"),
    )
    pend = situacao_rede()["pendentes"]
    aviso_pendentes = ft.Text(
        f"{pend} registro(s) guardado(s) neste aparelho serão enviados depois do login." if pend else "",
        size=12, color=TEXT_SECONDARY, visible=bool(pend))

    texto_erro = ft.Text("", color=REVIEW_TEXT, size=13, visible=False)
    carregando = ft.ProgressRing(visible=False, width=22, height=22)

    def ao_clicar_entrar(e):
        texto_erro.visible = False

        if not email_input.value or not senha_input.value:
            texto_erro.value = "Preencha o e-mail e a senha."
            texto_erro.visible = True
            page.update()
            return

        carregando.visible = True
        page.update()

        sucesso, mensagem = autenticar_usuario(email_input.value, senha_input.value)
        carregando.visible = False

        if not sucesso:
            texto_erro.value = mensagem
            texto_erro.visible = True
            page.update()
            return

        navegar("participantes")

    page.add(
        ft.Column(
            controls=[
                ft.Divider(height=30, color="transparent"),
                ft.Text("OrthoTest", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.Text(
                    "Avaliação Ortopédica Acadêmica",
                    color=TEXT_SECONDARY,
                    size=14,
                ),
                aviso_demo,
                ft.Divider(height=15, color="transparent"),
                email_input,
                senha_input,
                texto_erro,
                aviso_pendentes,
                carregando,
                ft.Button(
                    content=ft.Text("Entrar e Iniciar", weight=ft.FontWeight.BOLD),
                    bgcolor=PRIMARY,
                    color="white",
                    width=350,
                    on_click=ao_clicar_entrar,
                ),
                ft.Text("O app lembra do seu login neste aparelho. O primeiro acesso precisa de internet.",
                        size=12, color=TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
    )