---
name: esaj_acesso_fora_horario
description: eSAJ TJMS era acessado 1x/hora (fora do horário) + 2FA quebrado — AMBOS CORRIGIDOS 28/07 (acesso só 6h/20h + endpoint do código 2FA religado)
metadata: 
  node_type: memory
  type: project
  originSessionId: e7c45933-ce0e-4235-b3f8-5d8d1369984c
  modified: 2026-07-28T14:34:29.831Z
---

28/07/26 — Bruno: acessos eSAJ TJMS fora do horário + captação do 2FA quebrada. Investigado e **RESOLVIDO**.

**CAUSA RAIZ (corrigida) do acesso horário:** `backend/app/workers/main.py` → `enfileirar_busca_esaj()` criava job `esaj_intimacoes` "no máximo 1 por hora" = **24 acessos/dia**. O mac-agent (launchd `com.ipc.perito-mac-agent`, roda `v6/scripts/mac_agent.py` → `pipeline/esaj_dispatcher.py` → `intimacoes_v5.py`) executa o login. Roda no container **perito-v6-worker**.
⚠️ CORREÇÃO de diagnóstico: o cron `sync_tjms.sh` (0 * * * *) NÃO acessa o eSAJ — é POST interno em localhost:3001/processos. O "✅ TJMS SYNC" engana. O acesso real ao eSAJ é o `esaj_intimacoes` (workers/main.py), que tinha a MESMA cadência horária.

**FIX 1 aplicado (deployed+verificado):** guarda em enfileirar_busca_esaj — `if (utcnow()-4h).hour not in (6,20): return 0`. Só 6h e 20h horário de MS (UTC-4). docker cp → perito-v6-worker + restart. TZ confirmada pelo Bruno: UTC-4 (uso interno) — fix está correto.

**CAUSA do 2FA quebrado (corrigida):** endpoint `GET /api/v1/esaj/codigo-2fa` (routes/esaj.py) foi COMENTADO em 22/07 ("tentando à toa"). Mas o `intimacoes_v5.py` (linha 256) continua chamando `https://sistema.ipcms.com.br/api/v1/esaj/codigo-2fa` → 404 → "codigo nao veio" → cai no manual → login falha (ok:false). O email do 2FA chega CERTO em **ipcms@** (remetente `saj-envio@tjms.jus.br`, assunto "Validação de identificação"); `buscar_codigo_2fa` extrai OK (testei = 516084).

**FIX 2 aplicado (deployed+verificado E2E):** reativei o endpoint (routes/esaj.py). docker cp → perito-v6-backend + restart. Teste na URL real c/ X-Agent-Key = `{"codigo":"516084","caixa":"ipcms@ipcms.com.br"}` HTTP 200.

**Commit:** branch `fix/ui-ajustes-perito`. Backups no VPS /root/.

**MIGRADO (permanente, 28/07):** compose em `/var/www/perito-v5.2/v6/docker-compose.yml` — **backend E worker usam a MESMA imagem `v6-backend:consolidado-27jul`** (worker: linha 37; imagem tem 64 routers). `docker commit perito-v6-backend v6-backend:consolidado-27jul` com os DOIS fixes dentro (cp do main.py com guard + esaj.py) → recreate preserva. Verificado via `docker run` (endpoint 2FA=1, guard=1). `saude` = **15/15 VERDE**. (Técnica: docker commit no lugar de rebuild pq o contexto de build é stripado — [[deploy_vps_docker_cp]].)

**Pendências menores:** (1) 403 em `/parametros/agente` (agente usa defaults, não bloqueia); (2) Excel `~/Downloads/acessos_esaj_tjms_fora_horario_20260728.xlsx` foi feito do log do sync_tjms.sh (interno), não do eSAJ real — mas a cadência horária era idêntica, então o padrão/15-fora vale; regenerar do log do worker se quiser timestamps exatos do eSAJ.

Relacionado: [[esaj_automacao_existente]] · [[sequencia_login_codigo_2fa]] · [[deploy_vps_docker_cp]] · [[skill_codemail]]
