# Arquitetura e Segurança do Módulo de IA (ORT-35)

Este documento detalha a infraestrutura adotada para o módulo de Inteligência Artificial do OrthoTest, assegurando a proteção de dados sensíveis e a robustez do sistema.

## 1. Opção de Infraestrutura
Em vez de expor endpoints provisórios (ex: Colab + ngrok), o grupo optou por uma **Arquitetura Híbrida em Cascata (High Availability)**:
1. **Motor Primário (Local):** Ollama a correr o modelo `gemma`. Processamento 100% offline, zero latência de rede externa.
2. **Motor Secundário (Nuvem):** NVIDIA API a correr `nemotron-4-340b-instruct`. Usado apenas como *fallback* se o motor local falhar.
3. **Safe Fallback:** Se ambos falharem, o sistema devolve um erro tratado na interface Flet, sem corromper a aplicação.

## 2. Autenticação e Gestão de Segredos
- O endpoint da nuvem (NVIDIA) exige autenticação rigorosa. A comunicação é feita injetando o token no cabeçalho HTTP: `headers={"Authorization": f"Bearer {chave_nvidia}"}`.
- **Proteção de Segredos:** A chave de API está estritamente guardada no ficheiro `.env` local. Este ficheiro foi adicionado ao `.gitignore` para garantir que os segredos ficam fora do controlo de versão.

## 3. Minimização e Desidentificação de Dados (Privacy by Design)
Os payloads enviados para o serviço de IA foram rigorosamente minimizados:
- **O que é enviado:** Apenas dados antropométricos genéricos (Idade, Peso, Altura) e a lista de achados clínicos textuais.
- **O que NUNCA é enviado:** Nomes, códigos de utente, contactos ou qualquer dado diretamente identificável do participante.
- Todo o *prompt* contém diretivas estritas que proíbem a IA de confirmar diagnósticos.