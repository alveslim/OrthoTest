# Dados fictícios para desenvolvimento

O arquivo `dados_ficticios/amostra.json` é produzido por `dados_ficticios/gerar_dados.py`. Todos os registros são artificiais; não representam participantes ou resultados clínicos reais.

## Como gerar

Na raiz do projeto, no PowerShell, execute `.\.venv\Scripts\python.exe dados_ficticios\gerar_dados.py`.

A semente fixa é `42`. Executar novamente no mesmo ambiente produz o mesmo arquivo. O gerador não acessa o Supabase.

## Conteúdo

- `metadados`: identifica o conjunto como fictício e informa a semente.
- `participantes`: 60 códigos de `P-001` a `P-060`, sem nome ou contato. Idade, peso e altura são inventados.
- `testes_catalogo`: identificadores e nomes dos 16 testes do README. As definições clínicas completas pertencem à issue do catálogo.
- `avaliacoes`: uma avaliação por participante, ligada pelo código.
- `resultados_testes`: registros ligados aos identificadores da avaliação e do teste, com lado, resultado e dor de 0 a 10 quando realizado.

As datas e o consentimento são simulados para exercitar o fluxo do aplicativo. As primeiras 12 avaliações têm registros para os 16 testes; as demais deixam testes pendentes. Um resultado `Não realizado` é diferente de um teste sem registro.

A distribuição dos resultados serve apenas para variar os exemplos do aplicativo. Ela não representa frequência clínica e não deve ser usada para diagnóstico.

## Verificação

Na raiz do projeto, execute `.\.venv\Scripts\python.exe -m pytest -q tests\test_gerar_dados.py`.