"""Login real, sessão lembrada e modo sem internet, contra um servidor simulado (sem rede de verdade)."""
import re
import time

import pytest
import requests

import contingencia_offline as fila
import estado
from armazenamento import pasta_dados


class Resp:
    def __init__(self, status, corpo=None):
        self.status_code, self._corpo = status, corpo if corpo is not None else {}

    def json(self):
        return self._corpo


class Servidor:
    """Mini API + Auth em memória. `online=False` simula falta de internet."""

    def __init__(self):
        self.online = True
        self.token = "tok1"
        self.refresh_validos = {"ref1"}
        self.participantes, self.avaliacoes, self.resultados = [], [], []
        self.recusar_resultados = False
        self.chamadas_refresh = 0

    # -- Auth (requests.post)
    def post(self, url, headers=None, json=None, timeout=None):
        if not self.online:
            raise requests.ConnectionError()
        if "grant_type=password" in url:
            if json["password"] != "certa":
                return Resp(400, {"error_code": "invalid_credentials"})
            return Resp(200, {"access_token": self.token, "refresh_token": "ref1", "expires_in": 3600,
                              "user": {"id": "u1"}})
        self.chamadas_refresh += 1
        if json["refresh_token"] in self.refresh_validos:
            self.token = f"tok{self.chamadas_refresh + 1}"
            return Resp(200, {"access_token": self.token, "refresh_token": "ref1", "expires_in": 3600, "user": {"id": "u1"}})
        return Resp(400, {"error_code": "refresh_token_not_found"})

    # -- API (requests.request)
    def request(self, metodo, url, headers=None, params=None, json=None, timeout=None):
        if not self.online:
            raise requests.ConnectionError()
        if headers.get("Authorization") != f"Bearer {self.token}":
            return Resp(401, {"detail": "Token inválido."})
        caminho = url.split("/api/v1", 1)[1]
        if (metodo, caminho) == ("GET", "/me"):
            return Resp(200, {"papel": "aluno"})
        if (metodo, caminho) == ("GET", "/participantes"):
            return Resp(200, self.participantes)
        if (metodo, caminho) == ("GET", "/avaliacoes"):
            return Resp(200, self.avaliacoes)
        if (metodo, caminho) == ("GET", "/catalogo/testes"):
            return Resp(200, estado._catalogo_local())
        if (metodo, caminho) == ("POST", "/participantes"):
            if json.get("codigo") and any(p["codigo"] == json["codigo"] for p in self.participantes):
                return Resp(409, {"detail": "duplicate key"})
            codigo = json.get("codigo") or fila.proximo_codigo([p["codigo"] for p in self.participantes])
            novo = dict(json, id=f"srv-p{len(self.participantes) + 1}", codigo=codigo)
            self.participantes.append(novo)
            return Resp(201, novo)
        if (metodo, caminho) == ("POST", "/avaliacoes"):
            nova = {"id": f"srv-a{len(self.avaliacoes) + 1}", "participante_id": json["participante_id"],
                    "status": "pendente", "progresso_percentual": 0.0}
            self.avaliacoes.append(nova)
            return Resp(201, nova)
        m = re.fullmatch(r"/avaliacoes/([^/]+)/resultados", caminho)
        if m:
            if metodo == "GET":
                return Resp(200, [r for r in self.resultados if r["avaliacao_id"] == m.group(1)])
            if self.recusar_resultados:
                return Resp(422, {"detail": "valor fora da faixa"})
            if not any(a["id"] == m.group(1) for a in self.avaliacoes):
                return Resp(404, {"detail": "Avaliação não encontrada."})
            self.resultados = [r for r in self.resultados if not (
                r["avaliacao_id"] == m.group(1) and r["teste_id"] == json["teste_id"] and r["lado"] == json["lado"])]
            self.resultados.append(dict(json, avaliacao_id=m.group(1)))
            return Resp(201, json)
        m = re.fullmatch(r"/avaliacoes/([^/]+)/resultados/(\d+)", caminho)
        if m and metodo == "DELETE":
            self.resultados = [r for r in self.resultados if not (r["avaliacao_id"] == m.group(1) and r["teste_id"] == int(m.group(2)))]
            return Resp(200, {})
        return Resp(404, {"detail": f"rota inesperada {metodo} {caminho}"})


@pytest.fixture
def srv(monkeypatch):
    s = Servidor()
    monkeypatch.setattr(estado, "MODO_DEMO", False)
    monkeypatch.setattr(estado, "SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setattr(estado, "SUPABASE_ANON_KEY", "anon")
    monkeypatch.setattr(estado.requests, "request", s.request)
    monkeypatch.setattr(estado.requests, "post", s.post)
    estado.limpar_sessao()
    yield s
    estado.limpar_sessao()


def _logar():
    ok, msg = estado.autenticar_usuario("aluno@exemplo.com", "certa")
    assert ok, msg


def _esquecer_memoria():
    """Simula fechar e reabrir o app: some a memória, fica só o que foi gravado em disco."""
    estado.sessao.update(access_token=None, refresh_token=None, expires_at=0, user_id=None, email=None)


# ---------------------------------------------------------------- login
def test_login_com_senha_errada_nao_entra(srv):
    ok, msg = estado.autenticar_usuario("aluno@exemplo.com", "qualquer")
    assert not ok and "incorretos" in msg and estado.sessao["access_token"] is None


def test_login_sem_internet_explica_que_o_primeiro_acesso_precisa_de_conexao(srv):
    srv.online = False
    ok, msg = estado.autenticar_usuario("aluno@exemplo.com", "certa")
    assert not ok and "primeiro acesso" in msg


def test_login_salva_sessao_sem_gravar_a_senha(srv):
    _logar()
    texto = (pasta_dados() / "sessao.json").read_text(encoding="utf-8")
    assert "ref1" in texto and "certa" not in texto


def test_reabrir_o_app_entra_direto_sem_pedir_login(srv):
    _logar()
    _esquecer_memoria()
    assert estado.tentar_restaurar_sessao() is True
    assert estado.sessao["email"] == "aluno@exemplo.com" and estado.sessao["access_token"] == "tok1"
    assert srv.chamadas_refresh == 0  # token ainda valia: nem precisou renovar


def test_reabrir_sem_internet_com_token_vencido_continua_logado(srv):
    _logar()
    import armazenamento
    dados = armazenamento.ler_json("sessao.json", {})
    dados["expires_at"] = int(time.time()) - 10
    armazenamento.gravar_json("sessao.json", dados)
    _esquecer_memoria()
    srv.online = False
    assert estado.tentar_restaurar_sessao() is True
    assert estado.sessao["offline"] is True


def test_sessao_revogada_volta_para_o_login(srv):
    _logar()
    import armazenamento
    dados = armazenamento.ler_json("sessao.json", {})
    dados["expires_at"] = int(time.time()) - 10
    armazenamento.gravar_json("sessao.json", dados)
    _esquecer_memoria()
    srv.refresh_validos.clear()
    assert estado.tentar_restaurar_sessao() is False
    assert not (pasta_dados() / "sessao.json").exists()


def test_token_vencido_e_renovado_sozinho_e_a_chamada_e_repetida(srv):
    _logar()
    srv.token = "outro-token"  # o servidor invalidou o token em uso
    ok, lista = estado.buscar_participantes_e_avaliacoes()
    assert ok and srv.chamadas_refresh == 1 and estado.sessao["access_token"] == srv.token


def test_sair_esquece_o_login(srv):
    _logar()
    estado.limpar_sessao()
    assert not (pasta_dados() / "sessao.json").exists() and estado.tentar_restaurar_sessao() is False


# ---------------------------------------------------------------- sem internet
def test_fluxo_completo_sem_internet_e_envio_ao_voltar(srv):
    _logar()
    estado.buscar_participantes_e_avaliacoes()  # online: enche o cache (catálogo vem junto ao abrir a ficha)
    srv.online = False

    ok, p = estado.criar_novo_participante(25, 70.0, 1.75, nome="Maria", sobrenome="Souza")
    assert ok and p["pendente"] and p["codigo"] == "P-001" and fila.eh_local(p["id"])
    ok, av = estado.garantir_avaliacao_ativa(p["id"], None)
    assert ok and fila.eh_local(av["id"])
    ok, msg = estado.salvar_resultado_teste(av["id"], {"teste_id": 14, "lado": "Direito", "resultado": "Positivo", "dor_0_10": 4})
    assert ok and "guardado neste aparelho" in msg
    estado.salvar_resultado_teste(av["id"], {"teste_id": 15, "lado": "Bilateral", "resultado": "Negativo", "dor_0_10": 0})
    assert estado.situacao_rede()["pendentes"] == 4 and srv.participantes == []

    # a tela continua mostrando tudo, com o que está pendente
    ok, lista = estado.buscar_participantes_e_avaliacoes()
    assert ok and lista[0]["codigo"] == "P-001" and lista[0]["pendente"] and lista[0]["avaliacao"]["progresso_percentual"] > 0
    ok, dados = estado.buscar_catalogo_e_resultados(av["id"])
    assert ok and set(dados["mapa_resultados"]) == {14, 15} and len(dados["catalogo"]) == 19

    estado.sessao.update(participante_atual=p, avaliacao_atual=av)
    srv.online = True  # a internet voltou
    res = estado.sincronizar_fila_offline()
    assert res["sincronizados"] == 4 and res["pendentes"] == 0 and not res["erros"]
    assert [x["codigo"] for x in srv.participantes] == ["P-001"] and srv.participantes[0]["nome"] == "Maria"
    assert srv.avaliacoes[0]["participante_id"] == srv.participantes[0]["id"]  # id provisório virou o real
    assert {(r["avaliacao_id"], r["teste_id"]) for r in srv.resultados} == {("srv-a1", 14), ("srv-a1", 15)}
    assert estado.situacao_rede()["pendentes"] == 0
    assert estado.sessao["avaliacao_atual"]["id"] == "srv-a1" and not fila.eh_local(estado.sessao["participante_atual"]["id"])


def test_falha_de_rede_no_meio_da_sincronizacao_mantem_o_resto(srv):
    _logar()
    srv.online = False
    _, p = estado.criar_novo_participante(30, None, None)
    _, av = estado.garantir_avaliacao_ativa(p["id"], None)
    estado.salvar_resultado_teste(av["id"], {"teste_id": 1, "lado": "Direito", "resultado": "Positivo", "dor_0_10": 1})
    res = estado.sincronizar_fila_offline()  # continua sem internet
    assert res["sincronizados"] == 0 and res["pendentes"] == 3 and res["erros"]


def test_codigo_provisorio_em_conflito_recebe_outro_codigo(srv):
    _logar()
    srv.online = False
    ok, p = estado.criar_novo_participante(30, None, None)
    assert p["codigo"] == "P-001"
    srv.participantes.append({"id": "srv-outro", "codigo": "P-001"})  # outro aparelho usou P-001 enquanto isso
    srv.online = True
    res = estado.sincronizar_fila_offline()
    assert res["sincronizados"] == 1 and res["codigos_alterados"] == [{"antes": "P-001", "depois": "P-002"}]


def test_salvar_online_descarta_versao_antiga_pendente(srv):
    _logar()
    estado.buscar_participantes_e_avaliacoes()
    _, p = estado.criar_novo_participante(30, None, None)
    _, av = estado.garantir_avaliacao_ativa(p["id"], None)
    chave = {"teste_id": 14, "lado": "Direito"}
    srv.online = False
    estado.salvar_resultado_teste(av["id"], dict(chave, resultado="Positivo", dor_0_10=7))
    assert estado.situacao_rede()["pendentes"] == 1
    srv.online = True
    estado.salvar_resultado_teste(av["id"], dict(chave, resultado="Negativo", dor_0_10=0))
    assert estado.situacao_rede()["pendentes"] == 0
    assert [r["resultado"] for r in srv.resultados] == ["Negativo"]  # a fila antiga não sobrescreve o mais novo


def test_resultado_recusado_pelo_servidor_nao_some_em_silencio(srv):
    _logar()
    estado.buscar_participantes_e_avaliacoes()
    _, p = estado.criar_novo_participante(30, None, None)
    _, av = estado.garantir_avaliacao_ativa(p["id"], None)
    srv.online = False
    estado.salvar_resultado_teste(av["id"], {"teste_id": 14, "lado": "Direito", "resultado": "Positivo", "dor_0_10": 1})
    srv.online, srv.recusar_resultados = True, True
    res = estado.sincronizar_fila_offline()
    assert res["rejeitados"] == 1 and res["pendentes"] == 0
    rejeitados = __import__("armazenamento").ler_json(fila.ARQ_REJEITADOS, [])
    assert rejeitados[0]["motivo"] == "valor fora da faixa"


def test_excluir_resultado_ainda_pendente_apenas_descarta(srv):
    _logar()
    srv.online = False
    _, p = estado.criar_novo_participante(30, None, None)
    _, av = estado.garantir_avaliacao_ativa(p["id"], None)
    estado.salvar_resultado_teste(av["id"], {"teste_id": 14, "lado": "Direito", "resultado": "Positivo", "dor_0_10": 1})
    ok, _ = estado.excluir_resultado_teste_api(av["id"], 14, "Direito")
    assert ok and estado.situacao_rede()["pendentes"] == 2  # sobram participante + avaliação


def test_fila_de_um_usuario_nao_e_enviada_por_outro(srv):
    _logar()
    srv.online = False
    estado.criar_novo_participante(30, None, None)
    estado.limpar_sessao()
    srv.online = True
    estado.sessao.update(access_token=srv.token, refresh_token="ref1", user_id="u2")
    assert estado.sincronizar_fila_offline()["sincronizados"] == 0 and srv.participantes == []
    assert len(fila.pendentes("u1")) == 1


def test_ia_e_sinalizar_avisam_quando_a_ficha_ainda_e_local(srv):
    _logar()
    srv.online = False
    _, p = estado.criar_novo_participante(30, None, None)
    _, av = estado.garantir_avaliacao_ativa(p["id"], None)
    ok, msg, _ = estado.solicitar_resumo_ia(av["id"])
    assert not ok and "ainda não foi enviada" in msg
    ok, msg = estado.sinalizar_avaliacao_professor(av["id"], "dúvida")
    assert not ok and "ainda não foi enviada" in msg
