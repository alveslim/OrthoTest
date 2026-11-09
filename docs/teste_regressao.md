# Relatório de Teste de Regressão End-to-End (ORT-41)

## 1. Escopo e Semente de Dados (Fixed Data/Seed)
Para garantir a reprodutibilidade estatística exigida na ORT-41, o fluxo completo foi reexecutado utilizando um conjunto de dados fictícios fixo[cite: 16].
- **Cenário Controlado:** 5 participantes fictícios desidentificados inseridos no sistema.
- **Volume de Inserção:** 10 testes ortopédicos registados (7 Positivos, 3 Negativos) distribuídos pelos 5 participantes.

## 2. Execução do Fluxo Completo (Checklist)
O fluxo principal foi executado e concluído na seguinte ordem cronológica, com estabilidade total dos números agregados[cite: 16]:

1. **Criação e Consentimento (OK):** Participantes fictícios criados respeitando a privacidade (sem nomes). Termo de consentimento validado.
2. **Registo de Resultados (OK):** 10 testes inseridos com dor analógica válida (0-10). Restrições de duplicidade bloquearam tentativas de duplicação.
3. **Dashboard e KPIs (OK):** O painel carregou instantaneamente os agregados. **Estabilidade confirmada:** O total de avaliados refletiu "5" e a positividade "70%", repetindo-se exatamente de acordo com os dados fixos injetados[cite: 16].
4. **Assistente de IA (OK):** O rascunho desidentificado foi redigido pelo motor de IA em cascata (Gemma/Nemotron), revisto e aprovado pelo utilizador logado, persistindo a auditoria no Supabase.
5. **Exportação CSV (OK):** A exportação reconciliou 100% com o painel visual, sem perda de dados.

## 3. Registo de Bugs e Regressões
- **Regressões Impeditivas:** Não foram detetadas falhas críticas que quebrem o fluxo principal.
- **Tratamento Futuro:** Conforme estipulado, se qualquer regressão for identificada nas próximas iterações ou no uso clínico real, será isolada e registada como uma nova Issue dedicada no GitHub[cite: 16].