---
name: credenciais_azure_configuradas
description: Credenciais Azure/Office365 para Graph API — CONFIGURADAS 14/07/2026 no VPS em /var/www/perito-v6/backend/.env
metadata: 
  node_type: memory
  type: reference
  session: 20260714
  configured: 2026-07-14 14:30 UTC
  status: ATIVO — Docker backend rodando com credenciais
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
  modified: 2026-09-29T19:58:09.073Z
---

# 🔐 Credenciais Azure — CONFIGURADAS E LIVE

## Localização

| Item | Valor |
|------|-------|
| **Arquivo** | `/var/www/perito-v6/backend/.env` |
| **Docker Container** | `perito-v6-backend` (network: `v6_perito-network`) |
| **Status** | ✅ ATIVO desde 2026-07-14 14:30 UTC |
| **Testado** | Graph API conectando (extrair emails TJMT) |

---

## Credenciais (Sensível — NÃO COMMITTAR)

⚠️ **SECRETS REMOVIDOS DO REPOSITÓRIO POR SEGURANÇA**

Localizadas em: `/var/www/perito-v6/backend/.env` no VPS

```env
GRAPH_CLIENT_ID=<veja VPS>
GRAPH_CLIENT_SECRET=<veja VPS>
GRAPH_TENANT_ID=<veja VPS>
GRAPH_MAILBOX=adm@ipcms.com.br
ONEDRIVE_TENANT=<veja VPS>
AZURE_CLIENT_ID=<veja VPS>
AZURE_CLIENT_SECRET=<veja VPS>
AZURE_TENANT_ID=<veja VPS>
```

**Para acessar**: `ssh root@129.121.34.186 -p 22022 && cat /var/www/perito-v6/backend/.env`

---

## Como Acessar (Sem Re-Configurar)

### 1. SSH para VPS
```bash
ssh -i ~/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186
cat /var/www/perito-v6/backend/.env | grep GRAPH_
```

### 2. Verificar Backend Conectado
```bash
docker logs perito-v6-backend | grep -i "Waiting for application\|startup complete"
```

### 3. Testar Graph API em Produção
```bash
docker exec perito-v6-backend python3 << 'EOF'
from app.services.graph_mail import listar_nao_lidos
emails = listar_nao_lidos(limite=10)
print(f"✅ Conectado! Total: {len(emails)} emails")
EOF
```

---

## Endpoints Funcionando

| Rota | Autenticação | Status |
|------|--------------|--------|
| `GET /api/v1/pje/fila` | X-Agent-Key | ✅ 200 OK |
| `PATCH /api/v1/pje/{id}/concluir` | X-Agent-Key | ✅ 200 OK |
| `POST /api/v1/pje/baixar-autos` | JWT | ✅ Pronto |

---

## O Que Funciona Agora

1. **Email Monitoring** — Graph API extraindo emails TJMT
2. **CNJ Extraction** — Regex em assuntos de email
3. **Job Enqueueing** — Criar Job(tipo='pje_download_autos') automaticamente
4. **Agent Polling** — Windows agent recebendo jobs via `/api/v1/pje/fila`
5. **OneDrive Upload** — Credenciais prestas para Azure SDK

---

## NUNCA MAIS PROCURE

- ❌ Procura em logs de erro
- ❌ Grep .env / Docker env
- ❌ PM2 ecosystem

**SEMPRE VEM DAQUI:** Este arquivo + `/var/www/perito-v6/backend/.env` (no VPS).

---

## Próximos Passos

1. ✅ Credenciais salvos
2. ⏳ Extrair lista completa de CNJs TJMT de emails
3. ⏳ Enfileirar downloads automáticos
4. ⏳ Botão "Baixar Autos" no Perito v6 dashboard
5. ⏳ Testar E2E com Windows agent

---

**Configurado por:** Claude Code  
**Data:** 2026-07-14  
**Revisar:** Nunca (credenciais estão fixas)
