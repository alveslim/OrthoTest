# Status e progresso da avaliação

O total de testes esperados vem dos IDs do catálogo consultado. Não há um total fixo no cálculo.

Para uma avaliação, cada teste do catálogo com resultado preenchido conta uma vez, mesmo que haja registros de lados diferentes. Positivo, Negativo, Não realizado e Inconclusivo contam como respondidos. Registros de outra avaliação ou de testes fora do catálogo não contam.

O status é Completo somente quando existe ao menos um teste esperado e todos foram respondidos. Caso contrário, é Incompleto. O progresso segue o formato "2 de 4 testes".

A função `backend.progresso.calcular_progresso` recebe os testes e resultados para calcular esses valores. A integração que consultará os registros persistidos e devolverá o cálculo na API ainda depende dos endpoints da ORT-13. O cliente não deve enviar nem gravar o status calculado.