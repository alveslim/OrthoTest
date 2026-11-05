import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY
from estado import buscar_kpis_dashboard

def render_dashboard(page: ft.Page, navegar):
    # ---------------------------------------------------------
    # 1. BUSCA DE DADOS
    # ---------------------------------------------------------
    sucesso, dados = buscar_kpis_dashboard()
    
    if not sucesso:
        page.add(ft.Text(f"Erro: {dados}", color=ft.Colors.ERROR))
        page.add(ft.ElevatedButton("Voltar", on_click=lambda _: navegar("participantes")))
        return

    # ---------------------------------------------------------
    # 2. CARTÕES DE KPI
    # ---------------------------------------------------------
    def criar_cartao_kpi(titulo, valor, cor_texto=PRIMARY):
        return ft.Card(
            elevation=2,
            content=ft.Container(
                padding=15,
                width=160,
                content=ft.Column([
                    ft.Text(titulo, size=12, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                    ft.Text(str(valor), size=24, color=cor_texto, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

    linha_kpis = ft.Row([
        criar_cartao_kpi("Participantes", dados.get("participantes_avaliados", 0)),
        criar_cartao_kpi("Concluídas", f"{dados.get('percentual_avaliacoes_completas', 0)}%"),
        criar_cartao_kpi("Dor Média", f"{dados.get('dor_media_geral', 0)}/10", cor_texto=ft.Colors.RED_400),
    ], alignment=ft.MainAxisAlignment.SPACE_EVENLY, wrap=True)

    # ---------------------------------------------------------
    # 3. GRÁFICO DE BARRAS NATIVO (À prova de quebras de versão)
    # ---------------------------------------------------------
    # AULA: Construímos o gráfico manualmente usando contentores. 
    # A altura máxima da área do gráfico será de 150 pixels.
    ALTURA_MAX_GRAFICO = 150 
    barras_ui = []
    
    lista_regioes = dados.get("positividade_por_regiao", [])
    
    for item in lista_regioes:
        valor_y = float(item["percentual_positivo"])
        nome_regiao = str(item["regiao"])
        
        # Regra de 3 simples para calcular a altura em pixels (0 a 100%)
        altura_pixels = (valor_y / 100.0) * ALTURA_MAX_GRAFICO
        
        # Garantir um mínimo de 5 pixels para que valores pequenos como 1% fiquem visíveis
        if valor_y > 0 and altura_pixels < 5:
            altura_pixels = 5
            
        # Desenhamos uma coluna que contém: [Percentagem] -> [Barra Colorida] -> [Nome da Região]
        coluna_grafico = ft.Column(
            controls=[
                ft.Text(f"{valor_y}%", size=10, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Container(
                    width=40,
                    height=altura_pixels,
                    bgcolor=PRIMARY,
                    border_radius=ft.BorderRadius.vertical(top=4, bottom=0), # Arredonda só em cima
                    tooltip=f"{nome_regiao}: {valor_y}%"
                ),
                ft.Text(nome_regiao[:10], size=10, color=TEXT_SECONDARY)
            ],
            alignment=ft.MainAxisAlignment.END, # Empurra tudo para a base da linha
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4
        )
        barras_ui.append(coluna_grafico)

    # Envolvemos todas as colunas dentro de uma Row principal que serve como o fundo do gráfico
    grafico_barras = ft.Container(
        content=ft.Row(barras_ui, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END),
        height=ALTURA_MAX_GRAFICO + 50, # Espaço extra para caber os textos
        padding=10,
        bgcolor=SURFACE,
        border_radius=8,
        border=ft.Border.all(1, CARD_BORDER)
    )

    # ---------------------------------------------------------
    # 4. NOTA DE PRIVACIDADE
    # ---------------------------------------------------------
    nota_privacidade = ft.Text(
        "Nota: Grupos com menos de 3 resultados (n<3) são agregados em 'Outros' para garantir o K-Anonimato e proteger a privacidade individual.",
        size=11, color=TEXT_SECONDARY, italic=True, text_align=ft.TextAlign.CENTER
    )

    # ---------------------------------------------------------
    # 5. MONTAGEM FINAL DO ECRÃ
    # ---------------------------------------------------------
    page.add(
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: navegar("participantes")),
            ft.Text("Dashboard Clínico", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        ]),
        ft.Divider(color="transparent"),
        linha_kpis,
        ft.Divider(height=20, color="transparent"),
        ft.Text("Taxa de Positividade por Região (%)", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        grafico_barras,
        ft.Divider(height=10, color="transparent"),
        nota_privacidade
    )