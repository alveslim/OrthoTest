import os
from app.contingencia_offline import salvar_rascunho_local, carregar_fila_local, sincronizar_rascunhos, ARQUIVO_FILA

class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

def test_fluxo_offline_e_sincronizacao_sem_duplicar():
    if os.path.exists(ARQUIVO_FILA):
        os.remove(ARQUIVO_FILA)

    item1 = {"avaliacao_id": "AV1", "teste_id": 1, "lado": "Direito", "resultado": "Positivo", "dor_0_10": 4}
    # Salva duas vezes o mesmo item: deve manter apenas 1 na fila (idempotência)
    salvar_rascunho_local(item1)
    salvar_rascunho_local(item1)
    assert len(carregar_fila_local()) == 1

    # Simula sincronização com sucesso (HTTP 201)
    res = sincronizar_rascunhos("http://localhost:8000", {}, post_fn=lambda *a, **kw: MockResponse(201))
    assert res["sincronizados"] == 1
    assert res["pendentes"] == 0
    assert len(carregar_fila_local()) == 0