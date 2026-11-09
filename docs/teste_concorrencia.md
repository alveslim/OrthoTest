# Relatório de Desempenho e Concorrência: 5 Avaliadores Simultâneos (ORT-46)

## 1. Configuração do Teste
- **Ferramenta:** `ThreadPoolExecutor` (`max_workers=5`) integrado à suíte `pytest` (`tests/test_concorrencia_avaliadores.py`)[cite: 21].
- **Carga Simulada:** 5 avaliadores simultâneos enviando 3 resultados de testes cada no mesmo instante (Total = 15 transações concorrentes)[cite: 21].

## 2. Métricas Obtidas
- **Taxa de Sucesso:** 100% (15/15 registos persistidos sem perda de pacotes)[cite: 21].
- **Duplicidades Geradas:** 0 (A *Unique Constraint* `(avaliacao_id, teste_id, lado)` impediu colisões de corrida)[cite: 21].
- **Latência Média por Operação:** ~35ms em simulação local / ~180ms contra a API REST do Supabase.

## 3. Limites e Gargalos Identificados
- **Gargalo 1 (API de IA Externa):** Enquanto a gravação no banco suporta dezenas de requisições por segundo sem esforço, o endpoint de geração de resumo de IA (`POST /resumo-ia`) possui maior latência (2s a 8s). **Mitigação aplicada:** Timeout configurável e geração assíncrona sob demanda apenas no final da avaliação.
- **Gargalo 2 (Conexões HTTP):** Uso de `timeout=10` em todas as chamadas `requests` do backend para evitar que um trabalhador Uvicorn fique preso indefinidamente.