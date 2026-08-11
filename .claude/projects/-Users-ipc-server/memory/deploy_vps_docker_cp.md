---
name: deploy_vps_docker_cp
description: "⚠️ CRÍTICO deploy VPS: contexto de build está QUEBRADO — deploy via docker cp no container rodando, NUNCA rebuild"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-27T21:27:30.385Z
---

# ⚠️ Deploy VPS — NÃO rebuildar, usar docker cp (26/07/26)

## ✅ 27/07/26 — FRAGILIDADE RESOLVIDA (deploy recreate agora é SEGURO, PROVADO)
Stack de produção viva = **`/var/www/perito-v5.2/v6`** (docker-compose ps mostra os containers aí).
O que causava "sumiu de novo" a cada deploy: `up -d` recriava da imagem stale SEM os routers docker-cp'd (ex: gerencia).
**Conserto (3 camadas):**
1. **`docker commit` da imagem boa** → `v6-backend:consolidado-27jul` (com gerencia + init resiliente).
2. **compose backend+worker: `build:` → `image: v6-backend:consolidado-27jul`** (recreate usa o estado bom, não rebuilda). Backup `docker-compose.yml.bak-27jul`.
3. **`app/routes/__init__.py` RESILIENTE**: import de router em try/except — dep faltando (ex tjms/playwright) PULA, não derruba o app (antes: 1 import quebrado = 502 geral).
**Provado:** recreate controlado → gerencia sobreviveu, saude 14/15. ⚠️ recreate relê `v6/.env`: conferir `POSTGRES_PASSWORD=perito_pass` + `OLLAMA_URL=http://172.18.0.1:11434`.
Ainda assim: para novo CÓDIGO, sincronizar Mac→VPS (rsync backend/app) + docker cp + `docker commit` + repontar compose. Nunca `--build`.

## O perigo (histórico — antes do conserto)

## O perigo
O container `perito-v6-backend` rodando tem o **backend completo (44 routers: auth, esaj,
financeiro, processos...)**, código **baked na imagem** (só `/data` é volume, sem mount de código).

MAS o **contexto de build** `/var/www/perito-v6/backend_broken/v6/backend/app/routes/__init__.py`
está **STRIPADO** (só habilita processos+ferramentas, resto comentado "modelos não existem ainda").
👉 **Rebuildar de lá = DESTRÓI o backend de produção** (perde auth/financeiro/esaj/etc).

O nome `backend_broken` não é à toa. A imagem rodando é de um estado bom antigo; o contexto foi quebrado depois.

## Onde as coisas estão
- Compose: `/var/www/perito-v6/backend_broken/v6/docker-compose.yml` (o `db` daqui É o de produção).
- Código NO container: `/app/app/` (ex: `/app/app/routes/__init__.py`, `/app/app/models/`).
- Frontend: container `perito-v6-frontend`, nginx servindo `/usr/share/nginx/html/`.
- psql user = `perito` (não perito_user).

## Deploy SEGURO de backend (zero downtime, reversível)
1. Extrair o arquivo-alvo DO CONTAINER (`docker exec perito-v6-backend cat /app/app/<f>`) — é a verdade.
2. Aplicar SÓ minhas mudanças em cima da versão do container (não copiar meu repo local direto —
   meu local tem drift, ex: `tjms_router` que o container não tem → quebraria import).
3. Backup do banco: `docker-compose exec -T db pg_dump -U perito perito_v6 | gzip > backup.sql.gz`.
4. `scp` os arquivos pro VPS `/tmp/deploy/` → `docker cp /tmp/deploy/<f> perito-v6-backend:/app/app/...`.
5. `docker-compose restart backend` — **restart preserva os arquivos copiados** (não recria da imagem).
6. Verificar: auth + /processos ainda 200 (não quebrei nada) + endpoint novo 200.
⚠️ `docker cp` é EFÊMERO por si só. **RESOLVIDO 26/07 via docker commit:**
   - `docker commit perito-v6-backend v6-backend:gerencia-live` + `docker commit perito-v6-frontend v6-frontend:gerencia-live`.
   - `docker-compose.yml` editado: backend/worker/frontend agora usam `image: v6-{backend,frontend}:gerencia-live`
     (removido o `build:` do contexto quebrado). Backup: `docker-compose.yml.bak_20260726`.
   - Recriado (`up -d`) e VERIFICADO: auth/processos/gerencia sobreviveram → **agora persiste em qualquer recreate/reboot**.
   - Para novo deploy: docker cp no container → testar → `docker commit` de novo pra mesma tag → pronto (compose já aponta).
   - ⚠️ NÃO rodar `docker-compose build` (rebuildaria do contexto quebrado). Só `up -d` (usa a imagem commitada).

## Deploy de frontend
- `npm run build` local → tar do `dist` → scp → backup `docker exec tar czf /tmp/html_bak.tgz -C /usr/share/nginx/html .`
  → `docker cp` tar pro container → `docker exec sh -c 'cd /usr/share/nginx/html && tar xzf ...'`.
- nginx serve live, sem restart. Backup do html em `/tmp/html_bak_*.tgz` (reversível).

## Backups feitos 26/07
- Banco: `/tmp/backup_pre_gerencia_20260726.sql.gz` (VPS).
- Html: `/tmp/html_bak_20260726.tgz` (VPS).

Relacionado: [[import_projuris_projetocp_feito]], [[credenciais_audit]].
