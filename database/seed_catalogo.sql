-- 1 · Lachman (LCA)
INSERT INTO testes_catalogo (id, regiao, nome, estrutura, definicao, objetivo,
  como_fazer, positivo_se, referencia)
VALUES (
  1,
  'Joelho',
  'Lanchman',
  'LCA',
  'O teste de Lachman é um teste clínico utilizado para avaliar a integridade e a estabilidade do ligamento cruzado anterior (LCA) do joelho. É considerado um dos principais testes para investigação de lesões do LCA, pois permite avaliar a translação anterior da tíbia em relação ao fêmur com o joelho em pequena flexão. É especialmente utilizado em casos de trauma esportivo, entorses e episódios de instabilidade do joelho.',
  'Verificar a presença de instabilidade anterior do joelho, identificando alterações na contenção da tíbia proporcionada pelo LCA. O teste auxilia na investigação de rupturas parciais ou completas do ligamento cruzado anterior, principalmente após mecanismos de trauma envolvendo rotação ou mudança brusca de direção.',
  'Paciente em decúbito dorsal, com o joelho relaxado e flexionado aproximadamente entre 20° e 30°. O examinador estabiliza o fêmur com uma das mãos e segura a região proximal da tíbia com a outra. Em seguida, realiza uma tração anterior da tíbia, observando a quantidade de deslocamento e a qualidade do ponto final do movimento. O resultado deve ser comparado com o membro contralateral.',
  'O teste é considerado positivo quando ocorre aumento da translação anterior da tíbia em relação ao fêmur, principalmente quando comparado ao lado saudável. Também pode ser observado um ponto final amolecido ou pouco firme, além de sensação de instabilidade. Esses achados são sugestivos de lesão ou insuficiência do ligamento cruzado anterior (LCA).',
  NULL
);
-- Gaveta Anterior (LCA)
INSERT INTO testes_catalogo (id, regiao, nome, estrutura, definicao, objetivo, como_fazer, positivo_se, referencia)
VALUES (
  2,
  'Joelho',
  'Gaveta Anterior',
  'LCA',
  'O teste de Gaveta Anterior é um teste clínico utilizado para avaliar a estabilidade anterior do joelho, principalmente a integridade do ligamento cruzado anterior (LCA). O LCA atua limitando o deslocamento anterior excessivo da tíbia em relação ao fêmur, sendo fundamental para a estabilidade do joelho durante atividades como corrida, saltos e mudanças de direção.',
  'Verificar se existe deslocamento anterior excessivo da tíbia, auxiliando na identificação de possíveis lesões ou insuficiência do LCA. O teste pode ser utilizado após traumas esportivos, entorses do joelho ou quando o paciente apresenta sensação de falseio ou instabilidade.',
  'Paciente em decúbito dorsal, com o quadril e o joelho flexionados, mantendo o joelho aproximadamente a 90°. O examinador estabiliza o pé do paciente e segura a região proximal da tíbia com as duas mãos. Em seguida, realiza uma tração da tíbia para frente, avaliando a quantidade de deslocamento anterior em relação ao fêmur. O movimento deve ser comparado com o membro contralateral.',
  'É considerado positivo quando ocorre translação anterior excessiva da tíbia, maior do que a observada no membro contralateral, podendo estar associada a uma sensação de instabilidade ou ponto final pouco firme. Esse resultado pode indicar lesão ou insuficiência do ligamento cruzado anterior.',
  NULL
);
 
-- 3 · Estresse em Valgo (LCM)
INSERT INTO testes_catalogo (id, regiao, nome, estrutura, definicao, objetivo, como_fazer, positivo_se, referencia)
VALUES (
  3,
  'Joelho',
  'Estresse em Valgo',
  'LCM',
  'O teste de estresse em Valgo é um teste clínico utilizado para avaliar principalmente a integridade do ligamento colateral medial (LCM) do joelho. O LCM contribui para a estabilidade medial da articulação, especialmente contra forças que tendem a deslocar o joelho para uma posição de valgo.',
  'Avaliar a estabilidade medial do joelho e identificar sinais compatíveis com lesão ou frouxidão do LCM. O teste é utilizado principalmente após traumas que provocam uma força de valgo, como impactos na região lateral do joelho.',
  'Paciente em decúbito dorsal. O examinador estabiliza a região lateral do joelho e segura a perna distalmente. Aplica-se uma força direcionada de lateral para medial, provocando o estresse em valgo. O teste pode ser realizado com o joelho em extensão e também aproximadamente entre 20° e 30° de flexão, permitindo avaliar diferentes componentes da estabilidade medial.',
  'O teste é considerado positivo quando há dor na região medial do joelho, associada ou não à abertura excessiva do espaço articular medial em comparação com o membro contralateral. A presença de frouxidão aumentada pode indicar lesão do ligamento colateral medial, sendo a extensão da abertura um possível indicativo da gravidade da instabilidade.',
  NULL
);
 
-- 4 · Estresse em Varo (LCL)
INSERT INTO testes_catalogo (id, regiao, nome, estrutura, definicao, objetivo, como_fazer, positivo_se, referencia)
VALUES (
  4,
  'Joelho',
  'Estresse em Varo',
  'LCL',
  'O teste de Estresse em Varo é utilizado para avaliar principalmente a integridade do ligamento colateral lateral (LCL) do joelho. Esse ligamento auxilia na estabilização da parte lateral da articulação, limitando movimentos excessivos provocados por forças em varo.',
  'Verificar a estabilidade lateral do joelho e identificar sinais de lesão ou frouxidão do LCL. É especialmente utilizado após traumas que provocam uma força direcionada para o varo, podendo ocorrer em atividades esportivas ou acidentes.',
  'Paciente em decúbito dorsal. O examinador estabiliza a região medial do joelho e segura a parte distal da perna. Em seguida, aplica uma força de medial para lateral, produzindo o estresse em varo. O teste pode ser realizado com o joelho em extensão e aproximadamente entre 20° e 30° de flexão, comparando-se o movimento com o membro contralateral.',
  'O teste é considerado positivo quando apresenta dor na região lateral do joelho e/ou abertura excessiva do espaço articular lateral em comparação ao lado oposto. Esses achados podem indicar lesão ou insuficiência do ligamento colateral lateral, podendo também sugerir comprometimento de outras estruturas estabilizadoras laterais quando a instabilidade é significativa.',
  NULL
);