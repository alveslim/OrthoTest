# Identidade visual do OrtoCheck

Referência visual: OrtoCheck - Design do app.pdf.

## Cores

| Uso | Token em `app/theme.py` | Cor |
| --- | --- | --- |
| Azul principal | `PRIMARY` | `#1659B2` |
| Fundo das telas | `BACKGROUND` | `#F7F8FC` |
| Superfície dos cards | `SURFACE` | `#FFFFFF` |
| Borda discreta dos cards | `CARD_BORDER` | `#DFE6EE` |
| Texto principal | `TEXT_PRIMARY` | `#152231` |
| Texto secundário | `TEXT_SECONDARY` | `#42556D` |

O tema Flet usa Material 3, modo claro e `PRIMARY` como cor-semente.

## Tipografia

A família de fonte é a padrão do tema Material 3 no Flet; não há fonte personalizada no projeto.

| Uso | Estilo Flet | Tamanho | Peso | Cor padrão |
| --- | --- | ---: | --- | --- |
| Cabeçalho da tela | `HEADLINE_MEDIUM` | 28 | Negrito | `TEXT_PRIMARY` |
| Título do card | `TITLE_LARGE` | 20 | Negrito | `TEXT_PRIMARY` |
| Texto comum | `BODY_MEDIUM` | 14 | Padrão | `TEXT_PRIMARY` |
| Texto de apoio | `BODY_SMALL` | 12 | Padrão | `TEXT_SECONDARY` |

A cor de um texto pode ser ajustada conforme sua função: na prévia, os dados do participante usam `TEXT_SECONDARY` e o progresso usa `PRIMARY`.

## Contraste medido

| Texto | Fundo | Relação |
| --- | --- | ---: |
| Branco `#FFFFFF` | Azul `#1659B2` | 6,76:1 |
| Azul `#1659B2` | Branco `#FFFFFF` | 6,76:1 |
| Principal `#152231` | Branco `#FFFFFF` | 16,09:1 |
| Secundário `#42556D` | Branco `#FFFFFF` | 7,63:1 |
| Secundário `#42556D` | Fundo `#F7F8FC` | 7,19:1 |

As combinações de texto acima superam 4,5:1. A borda cinza do card é decorativa e não deve ser usada como texto nem como única indicação de um estado.
