---
name: toolchains_periciais
description: "27/07/26 — 4 ferramentas periciais livres+locais instaladas (assinatura, OCR, transcrição, forense) em venv tools-pericia; falta integrar no Perito."
metadata: 
  node_type: memory
  type: project
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-27T17:40:18.411Z
---

# Toolchains periciais — instalados, falta integrar (27/07/26)

Curadoria proativa (MODO CTO) p/ complementar o Perito — **tudo livre, oficial, local, zero custo**.
Venv dedicado: `v6/tools-pericia/` (~380MB). Regra do Bruno: **grátis+local; nada pago sem necessidade real**
(por isso OCRmyPDF/docTR em vez de marker/Surya; ExifTool em vez de sherloq-GUI).

Módulos CLI testados E2E em `v6/backend/scripts/` (commit 62a57b8). Feitos em modo `free` (Qwen draft + Opus arremate):
| # | Ferramenta | Módulo | Status |
|---|---|---|---|
| 1 | **pyHanko** 0.36 (MIT) | `assinar_laudo.py` | ✅ testado (assina PAdES + verifica íntegro) |
| 2 | **OCRmyPDF** 17.8 (MPL) | `ocr_documento.py` | ✅ testado (scan→texto; chama `python -m ocrmypdf`, não bare) |
| 3 | **faster-whisper** 1.2 (MIT) | `transcrever.py` | ✅ testado (áudio→texto, CPU int8, modelo baixa 1º uso) |
| 4 | **ExifTool** 13.55 + ELA | `forense_imagem.py` | ✅ testado (metadados+ELA) |

## Falta: fase 3 — wire no fluxo do Perito (endpoint + UI + job)
- **#1**: endpoint `assinar laudo` + botão; **A3 (PKCS#11) roda no agente Windows** (lá está o token); soft-cert só dev.
- **#2**: chamar `ocr_documento.py` no mac_agent ANTES do parse/RAG dos escaneados.
- **#3**: serviço mídia→transcrição no mac_agent, texto entra no laudo/RAG.
- **#4**: análise de autenticidade no fluxo de imagem/grafotécnica (setor 40).
Os módulos já rodam standalone; falta só o encanamento com o backend/UI.

## `free` / `routerclaude`
Slash commands criados: `/free` (delegação máxima local + abre FREE.command) e `/routerclaude` (Qwen+DeepSeek+Opus arremate).
Ver [[free_command_local]], [[routerclaude-trigger]]. A integração pesada dá pra fazer no `free` (custo zero).
