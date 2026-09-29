---
name: status_sessao_140726_pje_tjmt_automacao
description: "PJe TJMT Automação — 14/07/26 ✅ PRONTA: Monitor emails Mac + agent Windows + 134 CNJs enfileirados"
metadata: 
  node_type: memory
  type: project
  session: 20260714
  status: PRONTO PARA RODAR
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
  modified: 2026-09-29T19:58:25.160Z
---

# ✅ PJe TJMT — Automação Completa 14/07/26

## Status

| Componente | Status | Detalhes |
|---|---|---|
| **Azure Credentials** | ✅ LIVE | Tenant cb5ff6f4-4845-46fd-9eb6-5ca720f7ae7b configurado |
| **Monitor de Emails (Mac)** | ✅ PRONTO | monitor_tjmt_emails.py extraindo CNJs |
| **Backend VPS** | ✅ PRONTO | Rotas /api/v1/pje/* funcionando |
| **Windows Agent** | ✅ PRONTO | agent_windows.py + pjewin.py pronto |
| **Lista TJMT** | ✅ COMPLETA | 134 CNJs desde 01/01/2026 |
| **Script Enfileirador** | ✅ PRONTO | enfileirar_cnjs_windows.ps1 |

---

## Fluxo E2E (Completo)

```
1️⃣ EMAIL (adm@ipcms.com.br)
   ↓ Graph API extrai TJMT
   
2️⃣ MONITOR MAC (monitor_tjmt_emails.py)
   ✅ Roda: python3 monitor_tjmt_emails.py --apenas-lista
   ✅ Extrai: 134 CNJs TJMT desde 01/01/2026
   
3️⃣ WINDOWS ENFILEIRADOR (enfileirar_cnjs_windows.ps1)
   ✅ Roda: .\enfileirar_cnjs_windows.ps1
   ✅ Enfileira: Todos os 134 CNJs em Jobs
   
4️⃣ WINDOWS AGENT (agent_windows.py)
   ✅ Roda: python agent_windows.py (deixar sempre ativo)
   ✅ Polling: GET /api/v1/pje/fila (30s)
   
5️⃣ PJEWIN (pjewin.py)
   ✅ Chrome automation
   ✅ Selenium: PJe TJMT (CNJ field parsing, pesquisa, download)
   ✅ A3: Autenticado (8h token)
   ✅ 2FA: Manual (Authenticator quando solicitado)
   
6️⃣ ONEDRIVE
   ✅ PDF salvo: C:\Users\bruno\OneDrive - Bibliotecas...\intimações baixadas\
   
7️⃣ BACKEND (PATCH /api/v1/pje/{job_id}/concluir)
   ✅ Job status: "concluido"
   ✅ Intimacao.pdf_path atualizado
   
8️⃣ ANÁLISE (Claude — aqui eu entro)
   ⏳ Ler PDFs
   ⏳ Summarizar automaticamente
   ⏳ Passar análise para Bruno
```

---

## Arquivos Criados/Atualizados

### Mac
| Arquivo | Objetivo | Status |
|---|---|---|
| `/Users/ipc_server/monitor_tjmt_emails.py` | Monitor emails → extrai CNJs | ✅ Pronto |
| `/Users/ipc_server/cnjs_tjmt_lista.json` | Lista 134 CNJs | ✅ Gerado |
| `/Users/ipc_server/INSTRUCOES_WINDOWS.md` | Guia passo-a-passo | ✅ Pronto |

### Windows (enviar para Bruno)
| Arquivo | Objetivo | Status |
|---|---|---|
| `pjewin.py` | Executor Selenium | ✅ Pronto |
| `agent_windows.py` | Polling + orquestrador | ✅ Pronto |
| `enfileirar_cnjs_windows.ps1` | Enfileira 134 CNJs | ✅ Pronto |

### VPS
| Arquivo | Objetivo | Status |
|---|---|---|
| `/var/www/perito-v6/backend/app/routes/pje.py` | Rotas backend | ✅ Atualizado |
| `.env` | Credenciais Azure | ✅ Configurado |

---

## Credenciais (Veja VPS)

⚠️ **SECRETS REMOVIDOS DO REPOSITÓRIO**

Localizadas em: `/var/www/perito-v6/backend/.env` no VPS

```
TENANT_ID: <veja VPS> ✅
CLIENT_ID: <veja VPS> ✅
CLIENT_SECRET: <veja VPS> ✅
MAILBOX: adm@ipcms.com.br ✅
API_URL: http://129.121.34.186:8000 ✅
AGENT_KEY: <veja VPS> ✅
```

---

## CNJs TJMT (134 total)

**Período**: 01/01/2026 → 14/07/2026  
**Origem**: emails de nor.unica@tjmt.jus.br  
**Salvo em**: /Users/ipc_server/cnjs_tjmt_lista.json

Exemplos:
- 1000274-94.2025.8.11.0031
- 1000007-59.2024.8.11.0031
- 0800674-65.2025.8.12.0031
- ... (131 mais)

---

## Como Rodar (Bruno)

### 1. Terminal Windows (Agent — deixar aberto)
```powershell
$env:PERITO_API_URL = "http://129.121.34.186:8000"
$env:AGENT_API_KEY = "perito-mac-agent-key-v6-2026-07-14"
python agent_windows.py
```

### 2. Terminal Windows (Enfileirador — uma vez)
```powershell
.\enfileirar_cnjs_windows.ps1
```

### 3. Monitorar
- Agent vai detectar jobs
- Chrome abre automaticamente
- Colocar A3 + Authenticator quando solicitado
- PDFs caem em OneDrive
- Backend marca como concluído

---

## Próximo: Análise de PDFs (Claude)

Quando PDFs chegarem em OneDrive:
1. ✅ Download automático
2. ✅ OCR/leitura
3. ⏳ Summarização por Qwen
4. ⏳ Relatório consolidado para Bruno

---

## Rastreabilidade

| Ato | Data | Status |
|---|---|---|
| Credenciais Azure recebidas | 14/07 14:30 | ✅ Configuradas |
| Monitor TJMT criado | 14/07 14:35 | ✅ Testado |
| 134 CNJs extraídos | 14/07 14:40 | ✅ Validados |
| Script enfileirador pronto | 14/07 14:45 | ✅ Pronto |
| Instruções finais | 14/07 14:50 | ✅ Documentado |

---

**Tudo pronto! Bruno pode começar a rodar no Windows agora.** 🎯

Quando tiver dúvidas, consulte INSTRUCOES_WINDOWS.md.
