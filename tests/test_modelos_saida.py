"""As respostas da API devem aceitar a linha COMPLETA que o banco devolve (select *).
Antes, `excluido_em` não estava no modelo de saída (extra=forbid): a rota dava 500 e, sem cabeçalhos de CORS,
o navegador só mostrava "NetworkError" (app dizia 'sem conexão')."""
from backend.schemas import AvaliacaoSaida, ParticipanteSaida, ResultadoTesteSaida

U = "9995608c-c4a2-461b-aa0c-2a1abc316c63"
T = "2026-11-12T15:49:32.238359+00:00"


def test_participante_do_banco_valida():
    linha = {"id": U, "user_id": U, "codigo": "P-001", "idade": 22, "peso_kg": 68.5, "altura_m": 1.72,
             "consentimento": True, "data_consentimento": T, "criado_em": T, "excluido_em": None,
             "nome": "Ana", "sobrenome": None, "termo_versao": "2026-11-v1", "consentimento_responsavel": False}
    assert ParticipanteSaida(**linha).codigo == "P-001"


def test_avaliacao_do_banco_valida():
    linha = {"id": U, "participante_id": U, "avaliador_id": U, "data_avaliacao": T, "flag_professor": False,
             "flag_motivo": None, "status": "pendente", "progresso_percentual": 0, "excluido_em": None}
    assert AvaliacaoSaida(**linha).status == "pendente"


def test_resultado_do_banco_valida():
    linha = {"id": U, "avaliacao_id": U, "teste_id": 1, "lado": "Esquerdo", "resultado": "Positivo",
             "valor_medido": None, "dor_0_10": 3, "observacoes": None, "criado_em": T, "excluido_em": None}
    assert ResultadoTesteSaida(**linha).teste_id == 1
