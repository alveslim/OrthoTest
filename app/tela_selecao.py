import flet as ft
from theme import (
    PRIMARY,
    SURFACE,
    CARD_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING_BACKGROUND,
    WARNING_TEXT,
    REVIEW_TEXT,
)
from estado import sessao, buscar_catalogo_e_resultados, sinalizar_avaliacao_professor


def render_selecao(page: ft.Page, navegar):
    participante = sessao.get("participante_atual") or {"codigo": "P-000", "idade": 20, "peso_kg": 70, "altura_m": 1.70}
    avaliacao = sessao.get("avaliacao_atual") or {"id": ""}

    regiao_selecionada = {"valor": "Todas"}
    dados_estado = {"catalogo": [], "mapa_resultados": {}}

    coluna_regioes_resumo = ft.Column(spacing=8)
    coluna_testes = ft.Column(spacing=10)
    texto_progresso = ft.Text("Carregando progresso...", size=14, weight=ft.FontWeight.BOLD, color=PRIMARY)
    barra_progresso = ft.ProgressBar(value=0, color=PRIMARY, bgcolor=CARD_BORDER, height=8, border_radius=4)
    feedback_msg = ft.Text("", size=12, color=REVIEW_TEXT, visible=False)

    # Cálculo simples de IMC para o cabeçalho (igual ao PDF)
    peso = participante.get("peso_kg")
    altura = participante.get("altura_m")
    imc_str = f" · IMC {peso / (altura ** 2):.1f}" if (peso and altura and altura > 0) else ""

    def abrir_teste(teste_item: dict):
        sessao["teste_atual"] = teste_item
        sessao["resultado_atual"] = dados_estado["mapa_resultados"].get(int(teste_item["id"]))
        navegar("teste")

    def selecionar_regiao(nome_regiao: str):
        regiao_selecionada["valor"] = nome_regiao
        atualizar_interface()

    def montar_badge_estado(res_obj: dict | None) -> ft.Container:
        """Separa visualmente: Pendente vs Não realizado vs Resultado registrado."""
        if not res_obj or not res_obj.get("resultado"):
            return ft.Container(
                bgcolor=CARD_BORDER,
                border_radius=8,
                padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                content=ft.Text("Pendente", size=11, color=TEXT_SECONDARY, weight=ft.FontWeight.BOLD),
            )

        valor_res = res_obj["resultado"]
        lado_res = res_obj.get("lado", "")

        if valor_res == "Não realizado":
            return ft.Container(
                bgcolor=WARNING_BACKGROUND,
                border_radius=8,
                padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                content=ft.Text("Não realizado", size=11, color=WARNING_TEXT, weight=ft.FontWeight.BOLD),
            )

        # Resultado efetivamente registrado (Positivo, Negativo ou Inconclusivo)
        return ft.Container(
            bgcolor="#E6F4EA" if valor_res == "Negativo" else "#E8F0FE",
            border_radius=8,
            padding=ft.Padding(left=10, top=4, right=10, bottom=4),
            content=ft.Text(
                f"Registrado: {valor_res} ({lado_res})",
                size=11,
                color=PRIMARY,
                weight=ft.FontWeight.BOLD,
            ),
        )

    def atualizar_interface():
        catalogo = dados_estado["catalogo"]
        mapa_res = dados_estado["mapa_resultados"]

        total = len(catalogo)
        respondidos = sum(
            1 for t in catalogo
            if int(t["id"]) in mapa_res and mapa_res[int(t["id"])].get("resultado") is not None
        )
        perc = (respondidos / total) if total > 0 else 0.0

        texto_progresso.value = f"{respondidos} de {total} testes ({perc * 100:.0f}%)"
        barra_progresso.value = perc

        # Agrupar por região
        regioes_dict: dict[str, list[dict]] = {}
        for t in catalogo:
            reg = t.get("regiao", "Geral")
            regioes_dict.setdefault(reg, []).append(t)

        # Botões de navegação entre regiões
        coluna_regioes_resumo.controls.clear()
        botoes_filtro = [
            ft.TextButton(
                "Todas",
                on_click=lambda _: selecionar_regiao("Todas"),
                style=ft.ButtonStyle(color=PRIMARY if regiao_selecionada["valor"] == "Todas" else TEXT_SECONDARY),
            )
        ]

        for nome_reg, lista_t in regioes_dict.items():
            resp_reg = sum(1 for item in lista_t if int(item["id"]) in mapa_res)
            botoes_filtro.append(
                ft.TextButton(
                    f"{nome_reg} ({resp_reg}/{len(lista_t)})",
                    on_click=lambda _, r=nome_reg: selecionar_regiao(r),
                    style=ft.ButtonStyle(color=PRIMARY if regiao_selecionada["valor"] == r else TEXT_SECONDARY),
                )
            )

        coluna_regioes_resumo.controls.append(ft.Row(controls=botoes_filtro, wrap=True, spacing=4))

        # Lista de cards de testes da região selecionada
        coluna_testes.controls.clear()
        reg_atual = regiao_selecionada["valor"]
        testes_visiveis = catalogo if reg_atual == "Todas" else regioes_dict.get(reg_atual, [])

        if not testes_visiveis:
            coluna_testes.controls.append(
                ft.Text("Nenhum teste encontrado no catálogo.", color=TEXT_SECONDARY, size=13)
            )
        else:
            for t in testes_visiveis:
                res_salvo = mapa_res.get(int(t["id"]))
                coluna_testes.controls.append(
                    ft.Container(
                        bgcolor=SURFACE,
                        border=ft.Border.all(width=1, color=PRIMARY if res_salvo else CARD_BORDER),
                        border_radius=12,
                        padding=14,
                        on_click=lambda _, item=t: abrir_teste(item),
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(t["nome"], weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, size=15),
                                        ft.Text(
                                            f"{t.get('regiao', '')} • {t.get('estrutura', '')}",
                                            color=TEXT_SECONDARY,
                                            size=12,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                montar_badge_estado(res_salvo),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    )
                )

        page.update()

    def carregar_dados():
        feedback_msg.visible = False
        sucesso, resp = buscar_catalogo_e_resultados(str(avaliacao["id"]))
        if not sucesso:
            feedback_msg.value = str(resp)
            feedback_msg.visible = True
            page.update()
            return
        dados_estado["catalogo"] = resp["catalogo"]
        dados_estado["mapa_resultados"] = resp["mapa_resultados"]
        atualizar_interface()

    # Sinalizar ao professor (ORT-15 integrada na tela de seleção conforme PDF)
    motivo_input = ft.TextField(
        hint_text="Motivo para revisão do professor (opcional)",
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        text_size=13,
    )

    def acao_sinalizar(e):
        ok, msg = sinalizar_avaliacao_professor(str(avaliacao["id"]), motivo_input.value or "")
        feedback_msg.value = msg
        feedback_msg.color = PRIMARY if ok else REVIEW_TEXT
        feedback_msg.visible = True
        page.update()

    cabecalho = ft.Row(
        controls=[
            ft.IconButton(icon="arrow_back_ios", icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("participantes")),
            ft.Text(
                f"Avaliação • {participante['codigo']}",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                expand=True,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.IconButton(icon="refresh", icon_color=TEXT_PRIMARY, tooltip="Atualizar", on_click=lambda _: carregar_dados()),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    info_participante = ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(width=1, color=CARD_BORDER),
        border_radius=12,
        padding=12,
        content=ft.Column(
            controls=[
                ft.Text(
                    f"{participante['idade']} anos · {peso or '--'} kg · {altura or '--'} m{imc_str}",
                    size=13,
                    color=TEXT_SECONDARY,
                ),
                ft.Text("Consentimento registrado", size=12, color=PRIMARY, weight=ft.FontWeight.W_500),
                texto_progresso,
                barra_progresso,
            ],
            spacing=6,
        ),
    )

    page.add(
        cabecalho,
        info_participante,
        feedback_msg,
        ft.Text("Regiões", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        coluna_regioes_resumo,
        coluna_testes,
        ft.Divider(height=15, color="transparent"),
        motivo_input,
        ft.Button(
            content=ft.Text("Sinalizar ao professor", weight=ft.FontWeight.BOLD),
            bgcolor=SURFACE,
            color=PRIMARY,
            width=350,
            on_click=acao_sinalizar,
        ),
    )

    carregar_dados()