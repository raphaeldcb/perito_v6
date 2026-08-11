---
name: sistema-laudos-v6-1
description: Sistema de Laudos Periciais v6.1 — Qwen→Fable→Perito→Emissão (IMPLEMENTAÇÃO COMPLETA)
metadata: 
  node_type: memory
  type: project
  status: em_implementação
  data_inicio: 2026-07-07
  originSessionId: 2c421bcf-d51b-4fac-a34e-76bfabd14055
---

# SISTEMA DE LAUDOS PERICIAIS v6.1+ — IMPLEMENTAÇÃO COMPLETA

## VISÃO GERAL

**O que você quer:** Sistema ponta a ponta que transforma processo judicial → **laudo completo, validado por IA, auditável**. Peritos entram, veem fila de análises, revisam pontos críticos (apontados por Fable 5), assinam e emitem. Gestor vê dashboard de laudos por status.

**Estado:** 
- ❌ v6.0 tem coleta (ESAJ) + análise (Qwen JSON)
- ✅ Agora: sistema de LAUDOS (rascunho estruturado → auditoria → revisão → emissão)

---

## DECISÕES FINAIS (Confirmadas 07/07/2026)

| Aspecto | Decisão | Por quê |
|--------|---------|--------|
| **Qwen** | Ollama local (Mac) | Privado, rápido, sem custo, já instalado |
| **Fable 5** | Anthropic API | Auditoria técnica profunda |
| **Assinatura** | Email (link + clique) | Simples, sem token A3 (problema Mac) |
| **Pipeline** | Manual (perito clica "Auditar") | Mais controle, não automático |
| **Projuris** | Sincronizar dados (não coleta) | Perito analisa, Projuris registra resultado |
| **Tipos laudo** | Todos (Contábil, Engenharia, Outros) | Bruno vai "ensinando" — gera, manda pro RAG |

---

## ARQUITETURA

### Modelos (DB)

**Laudo** (nova tabela)
- `id` INT PK
- `processo_id` INT FK → Processo
- `tipo_laudo` VARCHAR (Enum: Contábil, Engenharia, Outro)
- `status` VARCHAR (Enum: rascunho, auditado, em_revisão, emitido, cancelado)
- `perito_id` INT FK → User
- `revisor_id` INT FK → User (opcional)
- `empresa_id` INT FK → Empresa
- `quesitos` JSON (lista de perguntas)
- `data_criacao`, `data_emissao`, `data_assinatura` TIMESTAMP
- `arquivo_docx_id`, `arquivo_pdf_id` INT FK → Arquivo

**LaudoVersao** (histórico rascunhos)
- `id` INT PK
- `laudo_id` INT FK
- `numero_versao` INT
- `conteudo_markdown` TEXT (rascunho em Markdown)
- `gerado_por` VARCHAR ("qwen" ou "perito")
- `data_criacao` TIMESTAMP

**AuditoriaFable** (validações)
- `id` INT PK
- `laudo_id` INT FK
- `versao_numero` INT
- `relatorio_json` JSONB ({validacoes_ok, avisos, erros_criticos, score})
- `data_criacao` TIMESTAMP

### Fluxo

```
PERITO CLICA "Gerar Rascunho"
     ↓
Job Qwen (Mac Ollama local, ~40s)
     ↓
LaudoVersao v1 (Markdown estruturado)
     ↓
Notifica: "Rascunho pronto"
     ↓
PERITO CLICA "Auditar"
     ↓
Job Fable 5 (Anthropic API, ~10s)
     ↓
AuditoriaFable salva (JSON ✅⚠️❌)
     ↓
LaudoDetail renderiza LADO A LADO
     ↓
PERITO EDITA (opcional) → Salva Versão 2
     ↓
PERITO CLICA "Finalizar"
     ↓
Valida (checklist automático)
     ↓
Exporta Word (template) + PDF + assina email
     ↓
Status = "emitido"
     ↓
FIM
```

### Prompts (Críticos)

**PROMPT QWEN** (gera rascunho)
- Estrutura obrigatória: NBC TP 01 R2 (Contábil) ou NBR 13752 (Engenharia)
- Seções: Identificação → Síntese → Metodologia → Diligências → Análise → Quesitos → Conclusão → Encerramento
- Output: Markdown com títulos ##, tabelas, listas
- Validações: cite fls. XXX, valores consistentes, sem termos subjetivos

**PROMPT FABLE** (audita)
- Valida: citações (existem?), estrutura ABNT, inconsistências de valores, rastreabilidade
- Output: JSON {validacoes_ok, avisos, erros_criticos, score}
- Bloqueadores: artigos inexistentes, valores divergentes, quesitos não respondidos

### Serviços

| Serviço | Função |
|---------|--------|
| `laudo_generator.py` | Qwen: processo → rascunho Markdown |
| `auditor_fable.py` | Fable: rascunho → relatório JSON |
| `laudo_exporter.py` | Exporta Word/PDF com estrutura |
| `laudo_validator.py` | Checklist antes de emitir |

### Rotas API

| Rota | Método | Função |
|------|--------|--------|
| `/laudos/{processo_id}/gerar-rascunho` | POST | Enfileira Qwen |
| `/laudos/{laudo_id}` | GET | Retorna rascunho + auditoria |
| `/laudos/{laudo_id}/auditar` | POST | Dispara Fable |
| `/laudos/{laudo_id}/revisar` | PATCH | Perito corrige |
| `/laudos/{laudo_id}/finalizar` | POST | Valida e emite |
| `/laudos` | GET | Lista com filtros |

### Frontend

| Componente | Função |
|-----------|--------|
| `LaudoDetail.jsx` | Editor rascunho + auditoria lado a lado |
| `LaudosLista.jsx` | Fila com status e filtros |
| `LaudoViewer.jsx` | Renderizador Markdown |
| `AuditoriaPanel.jsx` | Visualizador auditoria (✅⚠️❌) |

---

## INTEGRAÇÃO TÉCNICA

### Ollama (Qwen Local)

```
URL: http://localhost:11434/api/generate
Modelo: batiai/qwen3.6-35b:iq4
Timeout: 300s
Fallback: DashScope API (sk-ce58...)
```

### Fable 5 (Anthropic)

```
SDK: from anthropic import Anthropic
API Key: ANTHROPIC_API_KEY (variável env)
Modelo: claude-fable-5
Timeout: 30s
```

### Word Templates

```
templates/laudo_contabil.docx (NBC TP 01 R2)
templates/laudo_engenharia.docx (NBR 13752)
Placeholders: {{identificacao}}, {{metodologia}}, {{analise}}, {{conclusao}}, ...
```

---

## IMPLEMENTAÇÃO (STATUS)

### Fase 1: Modelos ⏳
- [ ] `models/laudo.py` (Laudo, LaudoVersao, AuditoriaFable)
- [ ] Migration Alembic

### Fase 2: Services ⏳
- [ ] `services/laudo_generator.py` (Qwen)
- [ ] `services/auditor_fable.py` (Fable)
- [ ] `services/laudo_validator.py` (Checklist)
- [ ] `services/laudo_exporter.py` (Word/PDF)

### Fase 3: Rotas ⏳
- [ ] `routes/laudos.py` (6 endpoints)

### Fase 4: Templates ⏳
- [ ] `templates/laudo_contabil.docx`
- [ ] `templates/laudo_engenharia.docx`

### Fase 5: Frontend ⏳
- [ ] `pages/LaudoDetail.jsx`
- [ ] `pages/LaudosLista.jsx`
- [ ] `components/LaudoViewer.jsx`
- [ ] `components/AuditoriaPanel.jsx`

### Fase 6: E2E ⏳
- [ ] Integração + testes
- [ ] Documentação prompts

---

## DEPENDÊNCIAS NOVAS

```
anthropic>=0.7.0       # Fable 5
python-docx>=0.8.11    # Word generation
markdown>=3.4.1        # Markdown parsing
requests>=2.31.0       # Já tem
```

---

## .ENV NECESSÁRIO

```
ANTHROPIC_API_KEY=sk-ant-...      # CRÍTICO
QWEN_URL=http://localhost:11434   # Local Ollama
QWEN_MODEL=batiai/qwen3.6-35b:iq4 # Modelo
QWEN_API_KEY=sk-...                # Fallback DashScope (opcional)
```

---

## PRÓXIMOS PASSOS

1. ✅ Haiku implementando agora (background)
2. Testar E2E: criar processo → gerar rascunho → auditar → revisar → emitir
3. Integrar Projuris (dados, não coleta)
4. RAG dos laudos (base de conhecimento)
5. Dashboard de laudos (analytics)

---

## REFERÊNCIAS

- Design completo: `/tmp/design_laudos_completo.md`
- Plano: `/Users/ipc_server/.claude/plans/spicy-orbiting-pudding.md`
- Manual perícia: `/Users/ipc_server/Downloads/Escritório de Perícias Judiciais.txt`
- Projuris info: `/Users/ipc_server/Downloads/projuris.txt`

---

*Documento criado 07/07/2026 — Haiku em implementação*
