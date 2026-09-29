---
name: project-ipc-pipeline
description: "Pipeline autônomo IPC — arquitetura completa Ollama-first + Claude Revisor + RAG, status atual e pendências"
metadata:
  type: project
  originSessionId: b0cc2ab7-a18a-4b27-8166-5333724f573e
  modified: 2026-09-29T19:58:38.649Z
---

## Arquitetura atual (Ollama-first + Claude Revisor + RAG)

```
PDF → Analisador (41 campos) → pdfplumber fallback se falhar
           ↓
   RAG: busca 3 casos similares (ChromaDB + nomic-embed-text)
           ↓
  Ollama qwen2.5-coder:32b (análise jurídica completa)
           ↓
  Claude revisa (CLAUDE_REVIEW_ENABLED=false — via sessão interativa)
           ↓
  ChromaDB ← salva análise para autoaprendizado
           ↓
  VPS perito-system + .md em OneDrive + .docx ofício proposta
```

---

## LaunchAgents registrados

| Label | Horário | O que faz |
|---|---|---|
| `com.ipcms.pipeline` | 8:15 seg-sex | Download ESAJ + análise (requer PIN A3) |
| `com.ipcms.analise-noturna` | 21:00 todos os dias | Analisa PDFs pendentes sem ESAJ/PIN |
| `com.ipcms.email-monitor` | 02:00 todos os dias | Lê emails tribunais, baixa autos TJMS via ESAJ, envia relatório |
| `com.ipcms.model_update` | 7:00 diário | Verifica novos modelos Ollama (a cada 10 dias) |
| `com.ipc_server.monitor_pericias` | 21:00 diário | Monitor RSS/web (NÃO é o pipeline) |

**Fluxo noturno:**
- 21:00 → analise-noturna: Ollama analisa PDFs já em DOWNLOADS_DIR (sem Chrome/PIN)
- 02:00 → email-monitor: lê inbox ipcms@ipcms.com.br, extrai processos TJMS novos, baixa autos via ESAJ (sem Ollama — análise fica para o dia seguinte às 21h)

---

## Componentes criados

### pipeline/
- `model_selector.py` — seleciona melhor modelo Ollama por prioridade
- `rag_juridico.py` — ChromaDB + nomic-embed-text embeddings
- `claude_revisor.py` — revisão Claude (pulada se sem API key)
- `ollama_juridico.py` — análise com RAG few-shot + revisão + contexto adaptativo por área
- `oficio_proposta.py` — gera .docx ofício de proposta a partir do template 10-CONT-JUD.docx
- `email_monitor.py` — lê emails de tribunais via Graph API, baixa autos, envia relatório
- `auto_update.py` — atualização automática modelos a cada 10 dias
- `esaj_baixar_autos.py` — download autos por número CNJ
- `esaj_dispatcher.py` — dispatcher (chama baixar_autos ou intimações)
- `config.py` — novas vars: CHROMA_DIR, RAG_N_EXEMPLOS, CLAUDE_REVIEW_MODEL
- `.env` — CLAUDE_REVIEW_ENABLED=false, OLLAMA_TIMEOUT=750, VPS_PASSWORD=Admin@2026
- `run_noturno.sh` — script para análise noturna (usa /usr/bin/python3)
- `run_email_monitor.sh` — script para email monitor noturno
- `nfse_campogrande.py` — emissão NFS-e ABRASF v2.03 SOAP (Campo Grande/MS)
- `nfse_ollama.py` — 3 funções: extrair_tomador_ollama, extrair_dados_pagamento_ollama, gerar_discriminacao_ollama
- `inter_extrato.py` — Banco Inter API (aguardando credenciais mTLS do banco)
- `financeiro_matching.py` — matching pagamento ↔ processo por valor/SELIC
- `financeiro_cli.py` — CLI completo: importar-inter / matching (c/ fallback Ollama) / emitir-nfse / status

---

## ESAJ download — fluxo correto descoberto

Sequência OBRIGATÓRIA (direto para abrirPastaDigital.do não funciona):
1. `garantir_login(driver)` via intimacoes_v7
2. `open.do` → preencher formulário via JS (nnd + foro separados)
   - `#numeroDigitoAnoUnificado` = `NNNNNNN-DD.AAAA` (ex: `0800472-51.2017`)
   - `#foroNumeroUnificado` = `OOOO` (ex: `0037`)
3. Aguardar AJAX resultar
4. `show.do?processo.codigo={cd}&processo.foro={foro}` (estabelece sessão)
5. Clicar "Visualizar autos" → NOVA ABA abre (`pastadigital/`)
6. `switch_to.window(handles[-1])` → aguardar `#selecionarButton`
7. Selecionar todas + salvar + baixar PDF

---

## Ollama — otimizações de prompt (2026-05-27)

- Contexto adaptativo por área: _contexto_ipc(dados) em vez de monolítico (843 chars vs 3329)
- dados_json reduzido a 13 campos essenciais (não todos 41)
- versao_autor incluída nos campos de detecção de área (corrige casos como pavimentação)
- texto[:2000] em vez de [:8000]
- Resultado: prompt ~4800 chars (era 15362), tempo médio ~11 min, timeout 750s
- OLLAMA_TIMEOUT=750s (era 600s)
- keep_alive=0 + num_predict=1024

---

## Modelos

| Função | Modelo | Detalhe |
|---|---|---|
| Geração (novo) | batiai/qwen3.6-35b:iq4 | maior capacidade, para processamento pesado noturno |
| Geração (fallback) | qwen2.5-coder:32b | ~11 min por análise, mantido como fallback |
| Fallback | gemma4:latest | instalado |
| Embeddings | nomic-embed-text | instalado |
| Revisão | claude-sonnet-4-6 | desabilitado (CLAUDE_REVIEW_ENABLED=false) |

**Mudança 2026-06-03:** Upgraded model priority em `model_selector.py` para qwen3.6-35b como primeira opção. Commit: c59fdec

---

## Email Monitor (Graph API)

- Mailbox: ipcms@ipcms.com.br
- Tenant: cb5ff6f4-4845-46fd-9eb6-5ca720f7ae7b
- CLIENT_ID: 56fd2738-851e-4482-959d-c3fcea794d90
- Relatório enviado para: bruno@ipcms.com.br
- Scan desde: 2026-01-01
- 139 emails de tribunais identificados
- 85 processos únicos (62 TJMS)
- 51 sem resposta do IPC
- 10 reiterações/urgentes

---

## Processos com cd_processo conhecido

| Processo | cd_processo | Observação |
|---|---|---|
| 0800472-51.2017.8.12.0037 | 1100010UE0000 | Foro 0037=Itaporã/MS |
| 0800828-04.2026.8.12.0046 | 1A0002TB30000 | Foro 0046=Chapadão do Sul |

---

## Status 2026-06-03

| Componente | Status |
|---|---|
| ESAJ download automático | ✅ FUNCIONANDO |
| Analisador (41 campos) | ✅ FUNCIONANDO |
| Ollama qwen3.6-35b (NOVO) | ✅ Modelo principal (~30-90s por análise) |
| Ollama qwen2.5-coder:32b | ✅ Fallback secundário |
| RAG ChromaDB | ✅ 2 casos salvos |
| oficio_proposta.py (.docx) | ✅ FUNCIONANDO |
| email_monitor.py (Graph API) | ✅ FUNCIONANDO |
| VPS login (Admin@2026) | ✅ FUNCIONANDO |
| LaunchAgent analise-noturna (21h) | ✅ registrado + qwen3.6 |
| LaunchAgent email-monitor (02h) | ✅ registrado |
| LaunchAgent pipeline (8:15 seg-sex) | ✅ registrado + qwen3.6 |
| **Comprovantes vinculados** | **✅ 491/546 (89.9%)** |
| perito-system UI (sidebar) | ✅ FUNCIONANDO |
| Banco dados (2 empresas, 4 usuários) | ✅ ATUALIZADO |
| **Processador Retroativo (NOVO)** | **✅ 100% autônomo, diariamente 18:00** |
| **Email retroativo desde jan/2026** | **✅ 93 processos coletados** |
| **Dashboard visual (NOVO)** | **✅ Métricas em tempo real** |
| **Resposta automática tribunais** | **✅ Templates + Graph API** |

---

## Comprovantes — Vinculação (02/06/2026 — FINALIZADO)

**Status:** 491/546 despesas com comprovante_path (89.9%)

| Empresa | Vinculados | Total | Taxa | Notas |
|---|---|---|---|---|
| **Bruno (301)** | **13** | **13 meses** | **✅ 100%** | Pró-labore consolidado |
| **Pericias (terceiros)** | **104** | **260 arquivos** | **40%** | Hugo, Telefonica, Vincensi, etc |
| **Pesquisa** | **118** | **230 arquivos** | **51%** | Pending investigação |
| **Total** | **491** | **546 despesas** | **89.9%** | R$ 1.707.705,46 |

**Investigação 02/06:**
- Bruno 301: 13/13 ✅ — pró-labore contábil (não coletador), consolidado em CCC.YY.MM.pdf
- Terceiros: vinculados por LIKE nome (ignorando discrepâncias de data)
- Script: `vincular-comprovantes-vps.js` + `vincular-terceiros-pericias.js`

**Arquivos:** 260 pericias + 230 pesquisa em /var/www/perito/data/comprovantes/

**Próximas:**
- Pesquisa: investigar 499 (falta histórico completo)

---

## PENDÊNCIAS URGENTES (reiterações sem resposta)

1. **0809666-50.2022.8.12.0021** — REITERAÇÃO Três Lagoas/MS (23/04)
2. **0809670-87.2022.8.12.0021** — Reiteração complementação laudo Três Lagoas (23/04)
3. **0803197-29.2024.8.12.0017** — URGENTE REITERAÇÃO (10/04)
4. **0801442-04.2023.8.12.0017** — URGENTE REITERAÇÃO (10/04)
5. **0800475-49.2017.8.12.0055** — INTIMAÇÃO VENCIDA DIA 25/03 (31/03)
6. **0836868-77.2013.8.12.0001** — URGENTE PRECATÓRIO-ROPV (10/03)
7. **0001052-21.2011.8.11.0048** — Devolução valores 5 dias (05/05) [TJMT]
8. **0016109-48.2017.8.11.0055** — Reiteração Tangará/MT (12/03) [TJMT]
9. **0000591-19.2014.8.11.0024** — Urgente manifestação (09/03) [TJMT]
10. **0002939-24.2008.8.11.0055** — Impugnação laudo (26/02) [TJMT]

---

## Credenciais

- VPS: `sistema.ipcms.com.br` — credentials in VPS `/var/www/perito-v6/backend/.env`
- JWT_SECRET VPS: see `/var/www/perito-v6/backend/.env`
- ESAJ perfil IPC: `192743` (public)
- ESAJ segredo processo: **NOT IN REPO** (VPS only)
- DataJud API key: **NOT IN REPO** (VPS only)
- Microsoft Graph: **NOT IN REPO** (VPS `.env` only)
- Email/OneDrive password: **NOT IN REPO** (VPS only)
- NFSE cert password: **NOT IN REPO** (VPS only)
