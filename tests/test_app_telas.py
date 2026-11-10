"""Fluxo completo do app em MODO OFFLINE, com o `flet` substituído (ver fake_flet.py)."""
import sys

import pytest

import fake_flet  # noqa: E402  (tests/ está no sys.path pelo rootdir do pytest)

sys.modules["flet"] = fake_flet.instalar()

import estado  # noqa: E402
import tela_dashboard, tela_login, tela_participantes, tela_resumo_ia, tela_selecao, tela_teste  # noqa: E402,E401
from fake_flet import Pagina, clicavel_com_texto, textos  # noqa: E402


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(estado, "MODO_DEMO", True)
    monkeypatch.setattr(estado, "_off", {"participantes": [], "avaliacoes": {}, "resultados": []})
    estado.limpar_sessao()
    yield
    estado.limpar_sessao()


def _entrar():
    ok, _ = estado.autenticar_usuario("a@b.com", "x")
    assert ok


def _abrir_participante():
    ok, lista = estado.buscar_participantes_e_avaliacoes()
    assert ok and len(lista) == 2
    p = lista[0]
    ok, av = estado.garantir_avaliacao_ativa(p["id"], p.get("avaliacao"))
    assert ok
    estado.sessao.update(participante_atual=p, avaliacao_atual=av)
    return p, av


def test_catalogo_offline_tem_os_19_testes_das_fichas():
    ok, dados = estado.buscar_catalogo_e_resultados("a1")
    assert ok
    cat = dados["catalogo"]
    assert len(cat) == 19
    assert {t["regiao"] for t in cat} == {"Joelho", "Tornozelo", "Quadril", "Ombro", "Cotovelo", "Punho",
                                           "Coluna lombar", "Tórax", "Coluna cervical"}
    assert all(t["definicao"] and t["objetivo"] and t["como_fazer"] and t["positivo_se"] for t in cat)


def test_salvar_excluir_e_progresso_offline():
    _entrar()
    _, av = _abrir_participante()
    ok, _ = estado.salvar_resultado_teste(av["id"], {"teste_id": 1, "lado": "Direito", "resultado": "Positivo", "dor_0_10": 3})
    assert ok
    estado.salvar_resultado_teste(av["id"], {"teste_id": 1, "lado": "Esquerdo", "resultado": "Negativo", "dor_0_10": 0})
    estado.salvar_resultado_teste(av["id"], {"teste_id": 2, "lado": "Direito", "resultado": "Não realizado", "dor_0_10": None})
    assert av["status"] == "em_andamento" and av["progresso_percentual"] == pytest.approx(10.53)  # 2 de 19 testes
    ok, dados = estado.buscar_catalogo_e_resultados(av["id"])
    assert sorted(r["lado"] for r in dados["mapa_resultados"][1]) == ["Direito", "Esquerdo"]
    estado.excluir_resultado_teste_api(av["id"], 1, "Direito")
    assert [r["lado"] for r in estado.buscar_catalogo_e_resultados(av["id"])[1]["mapa_resultados"][1]] == ["Esquerdo"]


def test_codigo_e_gerado_automaticamente_e_nome_e_opcional():
    _entrar()
    estado.buscar_participantes_e_avaliacoes()
    ok, p = estado.criar_novo_participante(20, None, None)
    assert ok and p["codigo"] == "P-003" and p["nome"] is None
    ok, p = estado.criar_novo_participante(21, 60.0, 1.65, nome="  Maria  ", sobrenome="Souza", responsavel_ciente=False)
    assert ok and p["codigo"] == "P-004" and (p["nome"], p["sobrenome"]) == ("Maria", "Souza")


def test_login_exige_email_e_senha_e_nao_pede_consentimento():
    pagina, destinos = Pagina(), []
    tela_login.render_login(pagina, destinos.append)
    assert not any(type(c).__name__ == "Checkbox" for c in fake_flet.percorrer(pagina.controles))
    clicavel_com_texto(pagina.controles, "Entrar e Iniciar").on_click(None)
    assert destinos == [] and any("Preencha" in t for t in textos(pagina.controles))
    campos = [c for c in fake_flet.percorrer(pagina.controles) if type(c).__name__ == "TextField"]
    campos[0].value, campos[1].value = "a@b.com", "x"
    clicavel_com_texto(pagina.controles, "Entrar e Iniciar").on_click(None)
    assert destinos == ["participantes"]


def _campos_form(pagina):
    por_rotulo = {getattr(c, "label", ""): c for c in fake_flet.percorrer(pagina.controles) if type(c).__name__ == "TextField"}
    caixas = [c for c in fake_flet.percorrer(pagina.controles) if type(c).__name__ == "Checkbox"]
    return por_rotulo, caixas


def test_formulario_exige_termo_e_responsavel_para_menor():
    _entrar()
    pagina, destinos = Pagina(), []
    tela_participantes.render_participantes(pagina, destinos.append)
    clicavel_com_texto(pagina.controles, "+ Novo participante").on_click(None)
    assert any(t.startswith("Código: gerado automaticamente (próximo: P-003)") for t in textos(pagina.controles))
    campos, caixas = _campos_form(pagina)
    assert "Nome (opcional)" in campos and "Sobrenome (opcional)" in campos and "Código (ex.: P-015 — nunca use nome)" not in campos
    campos["Idade (anos)"].value = "16"
    campos["Idade (anos)"].on_change(None)
    campos["Nome (opcional)"].value = "Joana"
    clicavel_com_texto(pagina.controles, "Salvar").on_click(None)
    assert any("termo de consentimento" in t for t in textos(pagina.controles))  # sem termo marcado
    chk_termo = next(c for c in caixas if getattr(c, "label", "").startswith("Li (ou foi lido"))
    chk_resp = next(c for c in caixas if getattr(c, "label", "").startswith("O responsável legal"))
    assert chk_resp.visible is True
    chk_termo.value = True
    clicavel_com_texto(pagina.controles, "Salvar").on_click(None)
    assert any("responsável legal" in t for t in textos(pagina.controles)) and len(estado._off["participantes"]) == 2
    chk_resp.value = True
    clicavel_com_texto(pagina.controles, "Salvar").on_click(None)
    assert [p["codigo"] for p in estado._off["participantes"]] == ["P-001", "P-002", "P-003"]
    assert estado._off["participantes"][-1]["nome"] == "Joana"
    assert any("P-003 cadastrado" in t for t in textos(pagina.controles))


def test_telas_montam_e_tela_do_teste_salva():
    _entrar()
    _, av = _abrir_participante()
    pagina, destinos = Pagina(), []

    tela_participantes.render_participantes(pagina, destinos.append)
    assert "P-001" in textos(pagina.controles)

    pagina.clean()
    tela_selecao.render_selecao(pagina, destinos.append)
    assert any("0 de 19 testes" in t for t in textos(pagina.controles))
    clicavel_com_texto(pagina.controles, "Lasègue").on_click(None)  # abre o teste
    assert destinos[-1] == "teste" and estado.sessao["teste_atual"]["nome"] == "Lasègue"

    pagina.clean()
    tela_teste.render_teste(pagina, destinos.append)
    assert any("Valor medido (graus)" == getattr(c, "label", None) for c in fake_flet.percorrer(pagina.controles))
    clicavel_com_texto(pagina.controles, "Salvar e voltar à lista").on_click(None)  # sem resultado: bloqueia
    assert destinos[-1] == "teste" and any("Escolha o resultado" in t for t in textos(pagina.controles))
    clicavel_com_texto(pagina.controles, "Esquerdo").on_click(None)  # trocar o lado recarrega o formulário daquele lado
    clicavel_com_texto(pagina.controles, "Positivo").on_click(None)
    clicavel_com_texto(pagina.controles, "7").on_click(None)
    campo = next(c for c in fake_flet.percorrer(pagina.controles) if getattr(c, "label", "") == "Valor medido (graus)")
    campo.value = "45,5"
    clicavel_com_texto(pagina.controles, "Salvar e voltar à lista").on_click(None)
    assert destinos[-1] == "selecao"
    salvo = estado._off["resultados"][0]
    assert (salvo["teste_id"], salvo["lado"], salvo["resultado"], salvo["dor_0_10"], salvo["valor_medido"]) == (14, "Esquerdo", "Positivo", 7, 45.5)


def test_excluir_pede_confirmacao_e_fica_separado_do_salvar():
    _entrar()
    _, av = _abrir_participante()
    estado.salvar_resultado_teste(av["id"], {"teste_id": 1, "lado": "Direito", "resultado": "Negativo", "dor_0_10": 0})
    estado.sessao["teste_atual"] = estado.buscar_catalogo_e_resultados(av["id"])[1]["catalogo"][0]
    estado.sessao["resultados_teste"] = estado.buscar_catalogo_e_resultados(av["id"])[1]["mapa_resultados"][1]
    pagina, destinos = Pagina(), []
    tela_teste.render_teste(pagina, destinos.append)
    clicavel_com_texto(pagina.controles, "Excluir resultado deste lado").on_click(None)
    assert estado._off["resultados"], "ainda não excluiu: só pediu confirmação"
    clicavel_com_texto(pagina.controles, "Sim, excluir").on_click(None)
    assert not estado._off["resultados"] and destinos[-1] == "selecao"


def test_dashboard_e_resumo_ia_montam():
    _entrar()
    _, av = _abrir_participante()
    pagina, destinos = Pagina(), []
    tela_dashboard.render_dashboard(pagina, destinos.append)
    assert "Positivos por região (%)" in textos(pagina.controles)
    pagina.clean()
    tela_resumo_ia.render_resumo_ia(pagina, destinos.append)
    clicavel_com_texto(pagina.controles, "Gerar resumo para discussão").on_click(None)
    caixa = next(c for c in fake_flet.percorrer(pagina.controles) if type(c).__name__ == "TextField")
    assert "NOTA: Este é um rascunho" in caixa.value
