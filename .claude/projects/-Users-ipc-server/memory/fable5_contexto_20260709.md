---
name: fable5_contexto_20260709
description: "Contexto compacto para Fable 5 — estado do sistema, atualizações pendentes, sem BS"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2c421bcf-d51b-4fac-a34e-76bfabd14055
---

# FABLE 5 — CONTEXTO EFICIENTE

## ESTADO ATUAL (07/07/26 11:15 UTC)

**Sistema:** Perito v6.0 LIVE em produção  
**Banco:** perito_v6 no PostgreSQL (34 tabelas, 10 usuários)  
**Acesso:** https://sistema.ipcms.com.br  
**Login:** admin@ipcms.com.br / admin123 ✅ FUNCIONA

---

## O QUE FUNCIONA (80% do sistema)

✅ **Autenticação:** JWT + roles + audit logs  
✅ **Dados:** processo, intimacao, laudo, job (fila)  
✅ **Kanban:** visualização e movimentação de cartões  
✅ **OCR:** pypdf + Tesseract (intimações)  
✅ **Qwen:** análise via DashScope (dados estruturados)  
✅ **A3:** assinatura + protocolo eSAJ (mac agent)  
✅ **Jobs:** queue system com status tracking  

---

## O QUE FOI ADICIONADO (20% novo)

### 1. Modelo Oficio (kanban.py)
```python
class Oficio(Base, TimestampMixin):
    id, intimacao_id, processo_id, tipo, arquivo_docx_path, 
    arquivo_pdf_path, numero_protocolo, status, erros
```
**Status flow:** gerado → protocolo_enfileirado → protocolado

### 2. Frontend (FluxoCompletoModal.jsx)
- Modal interativa: 4 steps (select → loading → success → error)
- Carrega intimações: GET /api/v1/intimacoes
- Dispara: POST /api/v1/fluxo/completo/{id}
- Polling: GET /api/v1/fluxo/status/{id} a cada 2s
- 4 progress bars com cores

### 3. Backend (fluxo_completo.py)
```
POST /api/v1/fluxo/completo/{intimacao_id}
  → gera ofício (DOCX preenchido)
  → Job(tipo="protocolo_oficio")
  → Job(tipo="gerar_laudo")
  → Job(tipo="protocolo_laudo", aguardar_job_id=laudo.id)
  → retorna {status, job_oficio_id, job_laudo_id}

GET /api/v1/fluxo/status/{intimacao_id}
  → retorna {oficio: {status, numero_protocolo}, laudo: {status}}
```

### 4. Services
- **oficio_generator.py:** gera DOCX a partir de template + dados
- **create_oficio_templates.py:** cria 3 templates Word (requerimento, manifestacao, resposta_quesito)

### 5. Templates Word
Salvos em `/app/templates/`:
- oficio_requerimento.docx
- oficio_manifestacao.docx  
- oficio_resposta_quesito.docx

Com placeholders: {{JUIZ}}, {{VARA}}, {{DATA}}, {{NUMERO}}, {{COMARCA}}, {{RESUMO_INTIMACAO}}, {{PRAZO_DIAS}}, {{RESPONSAVEL}}

---

## ✅ TESTADO E2E EM 09/07/26 (commit e6eb6d3, deployado)

1. ✅ Ofício DOCX gerado E PREENCHIDO em `/data/oficios/{cnj}/` (bug: f-strings nos templates)
2. ✅ Laudo gerado pelo **mac_agent + Ollama local** (Qwen 3.6) — chave DashScope está REVOGADA
3. ✅ Laudo DOCX exportado em `/data/laudos/` + LaudoVersao no BD (via _aplicar_resultado em jobs.py)
4. ✅ Fila respeita `aguardar_job_id` (protocolo_laudo só roda após laudo pronto)
5. ✅ Botão 🚀 agora em **ProcessosPage.jsx** (`/processos`) — ProcessosIntimacoes.jsx era página ÓRFÃ fora do router
6. ✅ `/fluxo/status` retorna estado real (laudo vem dos jobs; antes era hardcoded)
7. ⚠️ Protocolo eSAJ real: jobs falham no gate `PROTOCOLO_AUTOMATICO_ATIVO != 1` (por design) — pendente A3/Windows/homologação

### Armadilhas descobertas (não repetir)
- Templates de ofício vivem no layer efêmero do container → main.py cria no startup
- `docker-compose restart` NÃO carrega imagem rebuildada → usar `up -d`
- DEPLOY.sh agora builda frontend também (bundle estava meses defasado)
- Login API usa campo `password` (não `senha`); GET /intimacoes exige barra final (307)
- Duas classes `Processo` (processo.py + kanban.py) — nunca usar relationship("Processo")

---

## INSTRUÇÕES PARA TESTAR

```bash
# 1. Entra em: https://sistema.ipcms.com.br
# 2. Login: admin@ipcms.com.br / admin123
# 3. Gestão de Autos
# 4. Procura botão 🚀 Fluxo Completo (deve estar no header)
# 5. Clica, abre modal
# 6. Seleciona intimação
# 7. Clica Disparar
# 8. Aguarda 5 minutos (worker processa a cada 10min)
# 9. Verifica:
#    - PDF/DOCX em /data/storage/oficios/?
#    - Barra atualiza?
#    - Status no BD muda?
```

---

## CREDENCIAIS E PATHS

**VPS:** root@129.121.34.186:22022  
**Chave SSH:** /Users/ipc_server/.ssh/id_ed25519_perito  
**Docker Compose:** /var/www/perito-v5.2/v6/docker-compose.yml  
**Backend:** http://localhost:8000  
**Database:** postgresql://perito:pwd@db:5432/perito_v6  
**Storage:** /data/storage/ (volumes docker)  

**10 Usuários no BD:** admin, bruno, leticia, allan, ana, melissa, miriam, cezar, joyce, alberto  
(Senhas: desconhecidas, use admin123 como teste)

---

## ESTRUTURA DE CÓDIGO (quick reference)

```
backend/
  app/
    routes/
      fluxo_completo.py       ← NEW (endpoints)
      auth.py                 ← funciona
      kanban.py               ← funciona
      jobs.py                 ← funciona
    models/
      kanban.py               ← NEW Oficio model
      user.py, job.py, etc    ← funciona
    services/
      oficio_generator.py     ← NEW
      oficio.py               ← funciona (preenche dados)
      laudo_generator.py      ← funciona
      ocr_processor.py        ← funciona
    workers/
      main.py                 ← funciona (loop 10min)
      analise_qwen.py         ← funciona
    templates/
      oficio_*.docx           ← NEW (3 arquivos)

frontend/
  src/
    pages/
      ProcessosIntimacoes.jsx ← MODIFIED (adicionado botão 🚀)
    components/
      FluxoCompletoModal.jsx  ← NEW (modal interativa)
```

---

## DEPLOY (SEGURO)

```bash
cd /Users/ipc_server/projects/ipc-pericias-ai/v6
bash DEPLOY.sh
# → Faz backup, atualiza, verifica login, rollback se quebrar
```

---

## O QUE NÃO MEXER

❌ auth.py — funciona, não mexe  
❌ usuario table — dados reais, cuidado  
❌ job types antigos (protocolo, esaj_intimacoes) — em produção  
❌ workers/main.py — loop crítico  

---

## TOKENS EFICIÊNCIA

- NÃO pergunte "como está o sistema?" — leia este documento
- NÃO consulte BD — só faça se teste quebrou
- FOCO: testar novo fluxo (modal → ofício → protocolo)
- SE quebrar: diga exatamente o erro (screenshot ou log)

---

**Última atualização:** 2026-07-09 11:15 UTC
