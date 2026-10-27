import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, REVIEW_TEXT
from estado import autenticar_usuario, registrar_consentimento_sessao

def render_login(page: ft.Page, navegar):
    email_input = ft.TextField(
        label="E-mail institucional",
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
    )
    senha_input = ft.TextField(
        label="Palavra-passe",
        password=True,
        can_reveal_password=True,
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
    )

    checkbox_consentimento = ft.Checkbox(
        label="Confirmo que o consentimento livre e esclarecido foi obtido e que esta avaliação tem fim exclusivamente académico (não configura diagnóstico clínico).",
        value=False,
    )

    texto_erro = ft.Text("", color=REVIEW_TEXT, size=13, visible=False)
    carregando = ft.ProgressRing(visible=False, width=22, height=22)

    def ao_clicar_entrar(e):
        texto_erro.visible = False

        if not email_input.value or not senha_input.value:
            texto_erro.value = "Preencha o e-mail e a palavra-passe."
            texto_erro.visible = True
            page.update()
            return

        if not checkbox_consentimento.value:
            texto_erro.value = "É obrigatório confirmar o registo de consentimento antes de iniciar."
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

        # Guarda o estado e o timestamp do consentimento
        registrar_consentimento_sessao()
        navegar("participantes")

    page.add(
        ft.Column(
            controls=[
                ft.Divider(height=30, color="transparent"),
                ft.Text("OrtoTest", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.Text(
                    "Avaliação Ortopédica Académica",
                    color=TEXT_SECONDARY,
                    size=14,
                ),
                ft.Divider(height=15, color="transparent"),
                email_input,
                senha_input,
                ft.Container(
                    bgcolor=SURFACE,
                    border=ft.Border.all(width=1, color=CARD_BORDER),
                    border_radius=12,
                    padding=10,
                    content=checkbox_consentimento,
                ),
                texto_erro,
                carregando,
                ft.Button(
                    content=ft.Text("Entrar e Iniciar", weight=ft.FontWeight.BOLD),
                    bgcolor=PRIMARY,
                    color="white",
                    width=350,
                    on_click=ao_clicar_entrar,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
    )