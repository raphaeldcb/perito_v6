---
name: skill_codemail
description: 25/07/26 — Skill reutilizável para extrair código 2FA de email via Graph API
metadata: 
  node_type: memory
  type: reference
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-25T14:42:40.439Z
---

# Skill: CodeMail (2FA Email Extraction)

**Location:** `~/.claude/skills/codemail.md`

**Purpose:** Reusable skill para extrair código 2FA/OTP do email durante fluxos de login automático.

**Quando usar:**
- ESAJ + TJMS logins com 2FA
- Qualquer sistema que envia código via email
- Fluxos não-interativos que precisam código automático

**Componentes:**
- Graph API client (via Azure credentials)
- Email polling com timeout
- Regex para detectar padrões de código (6 dígitos)
- Logging + auditoria completa

**Invocação via routerclaude:**
```
routerclaude "integrar codemail no [sistema]"
```

**Credenciais necessárias (.env):**
```
GRAPH_TENANT_ID=<azure-tenant>
GRAPH_CLIENT_ID=<app-id>
GRAPH_CLIENT_SECRET=<app-secret>
GRAPH_MAILBOX=adm@ipcms.com.br
```

**Timeouts recomendados:**
- ESAJ: 60s
- TJMS: 45s
- SafeKey: 90s

**Integrada em:**
- (nenhuma ainda — pronta para TJMS/SafeKey/NFS-e)

---

**Próximas integrações:** TJMS, SafeKey, NFS-e
