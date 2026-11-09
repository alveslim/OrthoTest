import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Banco em memória protegido por Lock para simular transação ACID do PostgreSQL
banco_concorrente = []
lock_banco = threading.Lock()

def simular_gravacao_avaliador(avaliador_idx: int) -> dict:
    """AULA: Simula um avaliador salvando 3 testes simultaneamente."""
    inicio = time.perf_counter()
    sucessos = 0
    duplicidades = 0

    for teste_id in range(1, 4):
        registro = {
            "avaliacao_id": f"AVAL_CONC_{avaliador_idx}",
            "avaliador_id": f"avaliador_{avaliador_idx}",
            "teste_id": teste_id,
            "lado": "Direito",
            "resultado": "Positivo",
            "dor_0_10": 5
        }
        time.sleep(0.01) # Simula latência de rede de 10ms
        with lock_banco:
            # Verifica constraint de unicidade (avaliacao_id, teste_id, lado)
            existe = any(
                r["avaliacao_id"] == registro["avaliacao_id"] and
                r["teste_id"] == registro["teste_id"] and
                r["lado"] == registro["lado"]
                for r in banco_concorrente
            )
            if not existe:
                banco_concorrente.append(registro)
                sucessos += 1
            else:
                duplicidades += 1

    latencia_ms = round((time.perf_counter() - inicio) * 1000, 2)
    return {"avaliador": avaliador_idx, "sucessos": sucessos, "duplicidades": duplicidades, "latencia_ms": latencia_ms}

def test_cinco_avaliadores_concorrentes():
    """Dispara 5 avaliadores em paralelo e mede integridade e latência."""
    banco_concorrente.clear()
    num_avaliadores = 5

    with ThreadPoolExecutor(max_workers=num_avaliadores) as executor:
        futuros = [executor.submit(simular_gravacao_avaliador, i) for i in range(1, num_avaliadores + 1)]
        resultados = [f.result() for f in futuros]

    # 5 avaliadores x 3 testes cada = 15 registros exatos, zero perdas e zero duplicações
    assert len(banco_concorrente) == 15
    assert all(r["sucessos"] == 3 for r in resultados)
    assert all(r["duplicidades"] == 0 for r in resultados)
    assert max(r["latencia_ms"] for r in resultados) < 1000