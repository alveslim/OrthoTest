import flet as ft
from theme import PRIMARY, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, CARD_BORDER
from estado import sessao, solicitar_resumo_ia, aprovar_resumo_ia_api

def render_resumo_ia(page: ft.Page, navegar):
    avaliacao_atual = sessao.get("avaliacao_atual")
    if not avaliacao_atual:
        page.snack_bar = ft.SnackBar(ft.Text("Erro: Nenhuma avaliação ativa."), bgcolor=ft.Colors.ERROR)
        page.snack_bar.open = True
        navegar("participantes")
        return

    avaliacao_id = str(avaliacao_atual["id"])

    # ---------------------------------------------------------
    # COMPONENTES VISUAIS (ORT-33)
    # ---------------------------------------------------------
    
    # AULA: O Aviso Legal amarelo e gritante garante que o utilizador 
    # não confunde isto com um diagnóstico médico validado.
    aviso_legal = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_900),
            ft.Text(
                "ATENÇÃO: O texto abaixo é um rascunho gerado por IA para revisão humana. Não constitui diagnóstico médico nem substitui o raciocínio clínico.", 
                color=ft.Colors.AMBER_900, weight=ft.FontWeight.BOLD, size=12, expand=True
            )
        ]),
        bgcolor=ft.Colors.AMBER_100, padding=10, border_radius=8, border=ft.border.all(1, ft.Colors.AMBER_300)
    )

    # AULA: A caixa de texto é multiline (permite parágrafos) e é EDITÁVEL. 
    # O humano tem o poder de alterar o texto antes de aprovar[cite: 9].
    caixa_texto = ft.TextField(
        multiline=True,
        min_lines=12,
        max_lines=20,
        expand=True,
        label="Rascunho Clínico (Editável pelo profissional)",
        text_size=14,
        border_color=PRIMARY
    )

    indicador_estado = ft.Text(visible=False, size=12, italic=True)\n    pode_aprovar = sessao.get("papel") == "professor"\n    texto_permissao = ft.Text(\n        "Somente um usuário com papel de professor pode aprovar e registrar o resumo. Você pode gerar e revisar o rascunho.",\n        size=11, color=TEXT_SECONDARY, visible=not pode_aprovar\n    )

    # ---------------------------------------------------------
    # AÇÕES DOS BOTÕES
    # ---------------------------------------------------------
    def gerar_clique(e):
        # Bloqueia o botão enquanto a IA "pensa"
        btn_gerar.disabled = True
        btn_gerar.text = "A analisar achados..."
        indicador_estado.visible = False
        page.update()
        
        sucesso, resumo, aviso = solicitar_resumo_ia(avaliacao_id)
        
        # Injeta a resposta da IA na caixa de texto
        caixa_texto.value = resumo
        
        # AULA: Cumprimos o critério de renomear a ação explicitamente[cite: 9].
        btn_gerar.text = "Regerar resumo para discussão"
        btn_gerar.disabled = False
        
        if sucesso:
            indicador_estado.value = f"Status: {aviso} - Aguardando sua revisão."
            indicador_estado.color = ft.Colors.GREEN_700
            btn_aprovar.disabled = False # Só permitimos aprovar DEPOIS de gerar algo
        else:
            indicador_estado.value = "Falha ao contactar servidor de IA."
            indicador_estado.color = ft.Colors.ERROR
        
        indicador_estado.visible = True
        page.update()

    def aprovar_clique(e):
        # AULA: Bloqueamos a interface para evitar duplo clique
        btn_aprovar.disabled = True
        btn_aprovar.text = "A registar auditoria..."
        page.update()
        
        # Extraímos o texto que o utilizador eventualmente alterou na caixa de texto
        texto_revisado = caixa_texto.value
        
        sucesso, msg = aprovar_resumo_ia_api(avaliacao_id, texto_revisado)
        
        page.snack_bar = ft.SnackBar(
            ft.Text(msg), 
            bgcolor=ft.colors.GREEN_800 if sucesso else ft.colors.ERROR
        )
        page.snack_bar.open = True
        
        if sucesso:
            navegar("participantes")
        else:
            # Se falhar, devolvemos o botão ao estado normal para ele tentar novamente
            btn_aprovar.disabled = False
            btn_aprovar.text = "Aprovar Resumo Final"
            page.update()

    # AULA: Botão renomeado conforme exigido no requisito[cite: 9]. Sem a palavra "Diagnóstico".
    btn_gerar = ft.ElevatedButton("Gerar resumo para discussão", on_click=gerar_clique, icon=ft.Icons.AUTO_AWESOME, bgcolor=PRIMARY, color="white")
    
    # Botão de aprovação fica bloqueado até o rascunho existir[cite: 9].
    btn_aprovar = ft.FilledButton("Aprovar Resumo Final", on_click=aprovar_clique, icon=ft.Icons.CHECK_CIRCLE, disabled=True or not pode_aprovar, bgcolor=ft.Colors.GREEN_600)

    # ---------------------------------------------------------
    # MONTAGEM FINAL DO ECRÃ
    # ---------------------------------------------------------
    page.add(
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navegar("participantes")),
            ft.Text("Assistente de Revisão (IA)", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        ]),
        ft.Divider(color="transparent"),
        aviso_legal,
        ft.Divider(height=10, color="transparent"),
        ft.Row([btn_gerar, indicador_estado], alignment=ft.MainAxisAlignment.START),
        ft.Container(content=caixa_texto, padding=ft.padding.only(top=15, bottom=15), expand=True),
        texto_permissao,\n        ft.Row([btn_aprovar], alignment=ft.MainAxisAlignment.END)
    )