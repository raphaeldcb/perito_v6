---
name: tipos_pericia
description: "Tipos de perícia — modalidade de contratação (Judicial, Extrajudicial, AT)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-23T11:51:57.196Z
---

# Tipos de Perícia

**Versão:** 2026-07-23  
**Status:** Autoritativo

---

## Mapeamento Tipos de Perícia

| Código | Nome | Descrição |
|--------|------|-----------|
| **Judicial** | Judicial | Perícia requerida em processo judicial |
| **Extrajudicial** | Extrajudicial | Perícia extrajudicial (consultoria, arbitragem) |
| **AT** | Assistência Técnica | Assistência técnica (suporte, assessoria) |

---

## Referência Código

```python
TIPOS_PERICIA = [
    {"id": "Judicial", "label": "Judicial"},
    {"id": "Extrajudicial", "label": "Extrajudicial"},
    {"id": "AT", "label": "Assistência Técnica"},
]
```

---

## ⚠️ Distinção Crítica

**TIPO** = Modalidade de contratação (3 valores)
- Judicial
- Extrajudicial
- Assistência Técnica

**SETOR** = Especialidade técnica (6 valores) — [[setores_empresa]]
- Contábil
- DNA
- Engenharia
- Grafotécnica
- Multidisciplinar
- Declina

**ENQUADRAMENTO** = DNA-específico (ex: PD0101 "Mãe, criança e suposto pai")
- Apenas para perícias DNA
- Vinculado ao processo via tabela `enquadramento_dna`

---

## Arquivo de Referência

- `/Users/ipc_server/projects/ipc-pericias-ai/v6/TIPOS_PERICIA.md`
