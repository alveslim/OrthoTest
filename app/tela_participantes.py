import flet as ft

from estado import (
    buscar_participantes_e_avaliacoes,
    codigo_sugerido,
    criar_novo_participante,
    garantir_avaliacao_ativa,
    sessao,
    situacao_rede,
    sincronizar_fila_offline,
)
from termo import DECLARACAO, DECLARACAO_RESPONSAVEL, TITULO, secoes
from theme import (
    CARD_BORDER, PRIMARY, REVIEW_BACKGROUND, REVIEW_TEXT, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY,
    WARNING_BACKGROUND, WARNING_TEXT,
)


def render_participantes(page: ft.Page, navegar):
    eh_professor = sessao.get("papel") == "professor"
    lista_container = ft.Column(spacing=12)
    aviso_anterior = sessao.pop("aviso_selecao", None)
    mensagem_feedback = ft.Text(aviso_anterior or "", color=PRIMARY, size=13, visible=bool(aviso_anterior))
    faixa_situacao = ft.Container(visible=False, border_radius=8, padding=8, content=ft.Text("", size=12))
    filtro_codigo = ft.TextField(
        hint_text="Buscar por código ou nome (ex.: P-014)",
        border_color=CARD_BORDER,
        bgcolor=SURFACE,
        color=TEXT_PRIMARY,
        on_change=lambda _: atualizar_lista(),
    )
    so_sinalizadas = ft.Checkbox(label="Só com revisão solicitada", value=False, visible=eh_professor,
                                 on_change=lambda _: atualizar_lista())

    dados_carregados = []

    def dizer(msg: str, erro: bool = False):
        mensagem_feedback.value = msg
        mensagem_feedback.color = REVIEW_TEXT if erro else PRIMARY
        mensagem_feedback.visible = True
        page.update()

    def abrir_participante(participante: dict):
        sucesso, resultado = garantir_avaliacao_ativa(participante["id"], participante.get("avaliacao"))
        if not sucesso:
            return dizer(str(resultado), erro=True)
        sessao["participante_atual"] = participante
        sessao["avaliacao_atual"] = resultado
        navegar("selecao")

    def nome_completo(p: dict) -> str:
        return " ".join(x for x in (p.get("nome"), p.get("sobrenome")) if x)

    def montar_card(p: dict) -> ft.Container:
        aval = p.get("avaliacao")
        if not aval:
            status_txt = "Sem avaliação"
            progresso_txt = "0% concluído"
        else:
            status_map = {"pendente": "Incompleto", "em_andamento": "Em andamento", "concluido": "Completo"}
            status_txt = status_map.get(aval.get("status", "pendente"), "Incompleto")
            progresso_txt = f"{aval.get('progresso_percentual', 0.0):.0f}% concluído"

        peso_str = f"{p['peso_kg']} kg" if p.get("peso_kg") else "-- kg"
        altura_str = f"{p['altura_m']} m" if p.get("altura_m") else "-- m"
        nome = nome_completo(p)

        linhas = [
            ft.Row(
                controls=[
                    ft.Text(p["codigo"], theme_style=ft.TextThemeStyle.TITLE_LARGE),
                    ft.Text(status_txt, size=12, color=PRIMARY, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ]
        if nome:
            linhas.append(ft.Text(nome, size=14, color=TEXT_PRIMARY))
        linhas += [
            ft.Text(f"{p['idade']} anos · {peso_str} · {altura_str}",
                    theme_style=ft.TextThemeStyle.BODY_MEDIUM, color=TEXT_SECONDARY),
            ft.Text(progresso_txt, theme_style=ft.TextThemeStyle.BODY_MEDIUM, color=PRIMARY),
        ]
        if p.get("pendente") or (aval or {}).get("pendente"):
            linhas.append(ft.Text("Aguardando envio (guardado neste aparelho)", size=12, color=WARNING_TEXT,
                                  weight=ft.FontWeight.BOLD))
        if (aval or {}).get("flag_professor"):
            motivo = (aval.get("flag_motivo") or "").strip()
            linhas.append(ft.Container(
                bgcolor=REVIEW_BACKGROUND, border_radius=8, padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                content=ft.Text("Revisão solicitada" + (f": {motivo}" if motivo else ""), size=12, color=REVIEW_TEXT,
                                weight=ft.FontWeight.BOLD)))
        return ft.Container(
            bgcolor=SURFACE,
            border=ft.Border.all(width=1, color=CARD_BORDER),
            border_radius=16,
            padding=16,
            on_click=lambda _: abrir_participante(p),
            content=ft.Column(controls=linhas, spacing=4),
        )

    def atualizar_situacao():
        s = situacao_rede()
        if s["demo"]:
            txt, cor_fundo, cor_txt = "Modo demonstração: dados de exemplo, nada é gravado.", WARNING_BACKGROUND, WARNING_TEXT
        elif s["offline"]:
            txt = ("Sem conexão: você pode continuar. O que registrar fica neste aparelho"
                   + (f" ({s['pendentes']} aguardando envio)" if s["pendentes"] else "") + " e é enviado quando a internet voltar.")
            cor_fundo, cor_txt = WARNING_BACKGROUND, WARNING_TEXT
        elif s["pendentes"]:
            txt, cor_fundo, cor_txt = f"{s['pendentes']} registro(s) aguardando envio. Toque em sincronizar.", WARNING_BACKGROUND, WARNING_TEXT
        else:
            faixa_situacao.visible = False
            return
        faixa_situacao.content = ft.Text(txt, size=12, color=cor_txt)
        faixa_situacao.bgcolor = cor_fundo
        faixa_situacao.visible = True

    def atualizar_lista():
        lista_container.controls.clear()
        termo = (filtro_codigo.value or "").strip().upper()
        filtrados = [
            p for p in dados_carregados
            if (termo in p.get("codigo", "").upper() or termo in nome_completo(p).upper())
            and (not so_sinalizadas.value or (p.get("avaliacao") or {}).get("flag_professor"))
        ]
        if not filtrados:
            lista_container.controls.append(ft.Text("Nenhum participante encontrado.", color=TEXT_SECONDARY, size=14))
        else:
            for item in filtrados:
                lista_container.controls.append(montar_card(item))
        atualizar_situacao()
        page.update()

    def carregar_do_servidor():
        sucesso, resposta = buscar_participantes_e_avaliacoes()
        if not sucesso:
            atualizar_situacao()
            return dizer(str(resposta), erro=True)
        nonlocal dados_carregados
        dados_carregados = resposta
        atualizar_lista()

    def sincronizar_agora(_=None):
        res = sincronizar_fila_offline()
        if res["sincronizados"]:
            msg = f"{res['sincronizados']} registro(s) enviado(s) ao servidor."
            if res["codigos_alterados"]:
                msg += " Atenção: " + "; ".join(f"{c['antes']} virou {c['depois']}" for c in res["codigos_alterados"]) + "."
            dizer(msg)
        elif res["erros"]:
            dizer(res["erros"][0], erro=True)
        elif res["rejeitados"]:
            dizer(f"{res['rejeitados']} registro(s) foram recusados pelo servidor (dados inválidos).", erro=True)
        elif not situacao_rede()["pendentes"]:
            dizer("Nada pendente: tudo já está no servidor.")
        carregar_do_servidor()

    # ==========================================
    # FORMULÁRIO DE NOVO PARTICIPANTE (com termo de consentimento)
    # ==========================================
    form_visivel = ft.Container(visible=False)

    def campo(label, **kw):
        return ft.TextField(label=label, border_color=CARD_BORDER, bgcolor=SURFACE, **kw)

    texto_codigo = ft.Text("", size=13, color=TEXT_SECONDARY)
    nome_in = campo("Nome (opcional)", hint_text="Só para você localizar a ficha", max_length=60)
    sobrenome_in = campo("Sobrenome (opcional)", max_length=80)
    idade_in = campo("Idade (anos)", keyboard_type=ft.KeyboardType.NUMBER, on_change=lambda _: ao_mudar_idade())
    peso_in = campo("Peso em kg (ex.: 68.5)", keyboard_type=ft.KeyboardType.NUMBER)
    altura_in = campo("Altura em metros (ex.: 1.72)", keyboard_type=ft.KeyboardType.NUMBER)
    erro_form = ft.Text("", color=REVIEW_TEXT, size=12, visible=False)

    termo_box = ft.Container(
        visible=False, bgcolor=SURFACE, border=ft.Border.all(width=1, color=CARD_BORDER), border_radius=12, padding=12,
        content=ft.Column(
            controls=[ft.Text(TITULO, weight=ft.FontWeight.BOLD, size=14, color=TEXT_PRIMARY)] + [
                ft.Column([ft.Text(t, weight=ft.FontWeight.BOLD, size=13, color=PRIMARY),
                           ft.Text(x, size=13, color=TEXT_PRIMARY)], spacing=2)
                for t, x in secoes()],
            spacing=10, scroll=ft.ScrollMode.AUTO, height=280,
        ),
    )
    chk_termo = ft.Checkbox(label=DECLARACAO, value=False)
    chk_responsavel = ft.Checkbox(label=DECLARACAO_RESPONSAVEL, value=False, visible=False)

    def alternar_termo(_):
        termo_box.visible = not termo_box.visible
        page.update()

    def ao_mudar_idade():
        try:
            menor = 0 < int(idade_in.value) < 18
        except (TypeError, ValueError):
            menor = False
        chk_responsavel.visible = menor
        if not menor:
            chk_responsavel.value = False
        page.update()

    def alternar_formulario(e):
        form_visivel.visible = not form_visivel.visible
        erro_form.visible = False
        if form_visivel.visible:
            texto_codigo.value = f"Código: gerado automaticamente (próximo: {codigo_sugerido()})"
        page.update()

    def falha(msg: str):
        erro_form.value = msg
        erro_form.visible = True
        page.update()

    def salvar_participante(e):
        erro_form.visible = False
        try:
            idade_val = int(idade_in.value)
            if not (0 < idade_val < 120):
                raise ValueError()
        except Exception:
            return falha("A idade deve ser um número inteiro entre 1 e 119.")
        try:
            peso_val = float(peso_in.value.replace(",", ".")) if peso_in.value else None
            if peso_val is not None and not (0 < peso_val < 400):
                raise ValueError()
        except Exception:
            return falha("Peso inválido (informe um valor positivo em kg, ex.: 70.5).")
        try:
            altura_val = float(altura_in.value.replace(",", ".")) if altura_in.value else None
            if altura_val is not None and not (0.5 <= altura_val <= 2.5):
                raise ValueError()
        except Exception:
            return falha("Altura inválida (informe em metros entre 0.50 e 2.50, ex.: 1.75).")
        if not chk_termo.value:
            return falha("Peça ao participante para ler o termo de consentimento e marque a confirmação.")
        if idade_val < 18 and not chk_responsavel.value:
            return falha("Participante menor de 18 anos: é preciso a ciência do responsável legal.")

        sucesso, resp = criar_novo_participante(idade_val, peso_val, altura_val, nome_in.value, sobrenome_in.value,
                                                responsavel_ciente=bool(chk_responsavel.value))
        if not sucesso:
            return falha(str(resp))

        for c in (nome_in, sobrenome_in, idade_in, peso_in, altura_in):
            c.value = ""
        chk_termo.value = False
        chk_responsavel.value = False
        chk_responsavel.visible = False
        termo_box.visible = False
        form_visivel.visible = False
        carregar_do_servidor()
        dizer(f"Participante {resp['codigo']} cadastrado"
              + (" (guardado neste aparelho; será enviado quando a internet voltar)." if resp.get("pendente") else "."))

    form_visivel.content = ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(width=1, color=CARD_BORDER),
        border_radius=16,
        padding=16,
        content=ft.Column(
            controls=[
                ft.Text("Novo Participante", theme_style=ft.TextThemeStyle.TITLE_LARGE),
                texto_codigo,
                nome_in,
                sobrenome_in,
                idade_in,
                peso_in,
                altura_in,
                ft.TextButton("Ler o termo de consentimento", on_click=alternar_termo),
                termo_box,
                chk_termo,
                chk_responsavel,
                erro_form,
                ft.Row(
                    controls=[
                        ft.TextButton("Cancelar", on_click=alternar_formulario),
                        ft.Button(content=ft.Text("Salvar", weight=ft.FontWeight.BOLD), bgcolor=PRIMARY, color="white",
                                  on_click=salvar_participante),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=10,
        ),
    )

    cabecalho = ft.Row(
        controls=[
            ft.Text("Participantes", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, expand=True),
            ft.IconButton(icon=ft.Icons.SYNC, tooltip="Sincronizar", icon_color=TEXT_PRIMARY, on_click=sincronizar_agora),
            ft.IconButton(icon=ft.Icons.BAR_CHART, tooltip="Ver Dashboard", on_click=lambda _: navegar("dashboard")),
            ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="Sair", icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("login")),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    page.add(
        cabecalho,
        faixa_situacao,
        filtro_codigo,
        so_sinalizadas,
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
