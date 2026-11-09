import flet as ft
from theme import (
    PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, REVIEW_TEXT
)
from estado import (
    sessao, salvar_resultado_teste_api, excluir_resultado_teste_api
)


def render_teste(page: ft.Page, navegar):
    teste = sessao.get("teste_atual")
    if not teste or not teste.get("id"):
        page.add(
            ft.Text("Nenhum teste foi selecionado.", color=REVIEW_TEXT),
            ft.TextButton("Voltar aos testes", on_click=lambda _: navegar("selecao")),
        )
        return

    resultado_salvo = sessao.get("resultado_atual") or {}
    lado_selecionado = {"valor": resultado_salvo.get("lado", "Direito")}
    resultado_selecionado = {"valor": resultado_salvo.get("resultado", "Não realizado")}
    dor_atual = int(resultado_salvo.get("dor_0_10") or 0)

    valor_dor_txt = ft.Text(
        f"{dor_atual}/10", weight=ft.FontWeight.BOLD, size=16, color=PRIMARY
    )
    feedback_msg = ft.Text("", size=12, color=REVIEW_TEXT, visible=False)

    def atualizar_dor_ui(event):
        nonlocal dor_atual
        dor_atual = int(round(float(event.control.value)))
        valor_dor_txt.value = f"{dor_atual}/10"
        page.update()

    slider_dor = ft.Slider(
        min=0,
        max=10,
        divisions=10,
        value=dor_atual,
        label="{value}",
        active_color=PRIMARY,
        inactive_color=CARD_BORDER,
        on_change=atualizar_dor_ui,
    )

    dropdown_resultado = ft.Dropdown(
        label="Resultado do teste",
        value=resultado_selecionado["valor"],
        options=[
            ft.dropdown.Option("Positivo"),
            ft.dropdown.Option("Negativo"),
            ft.dropdown.Option("Não realizado"),
            ft.dropdown.Option("Inconclusivo"),
        ],
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
        on_change=lambda event: resultado_selecionado.update(
            {"valor": event.control.value}
        ),
    )

    # Dropdown nativo substitui o SegmentedButton, que causava a exceção
    # observada na gravação de tela em Flet 1.0.4.
    dropdown_lado = ft.Dropdown(
        label="Lado testado",
        value=lado_selecionado["valor"],
        options=[
            ft.dropdown.Option("Direito"),
            ft.dropdown.Option("Esquerdo"),
            ft.dropdown.Option("Bilateral"),
        ],
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
        on_change=lambda event: lado_selecionado.update(
            {"valor": event.control.value}
        ),
    )

    txt_obs = ft.TextField(
        value=resultado_salvo.get("observacoes", ""),
        label="Observações",
        hint_text="Registre somente observações relevantes à avaliação.",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        text_size=14,
    )

    def fechar_dialogo(dialog):
        dialog.open = False
        page.update()

    def abrir_ficha_clinica(_):
        dlg = ft.AlertDialog(
            title=ft.Text(f"Ficha clínica: {teste.get('nome', 'Teste')}"),
            content=ft.Column(
                [
                    ft.Text(
                        f"{teste.get('regiao', '')} • {teste.get('estrutura', '')}",
                        weight=ft.FontWeight.BOLD,
                        color=PRIMARY,
                    ),
                    ft.Text("Definição", weight=ft.FontWeight.BOLD),
                    ft.Text(teste.get("definicao") or "Não informada.", size=13),
                    ft.Text("Objetivo", weight=ft.FontWeight.BOLD),
                    ft.Text(teste.get("objetivo") or "Não informado.", size=13),
                    ft.Text("Como é feito", weight=ft.FontWeight.BOLD),
                    ft.Text(teste.get("como_fazer") or "Não informado.", size=13),
                    ft.Text("Resultado positivo", weight=ft.FontWeight.BOLD),
                    ft.Text(teste.get("positivo_se") or "Não informado.", size=13),
                    ft.Text(
                        "Material acadêmico. A aplicação dos testes deve ser feita "
                        "por profissional capacitado, com consentimento e respeitando "
                        "a tolerância do participante. O resultado isolado não confirma diagnóstico.",
                        size=11,
                        color=TEXT_SECONDARY,
                    ),
                ],
                tight=True,
                spacing=7,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda _: fechar_dialogo(dlg))
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def salvar_e_proximo(_):
        feedback_msg.visible = False
        avaliacao = sessao.get("avaliacao_atual")
        if not avaliacao or not avaliacao.get("id"):
            feedback_msg.value = "Não existe avaliação ativa nesta sessão."
            feedback_msg.visible = True
            page.update()
            return

        payload = {
            "teste_id": int(teste["id"]),
            "lado": lado_selecionado["valor"],
            "resultado": resultado_selecionado["valor"],
            "dor_0_10": dor_atual,
            "observacoes": (txt_obs.value or "").strip() or None,
        }
        sucesso, mensagem = salvar_resultado_teste_api(str(avaliacao["id"]), payload)
        if sucesso:
            sessao["resultado_atual"] = None
            navegar("selecao")
            return
        feedback_msg.value = mensagem
        feedback_msg.visible = True
        page.update()

    def confirmar_exclusao(_):
        def executar_exclusao(_):
            fechar_dialogo(dlg)
            avaliacao = sessao.get("avaliacao_atual") or {}
            sucesso, mensagem = excluir_resultado_teste_api(
                str(avaliacao.get("id", "")), int(teste["id"])
            )
            if sucesso:
                sessao["resultado_atual"] = None
                navegar("selecao")
                return
            feedback_msg.value = mensagem
            feedback_msg.visible = True
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Excluir resultado?"),
            content=ft.Text(
                "O resultado deste teste será removido da avaliação. "
                "Esta ação não pode ser desfeita."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: fechar_dialogo(dlg)),
                ft.FilledButton(
                    "Excluir",
                    bgcolor=ft.Colors.ERROR,
                    color=ft.Colors.WHITE,
                    on_click=executar_exclusao,
                ),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    cabecalho = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=TEXT_PRIMARY,
                on_click=lambda _: navegar("selecao"),
            ),
            ft.Text(
                teste.get("nome", "Teste"),
                size=18,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                expand=True,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.IconButton(
                icon=ft.Icons.HELP_OUTLINE,
                icon_color=TEXT_PRIMARY,
                tooltip="Ficha clínica",
                on_click=abrir_ficha_clinica,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    subtitulo = ft.Text(
        f"{teste.get('regiao', 'Geral')} • {teste.get('estrutura', 'Estrutura não informada')}",
        size=13,
        color=TEXT_SECONDARY,
        text_align=ft.TextAlign.CENTER,
    )

    ficha_resumo = ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(width=1, color=CARD_BORDER),
        border_radius=12,
        padding=12,
        content=ft.Column(
            [
                ft.Text("Objetivo", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Text(teste.get("objetivo") or "Consulte a ficha clínica.", size=13),
                ft.Text("Critério de resultado positivo", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Text(teste.get("positivo_se") or "Consulte a ficha clínica.", size=13),
            ],
            spacing=5,
        ),
    )

    rodape_acoes = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=ft.Colors.ERROR,
                tooltip="Excluir resultado",
                visible=bool(resultado_salvo),
                on_click=confirmar_exclusao,
            ),
            ft.Row(
                [
                    ft.TextButton(
                        "Voltar",
                        style=ft.ButtonStyle(color=TEXT_SECONDARY),
                        on_click=lambda _: navegar("selecao"),
                    ),
                    ft.FilledButton(
                        "Salvar resultado",
                        icon=ft.Icons.SAVE,
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        on_click=salvar_e_proximo,
                    ),
                ],
                spacing=8,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    page.add(
        cabecalho,
        ft.Container(content=subtitulo, alignment=ft.Alignment(0, 0)),
        ficha_resumo,
        feedback_msg,
        ft.Divider(height=8, color="transparent"),
        dropdown_lado,
        dropdown_resultado,
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Dor durante o teste", weight=ft.FontWeight.BOLD),
                        valor_dor_txt,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                slider_dor,
            ],
            spacing=4,
        ),
        txt_obs,
        ft.TextButton("Consultar ficha clínica completa", icon=ft.Icons.HELP_OUTLINE, on_click=abrir_ficha_clinica),
        ft.Divider(height=8, color="transparent"),
        rodape_acoes,
    )
