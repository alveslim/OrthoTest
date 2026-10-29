import flet as ft
import requests
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, REVIEW_TEXT
from estado import sessao, API_BASE_URL, _headers_autenticados

def render_teste(page: ft.Page, navegar):
    # Carrega os dados do teste selecionado na tela anterior (ORT-20)
    teste = sessao.get("teste_atual") or {
        "id": 1, "nome": "Teste", "regiao": "Região", "estrutura": "Estrutura", "como_fazer": "Instruções não disponíveis."
    }
    
    # Se já houver um resultado salvo para este teste, preenche os campos
    resultado_salvo = sessao.get("resultado_atual") or {}

    # Estados locais do formulário
    lado_selecionado = {"valor": resultado_salvo.get("lado", "Direito")}
    resultado_selecionado = {"valor": resultado_salvo.get("resultado", "Não realizado")}
    dor_atual = int(resultado_salvo.get("dor_0_10", 0))

    valor_dor_txt = ft.Text(f"{dor_atual}/10", weight=ft.FontWeight.BOLD, size=16, color=PRIMARY)
    
    def atualizar_dor_ui(novo_valor: int):
        global dor_atual
        dor_atual = novo_valor
        valor_dor_txt.value = f"{novo_valor}/10"
        page.update()

    slider_dor = ft.Slider(
        min=0, max=10, divisions=10, value=dor_atual, label="{value}",
        active_color=PRIMARY, inactive_color=CARD_BORDER,
        on_change=lambda e: atualizar_dor_ui(int(e.control.value))
    )

    dropdown_resultado = ft.Dropdown(
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
        on_change=lambda e: (resultado_selecionado.update({"valor": e.control.value}))
    )

    txt_obs = ft.TextField(
        value=resultado_salvo.get("observacoes", ""),
        hint_text="Ex.: dor ao final da tração, clique articular...",
        multiline=True, min_lines=2, max_lines=4,
        border_color=CARD_BORDER, bgcolor=SURFACE, text_size=14
    )

    feedback_msg = ft.Text("", size=12, color=REVIEW_TEXT, visible=False)

    # ==========================================
    # MODAL DA FICHA CLÍNICA (BOTÃO DE AJUDA ?)
    # ==========================================
    def abrir_ficha_clinica(e):
        dlg = ft.AlertDialog(
            title=ft.Text(f"Ficha Clínica: {teste['nome']}", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text(f"Região / Estrutura: {teste.get('regiao')} • {teste.get('estrutura')}", weight=ft.FontWeight.BOLD, color=PRIMARY),
                ft.Divider(height=10, color="transparent"),
                ft.Text("Como executar:", weight=ft.FontWeight.BOLD),
                ft.Text(teste.get("como_fazer", "Sem descrição detalhada."), size=13),
                ft.Divider(height=10, color="transparent"),
                ft.Text("Lembrete: Comparar sempre com o lado contralateral. Esta aplicação possui fins exclusivamente académicos.", size=11, color=TEXT_SECONDARY),
            ], tight=True, spacing=5),
            actions=[ft.TextButton("Fechar", on_click=lambda _: fechar_dialogo(dlg))]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def fechar_dialogo(dlg):
        dlg.open = False
        page.update()

    # ==========================================
    # GRAVAÇÃO NA API (POST /resultados)
    # ==========================================
    def salvar_e_proximo(e):
        feedback_msg.visible = False
        avaliacao = sessao.get("avaliacao_atual")
        
        if not avaliacao:
            feedback_msg.value = "Erro: Nenhuma avaliação ativa na sessão."
            feedback_msg.visible = True
            page.update()
            return

        payload = {
            "teste_id": int(teste["id"]),
            "lado": lado_selecionado["valor"],
            "resultado": resultado_selecionado["valor"],
            "dor_0_10": int(slider_dor.value),
            "observacoes": txt_obs.value.strip() or None
        }

        try:
            resp = requests.post(
                f"{API_BASE_URL}/avaliacoes/{avaliacao['id']}/resultados",
                json=payload,
                headers=_headers_autenticados(),
                timeout=10
            )
            if resp.status_code in (200, 201):
                # Voltar à lista de testes (que irá carregar os dados atualizados)
                navegar("selecao")
            else:
                feedback_msg.value = f"Erro ao salvar: {resp.text}"
                feedback_msg.visible = True
                page.update()
        except Exception:
            feedback_msg.value = "Falha de comunicação ao gravar o resultado na API."
            feedback_msg.visible = True
            page.update()

    # SegmentedButton para o Lado
    def mudar_lado(e):
        lado_selecionado["valor"] = e.control.selected.pop() if e.control.selected else "Direito"

    secao_lado = ft.Column([
        ft.Text("Lado testado", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ft.SegmentedButton(
            selected={lado_selecionado["valor"]},
            on_change=mudar_lado,
            segments=[
                ft.Segment(value="Direito", label=ft.Text("Direito")),
                ft.Segment(value="Esquerdo", label=ft.Text("Esquerdo")),
                ft.Segment(value="Bilateral", label=ft.Text("Bilateral")),
            ],
            expand=True
        )
    ])

    cabecalho = ft.Row(
        controls=[
            ft.IconButton(icon="arrow_back_ios", icon_size=18, icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("selecao")),
            ft.Text(teste["nome"], size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon="help_outline", icon_size=22, icon_color=TEXT_PRIMARY, tooltip="Ficha Clínica", on_click=abrir_ficha_clinica),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    subtitulo = ft.Text(f"{teste.get('regiao', 'Geral')} • Estrutura: {teste.get('estrutura', 'N/A')}", size=13, color=TEXT_SECONDARY, text_align=ft.TextAlign.CENTER)

    rodape_acoes = ft.Row(
        controls=[
            ft.TextButton("Voltar", style=ft.ButtonStyle(color=TEXT_SECONDARY), on_click=lambda _: navegar("selecao")),
            ft.Button(
                content=ft.Text("Salvar e próximo >", weight=ft.FontWeight.BOLD),
                bgcolor=PRIMARY, color="white",
                style=ft.ButtonStyle(padding=ft.Padding(left=20, top=12, right=20, bottom=12)),
                on_click=salvar_e_proximo
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    page.add(
        cabecalho,
        ft.Container(content=subtitulo, alignment=ft.Alignment(0, 0), margin=ft.Margin(left=0, top=0, right=0, bottom=10)),
        feedback_msg,
        ft.Divider(height=10, color="transparent"),
        secao_lado,
        ft.Divider(height=15, color="transparent"),
        ft.Column([ft.Text("Resultado", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY), dropdown_resultado]),
        ft.Divider(height=15, color="transparent"),
        ft.Column([ft.Row([ft.Text("Dor durante o teste", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY), valor_dor_txt], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), slider_dor], spacing=4),
        ft.Divider(height=15, color="transparent"),
        ft.Column([ft.Text("Observações", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY), txt_obs]),
        ft.Divider(height=25, color="transparent"),
        rodape_acoes
    )