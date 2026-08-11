---
name: setores_empresa
description: Mapeamento autoritativo dos setores da empresa IPC MS PERÍCIAS
metadata: 
  node_type: memory
  type: reference
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-23T11:46:10.409Z
---

# Setores IPC MS PERÍCIAS

Mapeamento **CORRETO E DEFINITIVO** (atualizado 23/07/2026):

| Código | Setor | ID DB | Descrição |
|--------|-------|-------|-----------|
| **10** | Contábil | 1 | Auditorias e análises contábeis |
| **20** | DNA | 2 | Análise de DNA e perícias genéticas |
| **30** | Engenharia | 3 | Engenharia civil, estrutural e criminal |
| **40** | Grafotécnica | 4 | Análise de documentos e assinaturas |
| **50** | Multidisciplinar | 5 | Múltiplas especialidades |
| **60** | Declina | 6 | Recusa e declínio de perícias |

**⚠️ NÃO INVENTAR NOVOS SETORES** — usar sempre este mapeamento.

## Referência no código

```python
SETORES = {
    10: "Contábil",
    20: "DNA",
    30: "Engenharia",
    40: "Grafotécnica",
    50: "Multidisciplinar",
    60: "Declina"
}
```

Arquivo de referência: `/Users/ipc_server/projects/ipc-pericias-ai/v6/SETORES.md`
