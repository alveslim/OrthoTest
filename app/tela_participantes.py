import flet as ft
from theme import PRIMARY, SURFACE, CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, REVIEW_TEXT
from estado import (
    sessao,
    buscar_participantes_e_avaliacoes,
    criar_novo_participante,
    garantir_avaliacao_ativa,
)

def render_participantes(page: ft.Page, navegar):
    lista_container = ft.Column(spacing=12)
    mensagem_feedback = ft.Text("", color=REVIEW_TEXT, size=13, visible=False)
    filtro_codigo = ft.TextField(
        hint_text="Buscar por código (ex.: P-014)",
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
        on_change=lambda _: atualizar_lista(),
    )

    dados_carregados = []

    def abrir_participante(participante: dict):
        sucesso, resultado = garantir_avaliacao_ativa(participante["id"], participante.get("avaliacao"))
        if not sucesso:
            mensagem_feedback.value = str(resultado)
            mensagem_feedback.visible = True
            page.update()
            return

        sessao["participante_atual"] = participante
        sessao["avaliacao_atual"] = resultado
        navegar("selecao")

    def montar_card(p: dict) -> ft.Container:
        aval = p.get("avaliacao")
        if not aval:
            status_txt = "Sem avaliação"
            progresso_txt = "0% concluído"
        else:
            status_map = {
                "pendente": "Incompleto",
                "em_andamento": "Em andamento",
                "concluido": "Completo",
            }
            status_txt = status_map.get(aval.get("status", "pendente"), "Incompleto")
            perc = aval.get("progresso_percentual", 0.0)
            progresso_txt = f"{perc:.0f}% concluído"

        peso_str = f"{p['peso_kg']} kg" if p.get("peso_kg") else "-- kg"
        altura_str = f"{p['altura_m']} m" if p.get("altura_m") else "-- m"

        return ft.Container(
            bgcolor=SURFACE,
            border=ft.Border.all(width=1, color=CARD_BORDER),
            border_radius=16,
            padding=16,
            on_click=lambda _: abrir_participante(p),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(p["codigo"], theme_style=ft.TextThemeStyle.TITLE_LARGE),
                            ft.Text(status_txt, size=12, color=PRIMARY, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f"{p['idade']} anos · {peso_str} · {altura_str}",
                        theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                        color=TEXT_SECONDARY,
                    ),
                    ft.Text(
                        progresso_txt,
                        theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                        color=PRIMARY,
                    ),
                ],
                spacing=4,
            ),
        )

    def atualizar_lista():
        lista_container.controls.clear()
        termo = (filtro_codigo.value or "").strip().upper()
        filtrados = [
            p for p in dados_carregados
            if termo in p.get("codigo", "").upper()
        ]

        if not filtrados:
            lista_container.controls.append(
                ft.Text("Nenhum participante encontrado.", color=TEXT_SECONDARY, size=14)
            )
        else:
            for item in filtrados:
                lista_container.controls.append(montar_card(item))
        page.update()

    def carregar_do_servidor():
        mensagem_feedback.visible = False
        sucesso, resposta = buscar_participantes_e_avaliacoes()
        if not sucesso:
            mensagem_feedback.value = str(resposta)
            mensagem_feedback.visible = True
            page.update()
            return
        nonlocal dados_carregados
        dados_carregados = resposta
        atualizar_lista()

    # ==========================================
    # FORMULÁRIO DE NOVO PARTICIPANTE
    # ==========================================
    form_visivel = ft.Container(visible=False)

    codigo_in = ft.TextField(label="Código (ex.: P-015 — nunca use nome)", border_color=CARD_BORDER, bgcolor=SURFACE)
    idade_in = ft.TextField(label="Idade (anos)", keyboard_type=ft.KeyboardType.NUMBER, border_color=CARD_BORDER, bgcolor=SURFACE)
    peso_in = ft.TextField(label="Peso em kg (ex.: 68.5)", keyboard_type=ft.KeyboardType.NUMBER, border_color=CARD_BORDER, bgcolor=SURFACE)
    altura_in = ft.TextField(label="Altura em metros (ex.: 1.72)", keyboard_type=ft.KeyboardType.NUMBER, border_color=CARD_BORDER, bgcolor=SURFACE)
    erro_form = ft.Text("", color=REVIEW_TEXT, size=12, visible=False)

    def alternar_formulario(e):
        form_visivel.visible = not form_visivel.visible
        erro_form.visible = False
        page.update()

    def salvar_participante(e):
        erro_form.visible = False
        cod = (codigo_in.value or "").strip()

        if not cod or len(cod) > 20 or " " in cod:
            erro_form.value = "Informe um código válido sem espaços (ex.: P-015). Não insira nomes."
            erro_form.visible = True
            page.update()
            return

        try:
            idade_val = int(idade_in.value)
            if not (0 < idade_val < 120):
                raise ValueError()
        except Exception:
            erro_form.value = "A idade deve ser um número inteiro entre 1 e 119."
            erro_form.visible = True
            page.update()
            return

        try:
            peso_val = float(peso_in.value.replace(",", ".")) if peso_in.value else None
            if peso_val is not None and not (0 < peso_val < 400):
                raise ValueError()
        except Exception:
            erro_form.value = "Peso inválido (informe um valor positivo em kg, ex.: 70.5)."
            erro_form.visible = True
            page.update()
            return

        try:
            altura_val = float(altura_in.value.replace(",", ".")) if altura_in.value else None
            if altura_val is not None and not (0.5 <= altura_val <= 2.5):
                raise ValueError()
        except Exception:
            erro_form.value = "Altura inválida (informe em metros entre 0.50 e 2.50, ex.: 1.75)."
            erro_form.visible = True
            page.update()
            return

        sucesso, resp = criar_novo_participante(cod, idade_val, peso_val, altura_val)
        if not sucesso:
            erro_form.value = str(resp)
            erro_form.visible = True
            page.update()
            return

        # Limpa campos, fecha o formulário e recarrega do banco
        codigo_in.value = ""
        idade_in.value = ""
        peso_in.value = ""
        altura_in.value = ""
        form_visivel.visible = False
        carregar_do_servidor()

    form_visivel.content = ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(width=1, color=CARD_BORDER),
        border_radius=16,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Text("Novo Participante", theme_style=ft.TextThemeStyle.TITLE_LARGE),
                codigo_in,
                idade_in,
                peso_in,
                altura_in,
                erro_form,
                ft.Row(
                    controls=[
                        ft.TextButton("Cancelar", on_click=alternar_formulario),
                        ft.Button(
                            content=ft.Text("Salvar", weight=ft.FontWeight.BOLD),
                            bgcolor=PRIMARY,
                            color="white",
                            on_click=salvar_participante,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=10,
        ),
    )

    cabecalho = ft.Row(
        controls=[
            ft.Text("Participantes", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.IconButton(icon="logout", icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("login")),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    page.add(
        cabecalho,
        filtro_codigo,
        mensagem_feedback,
        ft.Button(
            content=ft.Text("+ Novo participante", weight=ft.FontWeight.BOLD),
            bgcolor=PRIMARY,
            color="white",
            width=350,
            on_click=alternar_formulario,
        ),
        form_visivel,
        ft.Divider(height=10, color="transparent"),
        lista_container,
    )

    carregar_do_servidor()