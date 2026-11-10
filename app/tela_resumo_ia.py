import flet as ft

from estado import aprovar_resumo_ia_api, salvar_rascunho_ia_api, sessao, solicitar_resumo_ia
from theme import (
    CARD_BORDER, PRIMARY, REVIEW_TEXT, SURFACE, TEXT_PRIMARY, WARNING_BACKGROUND, WARNING_TEXT,
)


def render_resumo_ia(page: ft.Page, navegar):
    """Painel do assistente de IA (ORT-33): só gera RASCUNHO; nunca diagnostica."""
    avaliacao = sessao.get("avaliacao_atual")
    if not avaliacao:
        sessao["aviso_selecao"] = "Abra um participante para gerar o resumo da avaliação."
        navegar("participantes")
        return

    avaliacao_id = str(avaliacao["id"])
    eh_professor = sessao.get("papel") == "professor"

    aviso_legal = ft.Container(
        content=ft.Text(
            "ATENÇÃO: o texto abaixo é um rascunho gerado para discussão e revisão humana. "
            "Não constitui diagnóstico nem substitui o raciocínio clínico.",
            color=WARNING_TEXT, weight=ft.FontWeight.BOLD, size=12,
        ),
        bgcolor=WARNING_BACKGROUND, padding=12, border_radius=8,
    )
    caixa_texto = ft.TextField(
        multiline=True, min_lines=10, max_lines=18,
        label="Rascunho (editável antes de salvar ou aprovar)", text_size=14,
        border_color=PRIMARY, bgcolor=SURFACE,
    )
    estado_txt = ft.Text("", size=12, visible=False)

    botao_gerar = ft.Button(content=ft.Text("Gerar resumo para discussão", weight=ft.FontWeight.BOLD),
                            bgcolor=PRIMARY, color="white", height=48)
    botao_salvar = ft.Button(content=ft.Text("Salvar rascunho"), height=48, disabled=True)
    botao_aprovar = ft.Button(
        content=ft.Text("Aprovar (professor)", weight=ft.FontWeight.BOLD), bgcolor=PRIMARY, color="white",
        height=48, disabled=True, visible=eh_professor,
    )

    def mostrar(msg: str, ok: bool):
        estado_txt.value = msg
        estado_txt.color = PRIMARY if ok else REVIEW_TEXT
        estado_txt.visible = True
        page.update()

    def definir_texto_botao(botao: ft.Button, texto: str):
        botao.content = ft.Text(texto, weight=ft.FontWeight.BOLD)

    def gerar(_):
        botao_gerar.disabled = True
        definir_texto_botao(botao_gerar, "Gerando...")
        page.update()
        ok, resumo, aviso = solicitar_resumo_ia(avaliacao_id)
        botao_gerar.disabled = False
        definir_texto_botao(botao_gerar, "Gerar novamente")
        if ok:
            caixa_texto.value = resumo
            botao_salvar.disabled = False
            botao_aprovar.disabled = False
            mostrar(f"{aviso} Revise o texto antes de salvar.", True)
        else:
            mostrar(resumo or "Não foi possível gerar o resumo.", False)

    def salvar(_):
        if not (caixa_texto.value or "").strip():
            return mostrar("O texto não pode estar vazio.", False)
        ok, msg = salvar_rascunho_ia_api(avaliacao_id, caixa_texto.value)
        mostrar(msg, ok)

    def aprovar(_):
        if not (caixa_texto.value or "").strip():
            return mostrar("O texto não pode estar vazio.", False)
        ok, msg = aprovar_resumo_ia_api(avaliacao_id, caixa_texto.value)
        mostrar(msg, ok)

    botao_gerar.on_click = gerar
    botao_salvar.on_click = salvar
    botao_aprovar.on_click = aprovar

    page.add(
        ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("selecao")),
            ft.Text("Assistente de revisão (IA)", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ]),
        aviso_legal,
        botao_gerar,
        estado_txt,
        caixa_texto,
        ft.Row([botao_salvar, botao_aprovar], wrap=True, spacing=8),
    )
