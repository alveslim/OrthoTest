import flet as ft

from estado import buscar_kpis_dashboard, exportar_relatorio_dashboard
from theme import CARD_BORDER, PRIMARY, REVIEW_TEXT, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY


def _fmt(valor, sufixo=""):
    return "—" if valor is None else f"{valor}{sufixo}"


def render_dashboard(page: ft.Page, navegar):
    voltar = ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=TEXT_PRIMARY, on_click=lambda _: navegar("participantes"))
    sucesso, dados = buscar_kpis_dashboard()
    if not sucesso:
        page.add(ft.Row([voltar, ft.Text("Dashboard", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)]),
                 ft.Text(str(dados), color=REVIEW_TEXT))
        return

    def cartao(titulo: str, valor: str):
        return ft.Container(
            bgcolor=SURFACE, border=ft.Border.all(width=1, color=CARD_BORDER), border_radius=12, padding=14, width=165,
            content=ft.Column([
                ft.Text(titulo, size=12, color=TEXT_SECONDARY),
                ft.Text(valor, size=24, weight=ft.FontWeight.BOLD, color=PRIMARY),
            ], spacing=2),
        )

    def barras(titulo: str, grupos: list[dict], campo: str):
        """Barras horizontais (percentual positivo) — rótulo e valor sempre em texto."""
        linhas = [ft.Text(titulo, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)]
        if not grupos:
            linhas.append(ft.Text("Sem grupo com 3 ou mais participantes ainda.", size=12, color=TEXT_SECONDARY))
        for g in grupos:
            pct = float(g["percentual_positivo"])
            linhas.append(ft.Column([
                ft.Row([
                    ft.Text(str(g[campo]), size=13, color=TEXT_PRIMARY, expand=True),
                    ft.Text(f"{pct:.0f}% · n={g['participantes']}", size=12, color=TEXT_SECONDARY),
                ]),
                ft.Container(bgcolor=CARD_BORDER, height=10, border_radius=5, content=ft.Row([
                    ft.Container(bgcolor=PRIMARY, height=10, border_radius=5, expand=max(int(pct), 1)),
                    ft.Container(expand=max(100 - int(pct), 0) or None),
                ], spacing=0)),
            ], spacing=3))
        return ft.Container(
            bgcolor=SURFACE, border=ft.Border.all(width=1, color=CARD_BORDER), border_radius=12, padding=14,
            content=ft.Column(linhas, spacing=10),
        )

    resultado_export = ft.Text("", size=12, visible=False)

    def exportar(_):
        ok, msg = exportar_relatorio_dashboard()
        resultado_export.value = msg
        resultado_export.color = PRIMARY if ok else REVIEW_TEXT
        resultado_export.visible = True
        page.update()

    nota = "Grupos com menos de 3 participantes não são exibidos isoladamente (privacidade)."
    if dados.get("gerais_ocultos"):
        nota = "Com menos de 3 participantes, médias e percentuais ficam ocultos (privacidade). " + nota

    page.add(
        ft.Row([voltar, ft.Text("Dashboard", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, expand=True)]),
        ft.Row([
            cartao("Participantes", str(dados.get("participantes_avaliados", 0))),
            cartao("Avaliações completas", _fmt(dados.get("percentual_avaliacoes_completas"), "%")),
            cartao("Dor média", _fmt(dados.get("dor_media_geral"), "/10")),
        ], wrap=True, spacing=10),
        barras("Positivos por região (%)", dados.get("positividade_por_regiao", []), "regiao"),
        barras("Positivos por teste (%)", dados.get("positividade_por_teste", []), "teste"),
        barras("Positivos por faixa etária (%)", dados.get("positividade_por_faixa_etaria", []), "faixa_etaria"),
        barras("Positivos por faixa de IMC (%)", dados.get("positividade_por_imc", []), "faixa_imc"),
        ft.Text(nota, size=11, color=TEXT_SECONDARY, italic=True),
        ft.Button(content=ft.Text("Exportar CSV agregado", weight=ft.FontWeight.BOLD), bgcolor=PRIMARY, color="white",
                  height=48, on_click=exportar),
        resultado_export,
    )
