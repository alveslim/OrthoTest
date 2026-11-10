import flet as ft

from estado import excluir_resultado_teste_api, salvar_resultado_teste, sessao
from theme import CARD_BORDER, PRIMARY, REVIEW_BACKGROUND, REVIEW_TEXT, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY

# Tela montada só com Container/Text/Row/Column/TextField/Button: componentes estáveis entre versões
# do Flet (sem Dropdown, AlertDialog ou SnackBar, que mudaram de API na 1.0).
LADOS = ("Direito", "Esquerdo", "Bilateral")
RESULTADOS = ("Positivo", "Negativo", "Não realizado", "Inconclusivo")
ALVO = 48  # alvo de toque mínimo (px)


def render_teste(page: ft.Page, navegar):
    teste = sessao.get("teste_atual") or {}
    avaliacao = sessao.get("avaliacao_atual") or {}
    existentes = {r["lado"]: r for r in (sessao.get("resultados_teste") or [])}
    unidade = teste.get("unidade_medida")

    primeiro = next(iter(existentes.values()), {})
    estado = {
        "lado": primeiro.get("lado", "Direito"),
        "resultado": primeiro.get("resultado"),
        "dor": primeiro.get("dor_0_10"),
    }

    feedback = ft.Text("", size=13, color=REVIEW_TEXT, visible=False)
    campo_obs = ft.TextField(
        label="Observações (opcional)", hint_text="Ex.: dor ao final da tração, clique articular...",
        multiline=True, min_lines=2, max_lines=4, max_length=500,
        border_color=CARD_BORDER, bgcolor=SURFACE, text_size=14,
    )
    campo_valor = ft.TextField(
        label=f"Valor medido ({unidade})" if unidade else "", keyboard_type=ft.KeyboardType.NUMBER,
        border_color=CARD_BORDER, bgcolor=SURFACE, visible=bool(unidade),
    )

    linha_lados = ft.Row(spacing=8, wrap=True)
    linha_resultados = ft.Row(spacing=8, wrap=True)
    linha_dor = ft.Row(spacing=6, wrap=True)
    texto_dor = ft.Text("", size=13, color=TEXT_SECONDARY)
    botao_excluir_area = ft.Container(visible=False)
    ficha = ft.Container(visible=False)
    confirmacao = ft.Container(visible=False)

    def dizer(msg: str, erro: bool = True):
        feedback.value = msg
        feedback.color = REVIEW_TEXT if erro else PRIMARY
        feedback.visible = True
        page.update()

    def chip(rotulo: str, ativo: bool, ao_clicar, largura: int | None = None, perigo: bool = False):
        return ft.Container(
            content=ft.Text(rotulo, size=14, weight=ft.FontWeight.BOLD, color="white" if ativo else TEXT_PRIMARY,
                            text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment(0, 0), height=ALVO, width=largura,
            padding=ft.Padding(left=14, top=0, right=14, bottom=0),
            bgcolor=(REVIEW_TEXT if perigo else PRIMARY) if ativo else SURFACE,
            border=ft.Border.all(width=1, color=PRIMARY if ativo else CARD_BORDER),
            border_radius=24, on_click=ao_clicar,
        )

    def preencher_do_lado():
        """Ao trocar o lado, carrega o que já foi salvo para ele (ou limpa o formulário)."""
        salvo = existentes.get(estado["lado"])
        estado["resultado"] = salvo.get("resultado") if salvo else None
        estado["dor"] = salvo.get("dor_0_10") if salvo else None
        campo_obs.value = (salvo or {}).get("observacoes") or ""
        v = (salvo or {}).get("valor_medido")
        campo_valor.value = "" if v is None else str(v)

    def redesenhar():
        linha_lados.controls = [
            chip(l, estado["lado"] == l, lambda _, l=l: escolher_lado(l)) for l in LADOS
        ]
        linha_resultados.controls = [
            chip(r, estado["resultado"] == r, lambda _, r=r: escolher_resultado(r)) for r in RESULTADOS
        ]
        linha_dor.controls = [
            chip(str(n), estado["dor"] == n, lambda _, n=n: escolher_dor(n), largura=ALVO) for n in range(11)
        ]
        texto_dor.value = "Dor durante o teste: não informada" if estado["dor"] is None else f"Dor durante o teste: {estado['dor']}/10"
        botao_excluir_area.visible = estado["lado"] in existentes
        page.update()

    def escolher_lado(l):
        estado["lado"] = l
        preencher_do_lado()
        confirmacao.visible = False
        redesenhar()

    def escolher_resultado(r):
        estado["resultado"] = r
        redesenhar()

    def escolher_dor(n):
        estado["dor"] = None if estado["dor"] == n else n  # tocar de novo limpa
        redesenhar()

    # ----------------------------------------------------------- ficha clínica (botão ?)
    def secao_ficha(titulo: str, texto: str):
        return ft.Column([ft.Text(titulo, weight=ft.FontWeight.BOLD, size=13, color=PRIMARY),
                          ft.Text(texto or "—", size=13, color=TEXT_PRIMARY)], spacing=2)

    ficha.content = ft.Container(
        bgcolor=SURFACE, border=ft.Border.all(width=1, color=PRIMARY), border_radius=12, padding=14,
        content=ft.Column([
            secao_ficha("Definição", teste.get("definicao")),
            secao_ficha("Objetivo", teste.get("objetivo")),
            secao_ficha("Como fazer", teste.get("como_fazer")),
            secao_ficha("Positivo se", teste.get("positivo_se")),
            ft.Text("Compare sempre com o lado contralateral. Positivo indica sinal compatível com a hipótese em "
                    "investigação, não confirma lesão; negativo não significa ausência de alteração. "
                    "Uso exclusivamente acadêmico.", size=11, color=TEXT_SECONDARY, italic=True),
        ], spacing=10),
    )

    def alternar_ficha(_):
        ficha.visible = not ficha.visible
        page.update()

    # ----------------------------------------------------------- salvar
    def salvar(_):
        feedback.visible = False
        if not avaliacao.get("id") or not teste.get("id"):
            return dizer("Nenhuma avaliação ativa. Volte à lista de participantes.")
        if estado["resultado"] is None:
            return dizer("Escolha o resultado do teste antes de salvar.")
        valor = None
        if unidade and (campo_valor.value or "").strip():
            try:
                valor = float(campo_valor.value.replace(",", "."))
                if not 0 <= valor <= 999:
                    raise ValueError
            except ValueError:
                return dizer(f"Valor medido inválido (use um número entre 0 e 999 {unidade}).")
        payload = {
            "teste_id": int(teste["id"]), "lado": estado["lado"], "resultado": estado["resultado"],
            "dor_0_10": estado["dor"], "valor_medido": valor,
            "observacoes": (campo_obs.value or "").strip() or None,
        }
        ok, msg = salvar_resultado_teste(str(avaliacao["id"]), payload)
        if ok:
            sessao["aviso_selecao"] = msg
            navegar("selecao")
        else:
            dizer(msg)

    # ----------------------------------------------------------- excluir (separado do Salvar, com confirmação)
    def executar_exclusao(_):
        ok, msg = excluir_resultado_teste_api(str(avaliacao["id"]), int(teste["id"]), estado["lado"])
        if ok:
            sessao["aviso_selecao"] = msg
            navegar("selecao")
        else:
            confirmacao.visible = False
            dizer(msg)

    def cancelar_exclusao(_):
        confirmacao.visible = False
        page.update()

    confirmacao.content = ft.Container(
        bgcolor=REVIEW_BACKGROUND, border_radius=12, padding=14,
        content=ft.Column([
            ft.Text("Excluir o resultado deste teste e lado? O progresso da avaliação será atualizado.",
                    size=13, color=REVIEW_TEXT, weight=ft.FontWeight.BOLD),
            ft.Row([chip("Cancelar", False, cancelar_exclusao),
                    chip("Sim, excluir", True, executar_exclusao, perigo=True)], spacing=8),
        ], spacing=10),
    )

    def pedir_confirmacao(_):
        confirmacao.visible = True
        page.update()

    botao_excluir_area.content = ft.Container(
        content=ft.Text("Excluir resultado deste lado", size=13, color=REVIEW_TEXT, weight=ft.FontWeight.BOLD),
        padding=ft.Padding(left=4, top=12, right=4, bottom=12), on_click=pedir_confirmacao,
    )

    # ----------------------------------------------------------- montagem
    cabecalho = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=TEXT_PRIMARY, tooltip="Voltar",
                          on_click=lambda _: navegar("selecao")),
            ft.Text(f"Teste de {teste.get('nome', '')}", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY,
                    expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon=ft.Icons.HELP_OUTLINE, icon_color=PRIMARY, tooltip="Ficha clínica", on_click=alternar_ficha),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    subtitulo = ft.Text(f"{teste.get('regiao', '')} • {teste.get('estrutura') or ''}", size=13,
                        color=TEXT_SECONDARY, text_align=ft.TextAlign.CENTER)

    def titulo(txt):
        return ft.Text(txt, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)

    preencher_do_lado()
    page.add(
        cabecalho,
        ft.Container(content=subtitulo, alignment=ft.Alignment(0, 0)),
        ficha,
        feedback,
        titulo("Lado testado"), linha_lados,
        titulo("Resultado"), linha_resultados,
        titulo("Dor (0 a 10)"), texto_dor, linha_dor,
        campo_valor,
        campo_obs,
        ft.Button(
            content=ft.Text("Salvar e voltar à lista", weight=ft.FontWeight.BOLD),
            bgcolor=PRIMARY, color="white", height=ALVO, width=350, on_click=salvar,
        ),
        ft.TextButton("Voltar sem salvar", on_click=lambda _: navegar("selecao")),
        ft.Divider(height=8, color="transparent"),
        botao_excluir_area,
        confirmacao,
    )
    redesenhar()
