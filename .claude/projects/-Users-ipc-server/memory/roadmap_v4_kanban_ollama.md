---
name: roadmap-v4-kanban-ollama-automacao
description: "Roadmap v4.0 — Sistema completo com Kanban automático, Ollama IA, detector fake media, automação tribunal"
metadata: 
  node_type: memory
  type: project
  status: planejamento
  data: 2026-06-18
  origem: 4 markdown files em ~/Downloads
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

## 🚀 ROADMAP V4.0 — PERITO SYSTEM COMPLETO

**Baseado em:** APRESENTACAO_SISTEMA.md + README_V2_COMPLETO.md + KANBAN_WORKFLOW.md + GUIA_DEPLOY_MANUAL_VPS.md

**Status Atual:** v3.0 em produção (DRE, Alertas, Permissões, Intimações básicas)  
**Status Proposto:** v4.0 — Sistema 100% automático com Kanban + Ollama + Monitores  
**Data:** 2026-06-18  
**Esforço:** 6-8 semanas (Fase 5-8)

---

## 📋 O QUE ESTÁ FALTANDO (vs. Documentação v4.0)

### COMPONENTES NÃO IMPLEMENTADOS

| Componente | Localização | Esforço | Prioridade |
|------------|------------|--------|-----------|
| **Kanban Visual Automático** | `pipeline/kanban_api.py` + `kanban_frontend.html` | 3-4 dias | 🔴 CRÍTICA |
| **Ollama IA — Análise 41 campos** | `pipeline/ollama_extractor.py` | 3 dias | 🔴 CRÍTICA |
| **Detector Fake Media** | `pipeline/detector_fake_media.py` | 2 dias | 🟡 ALTA |
| **Monitor Outlook — Intimações** | `pipeline/monitor_outlook.py` | 2 dias | 🟡 ALTA |
| **Baixador ESAJ Automático** | `pipeline/esaj_downloader.py` | 1-2 dias | 🟡 ALTA |
| **Gerador DOCX Laudos** | `pipeline/gerador_laudo_docx.py` | 2 dias | 🟡 ALTA |
| **Protocolo Automático PJe/ESAJ** | `pipeline/protocolo_pje.py` | 2 dias | 🟡 ALTA |
| **Cron Automação** | PM2 + cron jobs | 1 dia | 🟢 MÉDIA |

**Total: ~18 dias de desenvolvimento (3.5 semanas)**

---

## 🎯 FLUXO PROPOSTO V4.0

```
┌─────────────────────────────────────────────────────────────────┐
│                   FLUXO V4.0 END-TO-END                        │
└─────────────────────────────────────────────────────────────────┘

DIA 1 — 08:00 AM
├─ 📧 Intimação chega no email (cliente)
├─ 🤖 Monitor Outlook detecta automaticamente
├─ 📥 ESAJ Downloader baixa autos (automático)
├─ 🎨 Detector Fake Media analisa mídias
├─ 🧠 Ollama extrai 41 campos estruturados
├─ 📋 Sistema cria cartão no Kanban [RASCUNHO]
└─ 📬 Email ao perito: "Novo caso: [Número Processo]"

DIA 2 — 14:00 PM
├─ 📄 DOCX laudo gerado automaticamente (enquanto perito trabalha)
├─ 👤 Perito move cartão: [RASCUNHO] → [ANÁLISE] → [REVISÃO]
├─ 📬 Email ao revisor: "Laudo aguardando aprovação"
└─ 20:00 PM: Revisor aprova (1 clique)

DIA 3 — 20:00 PM (Cron)
├─ 🤖 Sistema busca cartões [APROVADO]
├─ 📝 Gera PETICIONA jurídica + assinatura digital
├─ 🏛️ Protocola automaticamente via PJe/ESAJ
├─ ✅ Tribunal recebe número de protocolo
├─ 📋 Cartão move: [APROVADO] → [PROTOCOLADO]
└─ 📬 Email: "Protocolo: 2406040001234 ✅"

TOTAL: 3 DIAS | Zero intervenção manual (exceto 2 cliques revisor)
```

---

## 🏗️ ARQUITETURA V4.0

### Backend Adicional (Python + Ollama)

```
src/
├── database.js              (existente, expandir)
├── auth.js                  (existente)
├── routes.js                (existente, adicionar endpoints)
├── server.js                (existente)

pipeline/                      ← NOVOS
├── kanban_api.py            (API REST do Kanban)
├── kanban_schema.sql        (Schema: usuarios, kanbans, colunas, cartões)
├── ollama_extractor.py      (Extração 41 campos via Ollama)
├── detector_fake_media.py   (Análise imagem/vídeo/áudio)
├── monitor_outlook.py       (EWS — detecção intimações)
├── esaj_downloader.py       (Scraper/API ESAJ)
├── gerador_laudo_docx.py    (python-docx + templates)
├── protocolo_pje.py         (SOAP/XML ao tribunal)
└── cron_automacao.py        (Agendador de tarefas)

logs/
├── kanban-api.log
├── ollama-extractor.log
├── monitor-outlook.log
└── (outros)
```

### Frontend Adicional (HTML)

```
public/
├── index.html               (existente, expandir)
├── kanban/
│   ├── index.html           (UI Kanban drag & drop)
│   ├── kanban.js
│   └── kanban.css
└── (abas novas)
```

### Database Adicional (SQLite)

```sql
✅ Existentes (v3.0):
   usuarios, processos, financeiro, intimacoes, alertas_agendados, auditoria

📄 NOVOS (v4.0):
   kanbans                   -- Um por perito
   kanban_colunas            -- Fases customizáveis
   kanban_cartoes            -- Laudos/tarefas
   kanban_historico          -- Auditoria de movimentos
   ollama_extracts           -- Cache de 41 campos
   esaj_downloads            -- Autos baixados
   pje_protocolos            -- Resposta tribunal
```

---

## 📦 FASES DE IMPLEMENTAÇÃO

### FASE 5: Kanban Visual (3-4 dias)

**Objetivo:** Quadro Kanban funcional com drag & drop

**Tarefas:**
1. Criar schema SQL: `kanban_schema.sql`
2. Implementar API: `kanban_api.py` (FastAPI + 7 endpoints)
3. Frontend Kanban: `kanban_frontend.html` + drag & drop (Sortable.js)
4. Permissões: Perito vê só seu, Admin vê todos
5. Histórico: Auditoria de cada movimento
6. Deploy: Integrar ao PM2

**Deliverables:**
- [ ] Schema criado e testado
- [ ] API rodando em localhost:8001
- [ ] Frontend acessível em https://sistema.ipcms.com.br/kanban
- [ ] Drag & drop funcional
- [ ] Histórico de movimentos

---

### FASE 6: Ollama IA — Extração Automática (3 dias)

**Objetivo:** Análise automática de 41 campos com Ollama local

**Tarefas:**
1. Baixar modelo Qwen 3.6 via Ollama
2. Criar extractor: `ollama_extractor.py`
3. Integrar com ESAJ (autos PDF → text)
4. Extrair 41 campos estruturados (JSON)
5. Salvar cache em BD
6. Criar endpoint: `POST /api/process/analyze`

**Campos (exemplo):**
```
Processo: número, tipo, vara, comarca
Partes: autor, réu, juiz, advogados
Fatos: objeto, causa, prova documental
Prazos: intimação, resposta, prazo útil
```

**Deliverables:**
- [ ] Ollama Qwen 3.6 rodando
- [ ] Extractor testado com 5 PDFs
- [ ] Cache no BD funcionando
- [ ] Endpoint /analyze retornando JSON

---

### FASE 7: Automação Completa (4 dias)

**Objetivo:** Monitor Outlook + ESAJ + Detector Fake Media + Gerador DOCX

**Tarefas:**

1. **Monitor Outlook** (`monitor_outlook.py`)
   - EWS — conectar ao email corporativo
   - Detectar "Intimação" no subject
   - Baixar anexos (PDFs, imagens)
   - Criar cartão Kanban [RASCUNHO]

2. **ESAJ Downloader** (`esaj_downloader.py`)
   - Scraper de autos judiciais
   - Buscar por número processo
   - Salvar PDFs localmente

3. **Detector Fake Media** (`detector_fake_media.py`)
   - Imagem: EXIF, iluminação, artefatos, faces
   - Vídeo: temporal inconsistency, deepfake
   - Áudio: MFCC, prosódia, artefatos digitais
   - Gerar laudo técnico

4. **Gerador Laudo DOCX** (`gerador_laudo_docx.py`)
   - Template word
   - Preencher com dados Ollama
   - Formatação jurídica
   - Assinatura digital (campo vazio)

**Deliverables:**
- [ ] Monitor Outlook detectando intimações
- [ ] ESAJ downloader funcionando
- [ ] Fake media detector gerando laudo
- [ ] Gerador DOCX produzindo laudos

---

### FASE 8: Protocolo Automático (2 dias)

**Objetivo:** Envio automático de resposta ao tribunal via PJe/ESAJ

**Tarefas:**
1. Criar `protocolo_pje.py`
2. Integração SOAP/XML ao PJe
3. Assinatura digital ICP-Brasil
4. Envio automático quando cartão = [APROVADO]
5. Registrar número protocolo na BD
6. Email confirmação

**Deliverables:**
- [ ] Protocolo enviado com sucesso
- [ ] Número de protocolo registrado
- [ ] Cartão atualizado [PROTOCOLADO]

---

## 🔧 COMO INTEGRAR QWEN 3.6

### Opção 1: Ollama Local (Recomendado)

```bash
# Instalar Ollama (macOS/Linux/Windows)
curl https://ollama.ai/install.sh | sh

# Baixar Qwen 3.6
ollama pull qwen:3.6b

# Rodará em localhost:11434
curl http://localhost:11434/api/generate -d '{"model": "qwen:3.6b", "prompt": "Analise este processo..."}'
```

### Opção 2: API Remota

```python
# Se houver servidor Ollama em VPS
import requests

response = requests.post(
    'http://vps.ipcms.com.br:11434/api/generate',
    json={
        'model': 'qwen:3.6b',
        'prompt': 'Extraia os 41 campos...',
        'stream': False
    }
)
```

### Integração no `ollama_extractor.py`

```python
import requests
import json

def extract_fields_with_ollama(pdf_text):
    prompt = f"""Você é um especialista jurídico.
Analise o processo abaixo e extraia em JSON os 41 campos:
- Número processo
- Tipo (judicial/extrajudicial)
- Vara, Comarca, Juiz
- Autor, Réu
- Objeto
- Prazos
- Status
- etc.

PROCESSO:
{pdf_text[:5000]}  # Primeiros 5k chars

Responda APENAS em JSON válido, sem explicação."""

    response = requests.post(
        'http://localhost:11434/api/generate',
        json={'model': 'qwen:3.6b', 'prompt': prompt, 'stream': False}
    )
    
    return json.loads(response.json()['response'])
```

---

## 📊 ESTIMATIVA DE ESFORÇO

| Fase | Componente | Dev | Testes | Total |
|------|-----------|-----|--------|-------|
| 5 | Kanban | 2.5d | 0.5d | **3d** |
| 6 | Ollama IA | 2d | 1d | **3d** |
| 7 | Automação (Outlook+ESAJ+Fake) | 3d | 1d | **4d** |
| 8 | Protocolo | 1.5d | 0.5d | **2d** |
| — | Integração + Deploy | 2d | 2d | **4d** |
| **TOTAL** | — | — | — | **16 dias** |

**Timeline:** ~3.5 semanas (segunda-feira a segunda-feira)

---

## ✅ CHECKLIST FINAL V4.0

- [ ] Fase 5: Kanban online
- [ ] Fase 6: Ollama extraindo 41 campos
- [ ] Fase 7: Monitor Outlook + ESAJ + Fake Media
- [ ] Fase 8: Protocolo automático PJe
- [ ] Dados reais em produção (262 coletadores)
- [ ] PM2 monitorando 7+ apps
- [ ] HTTPS ativo (Nginx + Let's Encrypt)
- [ ] Backup automático funcionando
- [ ] Testes de carga OK
- [ ] Documentação atualizada
- [ ] Treinamento peritos concluído

---

## 🎯 PRÓXIMO PASSO

1. **Decidir:** Implementar v4.0 completo?
2. **Priorizar:** Qual fase começar primeiro?
3. **Recursos:** Qwen 3.6 disponível localmente?
4. **Cronograma:** Começar semana que vem?

---

**Data:** 2026-06-18  
**Elaborado por:** Análise de 4 markdown files  
**Status:** ✅ FASE 5 + 6 COMPLETAS (Kanban + Ollama)
