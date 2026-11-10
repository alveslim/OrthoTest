# Publicar o OrthoTest (API na internet + app no celular)

Três peças: **API** (Vercel), **app Android** (APK) e **app para iPhone** (versão web instalada na tela
inicial). O banco já está no Supabase.

## 1. Hospedar a API

| Opção | Vale a pena? |
|---|---|
| **Vercel** (recomendado) | Grátis, deploy direto do GitHub, sem cartão. API leve e sem estado, então combina. Primeira chamada após ficar parado pode levar 1 a 3 s. O resumo por IA pode levar até 40 s: já deixei o limite em 60 s no `vercel.json`. |
| Render (plano grátis) | Funciona, mas a API "dorme" e a primeira chamada leva cerca de 50 s. Ruim para apresentação ao vivo. |
| Railway / Fly | Pedem cartão ou créditos. Sem vantagem para este projeto. |
| Cloudflare Workers | Não: a API é Python com `requests`. |

**Passo a passo no Vercel**
1. Em vercel.com: *Add New → Project* → importe `alveslim/orthotest`. *Framework Preset*: **Other**. Raiz: `.`.
2. O Vercel publica em produção a branch principal. Faça o merge do PR na `main` antes (ou, em *Settings → Git*, troque a *Production Branch*).
3. Em *Settings → Environment Variables*, crie:
   - `SUPABASE_URL` = `https://ddlkfevmmpuofyrghfni.supabase.co`
   - `SUPABASE_ANON_KEY` = a chave **publishable** (veja a seção 2)
   - `CORS_ORIGINS` = endereço da versão web do app (seção 4), se for usar; separe vários por vírgula
   - (opcional) `NVIDIA_API_URL`, `NVIDIA_API_KEY`, `NVIDIA_MODEL` para a IA. Sem isso o resumo sai das regras locais.
4. *Deploy*. Teste abrindo `https://SEU-PROJETO.vercel.app/health`: deve responder `{"status":"ok",...}`.
   Se pedir login da Vercel, desligue *Settings → Deployment Protection → Vercel Authentication* para o ambiente de produção.
5. Abra `app/config_publica.json` e preencha:
   `"API_BASE_URL": "https://SEU-PROJETO.vercel.app/api/v1"`. Faça commit e gere o app de novo.

## 2. Onde buscar as chaves (Supabase)
Dashboard do Supabase → projeto **orthotest** → *Project Settings → API Keys*:
- **Project URL**: `https://ddlkfevmmpuofyrghfni.supabase.co`
- **Publishable key** (`sb_publishable_...`): pode ir no app e na Vercel.
- **Secret / service_role**: NUNCA no app, no GitHub nem na Vercel. O OrthoTest não usa essa chave.

`app/config_publica.json` já vem com a URL e a publishable key deste projeto. No computador, o `.env`
continua valendo e tem prioridade sobre esse arquivo.

## 3. Android (APK)
Pré-requisito: Python 3.10+ e `pip install -r requirements-app.txt`. O `flet build` baixa Flutter e o SDK do Android na primeira vez (demora e usa alguns GB).
```bash
flet build apk
```
O arquivo sai em `build/apk/`. Envie ao celular, abra e permita instalar de fontes desconhecidas.
Para a Play Store: `flet build aab` e conta de desenvolvedor Google (taxa única de uns US$ 25).

## 4. iPhone (sem Mac e sem pagar): versão web na tela inicial
```bash
flet build web
```
Publique a pasta `build/web` como site estático: Cloudflare Pages (*Workers & Pages → Create → Pages → Upload assets*) ou um segundo projeto no Vercel (*Other*, sem build, diretório de saída `build/web`).
Depois: coloque o endereço do site em `CORS_ORIGINS` na Vercel (a versão web chama a API de outro endereço) e faça *Redeploy*.

No iPhone: abra o endereço no **Safari** → *Compartilhar* → **Adicionar à Tela de Início**.

Pontos de atenção da versão web (não foram testados em aparelho real):
- Login salvo e fila offline usam o `localStorage` do navegador. Se o navegador não oferecer, ficam só na memória da aba: o app funciona, mas pede login a cada abertura e a fila se perde ao fechar. Teste isso primeiro.
- O primeiro carregamento é lento (o navegador baixa o Python).
- Se a tela entrar mas o login falhar com erro de rede, o `requests` não está funcionando no navegador: me envie o erro.
- Para iPhone com app de verdade (instalável, com tudo offline): precisa de Mac, Xcode e conta Apple Developer (US$ 99/ano): `flet build ipa` e TestFlight.

## 5. Conferir depois de publicar
1. `/health` da API responde ok.
2. Login com um usuário criado no Supabase (*Authentication → Users*).
3. Cadastrar participante com o termo, salvar um teste.
4. Ligar o modo avião, salvar outro teste, desligar, tocar em sincronizar e conferir no Supabase (*Table Editor → resultados_testes*).
