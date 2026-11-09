# Relatório Executivo Final — Projeto OrthoTest (ORT-48)

## 1. Visão Geral e Resultados Agregados (Dados Fictícios de Homologação)
O **OrthoTest** é uma plataforma clínica-académica desenvolvida em FastAPI, Flet e Supabase para padronizar o registo de manobras ortopédicas. Na bateria de homologação controlada, foram avaliados **12 participantes simulados** (75,0% de avaliações concluídas; dor média geral de **4,2/10**). Os testes "Não realizados" foram estritamente excluídos dos denominadores estatísticos. Respeitando a regra de privacidade de **K-Anonimato ($n < 3$)**, grupos com menos de 3 indivíduos foram fundidos na categoria *"Outros (Privacidade < 3)"*, resultando nas seguintes taxas de positividade: **Joelho (65,0%)**, **Ombro (20,0%)** e **Outros (15,0%)**. **Nota importante:** Nenhum resultado percentual ou achado apresentado pelo sistema constitui diagnóstico médico definitivo[cite: 23].

## 2. Limitações da Coleta Clínica
- **Natureza Académica e Amostral:** Os dados recolhidos durante os testes e simulações têm caráter estritamente pedagógico, não possuindo validade epidemiológica populacional[cite: 23].
- **Variabilidade Inter-Avaliador:** Apesar da padronização dos formulários e catálogos, a execução física das manobras ortopédicas (ex: Lachman, Neer) e a percepção subjetiva da escala de dor (0–10) estão sujeitas à experiência técnica de cada estudante avaliador[cite: 23].

## 3. Limitações do Sistema
- **Dependência de Infraestrutura e Sincronização:** Embora o sistema conte com fila de contingência offline (ORT-42) e formulário impresso de Plano B (ORT-43), a consolidação em tempo real no painel depende de conectividade HTTPS com o Supabase[cite: 23].
- **Escopo Estático da Base Clínica:** O motor determinístico reconhece apenas os testes previamente mapeados em `ai/regras_clinicas.json`, exigindo atualização manual da base bibliográfica quando novos testes são inseridos no catálogo[cite: 23].

## 4. O Papel da Inteligência Artificial (O que Fez vs. O que Não Fez)
A arquitetura de IA foi desenhada sob o princípio **Human-in-the-Loop (Humano no Comando)**[cite: 23]:
- **O que a IA FEZ:** Atuou exclusivamente como redatora assistente. A partir dos achados rastreáveis gerados pelo motor de regras Python (baseados em literatura como *Magee* e *Dutton*) e de dados estritamente desidentificados (Idade, Peso e Altura), o motor híbrido (Ollama Gemma local + fallback NVIDIA Nemotron) estruturou rascunhos textuais para discussão académica, exigindo revisão, edição e aprovação explícita de um utilizador autenticado (`revisado_por`)[cite: 23].
- **O que a IA NÃO FEZ:** A IA **jamais** recebeu nomes ou dados identificáveis; **não** inventou referências clínicas fora do JSON validado; **não** prescreveu tratamentos, exames ou medicamentos; e **nunca** confirmou diagnósticos clínicos autonomamente[cite: 23].