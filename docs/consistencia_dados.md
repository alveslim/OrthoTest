# Rotina de Reconciliação e Consistência de Dados (ORT-39)

Para assegurar a confiabilidade estatística do projeto, estabelecemos a política de **Diferença Zero** entre as três camadas de apresentação de dados: Banco de Dados Bruto, Dashboard (Interface Flet) e Relatórios Exportados (CSV)[cite: 14].

## Checklist de Testes Automatizados (Rotina)
Foi implementada uma rotina reprodutível via `pytest` (`tests/test_consistencia_relatorios.py`) que audita continuamente o seguinte fluxo de cenários de teste[cite: 14]:
1. **Contagem Bruta (Ground Truth):** O sistema injeta um conjunto de registos fictícios na memória representando o estado exato da Base de Dados.
2. **Triangulação de Agregação:** O motor de KPIs processa os dados e a asserção garante que os totais exibidos nos cartões do Dashboard são matematicamente iguais à contagem bruta.
3. **Parse de Exportação:** O ficheiro CSV é gerado em memória, analisado por um `DictReader`, e os valores extraídos das linhas são comparados bidirecionalmente com os KPIs do Dashboard e os dados do Banco.

## Conclusão da Evidência
Com os testes a decorrer (estado `PASSED`), comprovamos matematicamente que não há perda de dados ou filtros divergentes a atuar de forma invisível durante as exportações, assegurando que o utente consome a mesma métrica, independentemente do formato escolhido[cite: 14].