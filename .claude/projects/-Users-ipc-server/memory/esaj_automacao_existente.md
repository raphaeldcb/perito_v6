---
name: esaj-automacao-existente
description: Bruno JÁ construiu a automação eSAJ completa (A3) — protocolo_v21.py + intimacoes_v7.py; base do agente Windows
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Automação eSAJ já existe (achado 09/07/26) — NÃO precisa filmar/refazer

## ⚠️⚠️ ACESSO: MAC × WINDOWS são DIFERENTES (NUNCA misturar/quebrar)
O MESMO arquivo `intimacoes_v7.py` roda nas 2 máquinas, com login DIFERENTE por TAREFA:
- **WINDOWS = A3 (certificado/WebSigner)** → RECEBER intimações (tomar ciência, inicia prazos) + PROTOCOLO.
  Usa a aba "Certificado digital". O `.bat` do Windows NÃO define ESAJ_CPF/ESAJ_SENHA.
- **MAC = CPF/senha + 2FA do e-mail (SEM certificado)** → DOWNLOAD/consulta de autos (pasta digital).
  Ativa via env `ESAJ_CPF`/`ESAJ_SENHA` (senha=Bruno@841124). Perfil LOCAL `~/perito_chrome_esaj`.
- O `garantir_login` decide pelo env: se ESAJ_CPF+ESAJ_SENHA existem → CPF/senha (Mac); senão → A3 (Windows).
  Por isso as 2 coexistem: mexer no caminho CPF/senha NÃO afeta o A3 do Windows (gated no env). NÃO quebrar isso.


Pasta: `~/Library/CloudStorage/OneDrive-...IPCMSPERICIASLTDA/IPCMS - GERENCIA/DIRETORIA/Testes IA/ESAJBrunoFigueiredo/`

Bruno já tem a automação eSAJ COMPLETA e funcionando (Selenium + WebSigner + A3):

- **`intimacoes_v7.py`** (1065 ln): login por certificado A3 (`sajcas/login#aba-certificado`,
  `#submitCertificado`), **espera o PIN do A3** (lógica das 8h — antes das 8h espera 30s pelo PIN),
  consulta `abrirConsultaAtosNaoRecebidos.do`, marca e **RECEBE (dá ciência)**. JÁ lê o 2FA do
  v6 via `GET /api/v1/esaj/codigo-2fa` (endpoint EXISTE em `routes/esaj.py`, usa graph_mail).
- **`protocolo_v21.py`** (1080 ln): protocolo completo com WebSigner. Perfil Chrome persistente
  (`chrome_profile/` mantém a sessão 8h), upload PDF, nº processo via clipboard (Ctrl+V, máscara
  Angular rejeita send_keys), classificação (3 cliques), marca IPC como peticionante, Protocolar
  (click NATIVO), comprovante via CDP Page.printToPDF. Tem `DEBUG_MODE` (dry-run seguro).
- **`CONTINUIDADE.md`**: decisões técnicas (truques Angular/ng-if/stale element, códigos de
  classificação: 38369=Laudo, 8822=Manifestação Perito).
- Deps: `selenium pyperclip PyPDF2`. Estrutura espera `MS_login.txt`/`MS_password.txt`, `cnpj.txt`,
  `Web Signer 2.14.3.0.crx`, pastas PDF/oficios/laudos/protocolos.
- Também `Testes IA/Captura intimação/` tem automatizadores TJMS em Node (tjms-automatizador-*.js).

## Agente construído (09/07/26) — na pasta ESAJBrunoFigueiredo/
- `esaj_protocolo.py` = cópia importável do protocolo_v21 (main guardado).
- `agente_perito.py` = loop que puxa jobs protocolo_oficio/protocolo_laudo do VPS,
  baixa o arquivo, chama `protocolar_arquivo` (código do Bruno), reporta. Chave do
  agente = e042f6... (mesma do mac_agent). Nº do protocolo NÃO é raspado — vem por
  e-mail (adm@ipcms.com.br); backend lerá via graph_mail (mesma infra do 2FA). A FAZER.
- `RODAR-AGENTE-PROTOCOLO.bat` (protocolo) e `TESTE-A3-LISTAR-INTIMACOES.bat`
  (intimacoes_v7 --no-receber = modo seguro: loga A3 + lista, sem dar ciência).
- ⚠️ GAP p/ protocolo real: o job serve DOCX; eSAJ precisa PDF. Fechar (converter).
- ⚠️ Selenium só testa no Windows (não dá p/ testar no Mac).

## ✅ RESOLVIDO (10/07) — login A3 do intimacoes_v7 funciona
Após MUITAS tentativas, a causa raiz de tudo: **o chrome_profile estava na OneDrive**
(335MB) → Chrome CRASHAVA (`DevToolsActivePort file doesn't exist`) e perdia o WebSigner.
Correções aplicadas no intimacoes_v7.py:
1. **Perfil LOCAL** (fora da OneDrive) via env `PERITO_CHROME_PROFILE=C:\Users\bruno\perito_chrome`.
2. **Clicar na aba certificado** (`linkAbaCertificado`) — a tela abre em #aba-cpf por padrão.
3. Removidas opções anti-automação (excludeSwitches enable-automation, useAutomationExtension).
4. Suporte a anexar via `PERITO_DEBUG_PORT` (não usado — Chrome bloqueia debug no perfil real).

**Setup que FUNCIONA (Windows):**
- Passo 1 (1x): Chrome COMUM com `--user-data-dir=C:\Users\bruno\perito_chrome` → instalar
  WebSigner pela Web Store → certificado carrega → fechar. (add_extension/.crx NÃO serve —
  eSAJ não reconhece; tem que ser instalado de verdade num perfil LOCAL.)
- Passo 2: `taskkill /IM chrome.exe /F` + env PERITO_CHROME_PROFILE=...perito_chrome +
  `python intimacoes_v7.py` (sem --no-receber para RECEBER de verdade / com --no-receber = só lista).

⚠️ Chrome NÃO deixa automação/debug usar o perfil REAL do usuário (Default) — por isso perfil
dedicado LOCAL + WebSigner instalado nele.

**A FAZER:** (a) ✅ pular download se o PDF já existe (feito); (b) ⚠️ fluxo de RECEBER
(ciência) real — **AINDA NÃO CONFIRMADO**; (c) empurrar recebidas para o Perito v6 + rodar
pipeline_intimacoes (OCR→Qwen→email). Download grande já tem fix de timeout progressivo.

## ✅ RECEBER (ciência) — CONFIRMADO FUNCIONANDO (10/07 12:59)
Reteste 12:59:40 gravou `RECEBIDOS | 25` pela lógica nova (só grava se confirmou) e o
print `DIAG_receber_3_confirmacao_125940.png` mostra a tela de recibo do eSAJ:
**"As seguintes intimações/citações foram recebidos com sucesso:"** + botão "Imprimir
selecionados". Prova cruzada: os mesmos 25 que reapareciam a cada run (porque 10:01/10:13
NÃO tinham recebido de verdade — log incondicional antigo) saíram como recebidos.
Causa do bug: a espera antiga (5s + checagem de URL transitória) fechava o navegador no
meio do POST assinado. Fix que funcionou: esperar `EC.staleness_of(btn_receber)` (até 120s)
= página só troca depois do POST concluir. ⚠️ Dentro das 8h NÃO pede 2ª aprovação no celular
(Bruno confirmou) — a assinatura do WebSigner é silenciosa. Fluxo eSAJ A3 COMPLETO: login +
download (pula já baixados) + RECEBER.

## ✅ (c) CONECTADO ao Perito v6 (10/07) — recebidas entram no painel + pipeline
`intimacoes_v7.py` agora tem `enviar_para_perito(recebidos)`: após a ciência CONFIRMADA,
sobe cada PDF recebido via `POST /api/v1/intimacoes/upload-email?numero_processo=<CNJ>`
(login admin→token; multipart urllib, sem dep nova). O backend cria/acha o Processo, grava
a Intimação `pendente` (aparece no PAINEL) e o worker `analise_qwen` (ANALISE_MODO=agente)
**enfileira a análise pro mac_agent** (Qwen local) → enriquece (área/prazo/resumo) → relatório
diário por e-mail (`workers/relatorios.py`). ⚠️ Pra a ANÁLISE Qwen rodar, o **mac_agent tem
que estar ligado** no Mac; o upload/painel independe disso.
- **Autos são GIGANTES** (até 739MB!). `_pdf_pequeno_para_envio()` fatia as ÚLTIMAS 20/10/5
  páginas (onde está o despacho) num PDF pequeno via pypdf→PyPDF2 antes de subir. Cap 60MB.
- **Fix infra**: o nginx do container `perito-v6-frontend` não tinha `client_max_body_size`
  (default 1MB) → 413/broken pipe. Ajustado p/ **100M** em `v6/frontend/nginx.conf` +
  `proxy_request_buffering off` + timeouts 300s; aplicado live (docker cp + nginx -s reload).
- Testado E2E do Mac: upload 11MB OK → Intimação #870 / Processo #2631 `pendente`.
- `.bat` já tem `PERITO_API_URL=http://129.121.34.186`; RECEBER dá `pip install pypdf` quieto.
- Flags novas: `--no-perito` (não envia), `--no-receber` (não recebe → não envia).

## (histórico) RECEBER — não confirmado até o fix acima
Rodada de 10/07 10:01 gravou `RECEBIDOS | 25` MAS era **log incondicional** (linha 1026
gravava logo após o clique, sem checar). Os prints `DIAG_receber_2/3` provam que a página
**não mudou** — continuou em `receberAtos` com o botão "Receber" cinza. Ou seja: chegou até
a tela final com o cert carregado + 25 marcados, mas **a ciência provavelmente NÃO foi dada**.
Causa provável: botão "Receber" só habilita após a assinatura do WebSigner, e o A3 na nuvem
pode pedir **2ª aprovação no celular** (a 1ª foi só o login) — o script clicava e esperava só 5s.

**Correção aplicada em `receber_selecionados()` (intimacoes_v7.py ~997):**
(1) garante certificado selecionado no combo + dispara `change`;
(2) **espera o botão "Receber" HABILITAR** (loop ~120s — dá tempo da 2ª aprovação no celular);
(3) clica; (4) **confirma de verdade** (espera sair de `receberAtos` OU msg de sucesso, ~90s)
— só grava `RECEBIDOS` se confirmado; senão grava `RECEBER_INCOMPLETO`. Compila OK.

**RETESTE (Bruno, Windows):** rodar `RECEBER-INTIMACOES.bat` e **ficar de olho no celular**
por uma 2ª aprovação do A3 durante o "Receber". Verificação segura: depois, `LISTAR-INTIMACOES.bat`
(--no-receber) — se os processos sumiram da lista de não-recebidos, a ciência foi dada.

## ✅ DOWNLOAD AUTÔNOMO no MAC (CPF/senha + 2FA email) — 11/07, quase pronto
Objetivo: baixar autos dos 1.281 processos no MAC, sem A3, sem Bruno atento (tarefa de fds).
Mecanismo: `pipeline/esaj_dispatcher.baixar_autos_especifico(cnj)` → `esaj_baixar_autos.baixar_autos`
→ reusa `intimacoes_v7` (login CPF/senha via ESAJ_CPF/ESAJ_SENHA + 2FA do email). Rodar no Mac com
perfil LOCAL `~/perito_chrome_esaj` (não OneDrive). Selenium FUNCIONA no Mac (o "não funciona" era do A3).
**Consertos feitos:**
- `garantir_login`: quando há ESAJ_CPF/SENHA, vai DIRETO pro CPF/senha (não ativa aba certificado — era o overlay).
- senha via **JS set value** (não digitação char-a-char — mangla `@`). Senha real: **Bruno@841124** (em MS_password.txt).
- `/api/v1/esaj/codigo-2fa`: era **500** (filtro de data sem Z / caixa). Agora robusto: tenta várias caixas
  (adm@/ipcms@/bruno@), nunca 500. **Testado: retorna o código** (achou em adm@ipcms.com.br). ✅ AUTO-2FA OK.
- Sessão persiste 8h → "já logado" nas próximas (1 login por sessão p/ o lote todo).
## ✅✅✅ DOWNLOAD EM MASSA RODANDO (11/07 14:25) — as 2 descobertas finais
1. **Bloqueador era POP-UP** (Bruno achou): pasta digital abre por window.open → Chrome bloqueava →
   "nova aba não abriu". Fix: `--disable-popup-blocking` nas Options do `_iniciar_driver_sem_crx`.
2. **O "travado" era só o "Aguardando geração do PDF (até 600s)"** — autos grandes demoram. Eu estava
   com logging DESLIGADO no download_loop → não via os passos → achei travado (erro de diagnóstico meu).
   Fix: `logging.basicConfig(INFO)` no loop.
- ANEXAR (debuggerAddress) TRAVA (domínio pastadigital/ + multi-aba embanana o foco). Melhor: MEU Chrome
  no perfil `~/perito_chrome_debug` (Bruno logou → sessão persiste → "já logado") + pop-up liberado.
- `download_loop.py` (1.277 CNJs) baixa → extrai texto p/ `PROCESSOS/{cnj}/auto_texto.txt` → PODA o PDF.
  Retomável, lento (600s/auto grande), pega lote e retoma.

## ✅✅ RESOLVIDO E FUNCIONANDO (11/07) — download autônomo COMPLETO no Mac
A cagada era o seletor: o link "Visualizar autos" real é `<a id="linkPasta" href="#liberarAutoPorSenha">`
e havia UM aria-hidden=true (leitor de tela, invisível) — eu clicava no invisível. Fix em
`esaj_baixar_autos.py _baixar_pasta_direta`: seletor por TEXTO/href liberarAutoPorSenha + filtra
`aria-hidden!='true' and is_displayed()`. **Testado: baixou o auto completo** (0846180-91.2024.8.12.0001.pdf),
login CPF/senha + **2FA automático do e-mail** (sem Bruno digitar), pasta digital em nova aba, PDF gerado e salvo.
- **LOOP**: `scratchpad/download_loop.py` — 1 login, reusa a sessão, retomável (pula já baixados),
  gentil (3s), resiliente (re-loga se cair), **trava de disco 30GB**. Rodando nos ~1.277 CNJs de 1º grau.
  Funções reusadas: `eb._buscar_cd_processo(driver,cnj)` + `eb._baixar_pasta_direta(driver,cd,cnj)` + limpa abas.
- ⚠️ **DISCO**: autos são GRANDES (centenas de MB a 700MB). 1.277 autos = pode passar de 1TB; Mac tem ~134GB.
  A trava para em 30GB livre → baixa só um LOTE (~200) por vez. Pra baixar TODOS: **analisar (advogado/Karyna/
  ao_final) e PODAR o PDF** (guardar só o texto/extract) — decidir com o Bruno (podar é destrutivo, não fiz sozinho).
- 2º grau (`.0000`) fica de fora (consulta é cposg5, não cpopg5) — tratar depois se precisar.

## Plano do agente Windows (REVISADO — muito mais curto)
Adaptar esses 2 scripts para virarem o agente: em vez de ler pasta local, **puxar jobs do VPS**
(`GET /jobs/proximo` → `protocolo_oficio`/`protocolo_laudo`; e receber intimações), fazer o eSAJ+A3
com o código do Bruno, **reportar** (`PATCH /jobs/{id}/concluir`). Rodar no Windows (A3 lá).
A parte difícil (eSAJ/WebSigner/A3) JÁ está resolvida. Ver [[a3-sessao-8h]].
