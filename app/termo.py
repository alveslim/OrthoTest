"""Termo de Consentimento Livre e Esclarecido (TCLE) simplificado, mostrado ao participante no app.

Fonte única do texto: a tela de novo participante, o formulário impresso do Plano B
(docs/termo_consentimento.md, gerado por `python scripts/gerar_termo.py`) e a versão gravada no
banco (`participantes.termo_versao`) saem daqui. Mudou o texto? Mude TERMO_VERSAO.
"""
from config import cfg

TERMO_VERSAO = "2026-11-v1"
TITULO = "Termo de Consentimento Livre e Esclarecido"


def _contato() -> str:
    # Opcional: TERMO_CONTATO="Prof.ª Fulana, fulana@exemplo.edu.br" no .env
    c = cfg("TERMO_CONTATO").strip()
    return f" ({c})" if c else ""


def secoes() -> list[tuple[str, str]]:
    return [
        ("O que é esta atividade",
         "Atividade de extensão de estudantes de Fisioterapia da Universidade Nilton Lins, na disciplina de "
         "Semiologia e Diagnóstico Cinesiológico-Funcional. A finalidade é exclusivamente educativa: os estudantes "
         "praticam testes ortopédicos especiais sob supervisão."),
        ("O que será feito",
         "Um estudante aplicará alguns testes ortopédicos (movimentos, compressões ou trações leves em joelho, "
         "tornozelo, quadril, ombro, cotovelo, punho e coluna) e anotará o resultado de cada um, a dor que você "
         "sentir de 0 a 10 e dados simples: idade, peso e altura. Leva poucos minutos."),
        ("Desconfortos possíveis",
         "Pode haver desconforto ou dor leve e passageira durante os testes. Avise na hora e o teste será "
         "interrompido. Informe ao estudante se tem lesão recente, dor forte ou cirurgia na região."),
        ("Não é diagnóstico",
         "Os resultados não confirmam lesão nem indicam ausência de alteração, e não substituem a avaliação de "
         "um fisioterapeuta ou médico. Se tiver sintomas, procure um profissional de saúde."),
        ("Sua participação é voluntária",
         "Você pode recusar ou parar a qualquer momento, sem prejuízo algum. Enquanto o projeto estiver ativo, "
         "pode pedir a exclusão dos seus dados."),
        ("Privacidade dos seus dados (LGPD)",
         "Você é identificado(a) por um código (ex.: P-007). Nome e sobrenome são opcionais e servem só para o "
         "avaliador localizar a sua ficha: não aparecem em relatórios, no painel nem em apresentações, e nunca "
         "são enviados à inteligência artificial. O painel mostra apenas números de grupos com 3 ou mais pessoas. "
         "A IA, quando usada, só redige um rascunho com dados sem identificação, revisado por um professor."),
        ("O que acontece com os dados depois",
         "Ao fim do projeto, os dados individuais são apagados. Ficam apenas resultados agrupados, sem "
         "identificação de ninguém."),
        ("Menores de 18 anos",
         "O responsável legal precisa estar ciente e de acordo com a participação."),
        ("Dúvidas",
         f"Procure o(a) professor(a) responsável pela atividade{_contato()}."),
    ]


DECLARACAO = ("Li (ou foi lido para mim) este termo, tive a chance de tirar dúvidas e aceito participar "
              "voluntariamente.")
DECLARACAO_RESPONSAVEL = "O responsável legal está ciente e de acordo com a participação do menor de 18 anos."


def termo_markdown() -> str:
    linhas = [f"# {TITULO}", "", f"_Versão {TERMO_VERSAO}_ · Projeto OrthoTest · Universidade Nilton Lins", ""]
    for titulo, texto in secoes():
        linhas += [f"## {titulo}", "", texto, ""]
    linhas += [
        "## Declaração", "", f"- [ ] {DECLARACAO}", f"- [ ] {DECLARACAO_RESPONSAVEL} _(só se for menor de 18 anos)_", "",
        "Código do participante: ____________  Data: ____ / ____ / ________", "",
        "Nome (opcional): ______________________________________", "",
        "Assinatura (ou rubrica) do participante ou responsável: ______________________________", "",
        "Avaliador(a): ______________________________",
        "",
    ]
    return "\n".join(linhas)
