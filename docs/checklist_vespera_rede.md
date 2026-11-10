# Checklist de Verificação de Véspera e Conectividade de Rede (ORT-44)

## 1. Status de Execução (Véspera)
- [x] **Projeto Supabase Ativo:** Confirmado no painel administrativo que o banco não está em modo `Paused`.
- [x] **Teste de Autenticação (JWT):** Login de avaliador de teste efetuado com sucesso na rede alvo[cite: 19].
- [x] **Teste de Leitura e Escrita:** Leitura do catálogo e gravação de avaliação fictícia executadas via porta HTTPS (443), sem bloqueio de Firewall na rede da universidade[cite: 19].
- [x] **Diagnóstico Automatizado:** Script `python scripts/check_vespera.py` executado com retorno `[OK]` e latência estável (< 350ms).

## 2. Plano de Contingência de Rede e Contactos
Caso a rede Wi-Fi institucional sofra degradação durante o evento:
1. **Contingência Nível 1 (Hotspot 4G/5G):** Ligar roteamento móvel do smartphone principal da equipa (Portas 443 e 8000 abertas).
2. **Contingência Nível 2 (Modo Offline App):** O app já continua sem internet sozinho (fila local, ORT-42): confira antes que cada avaliador **entrou uma vez com internet** e, ao voltar a rede, toque em sincronizar. Não use `MODO_DEMO` em avaliações reais.
3. **Contingência Nível 3 (Plano B Físico):** Distribuir as fichas impressas elaboradas na ORT-43.

### Contactos de Emergência Técnica (Equipa)
- **Infraestrutura / Backend / Supabase:** Flávio Alves
- **Suporte de Bancada e Operação:** Lourenço Braga / Paulo Neto