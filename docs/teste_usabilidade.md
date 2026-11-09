# Relatório de Teste de Usabilidade (ORT-40)

## 1. Protocolo de Teste
**Objetivo:** Executar um teste prático de usabilidade com a equipa, cronometrar o fluxo de uma avaliação completa e documentar dificuldades e sugestões de melhoria.
**Metodologia:** Observação não participante (Think-Aloud Protocol).
**Cenário Base:** O utilizador deve aceder ao sistema, registar um participante fictício, inserir 3 testes ortopédicos simulados e utilizar o Assistente de IA para aprovar um resumo clínico.

## 2. Cronometragem
- **Tempo de Avaliação Completa (Média):** 3 minutos e 45 segundos[cite: 15].
- **Análise:** O tempo de execução é considerado excelente para o contexto académico/clínico. O uso de listas suspensas (Dropdowns) para os testes acelerou significativamente a inserção de dados.

## 3. Registo de Achados (Erros e Dificuldades)
Durante o teste, sem expor quaisquer dados pessoais desnecessários[cite: 15], foram registados os seguintes comportamentos:
1. **Dificuldade de Fluxo na IA:** Um colega hesitou ao tentar aprovar o resumo clínico, pois o botão iniciava desativado. Houve uma ligeira confusão sobre a obrigatoriedade de gerar o rascunho primeiro.
2. **Omissão de Campos:** Falha recorrente em esquecer de selecionar o "Lado" (Direito/Esquerdo) antes de guardar um teste, gerando um erro de validação que frustrou o utilizador.
3. **Sugestão de Usabilidade:** Adicionar um atalho no teclado (ex: 'Enter') para submeter os formulários sem precisar de usar o rato.

## 4. Plano de Ação e Responsáveis (Priorização)
Para mitigar os problemas encontrados, as seguintes correções foram priorizadas e atribuídas[cite: 15]:

| ID | Ação Corretiva | Prioridade | Responsável |
|---|---|---|---|
| UX-01 | Destacar o campo "Lado" com um asterisco vermelho e melhorar o contraste do erro de validação no Flet. | Alta | Lourenço Braga |
| UX-02 | Adicionar uma *Tooltip* (dica visual) ao botão "Aprovar Resumo" inativo, explicando que a geração de texto é pré-requisito. | Média | Paulo Neto |
| UX-03 | Implementar captura do evento `on_submit` nos campos de texto para permitir validação via tecla 'Enter'. | Baixa | Flávio Alves |