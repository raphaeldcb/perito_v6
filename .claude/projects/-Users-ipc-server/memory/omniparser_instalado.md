---
name: omniparser-instalado
description: "Microsoft OmniParser v2 instalado local no Mac — screenshot → elementos de UI (JSON), comando global omniparse + skill"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# OmniParser v2 — instalado (09/07/26)

Visão computacional: screenshot → elementos de UI estruturados (OCR texto + YOLO
ícones + legenda Florence-2). Local no Mac (M4 Pro, MPS), ~10s por imagem.

**Comando global:** `omniparse <img> [--out j.json --annotated a.png --no-caption]`
(wrapper em `~/.local/bin/omniparse` → venv em `~/projects/OmniParser/.venv`).
Skill em `~/.claude/skills/omniparse` para todas as sessões. Testado: 44 elementos
do screenshot do Perito ✓.

**Quando usar vs [[agent-browser-instalado]]:** OmniParser só quando NÃO há DOM/a11y
(app desktop, tela remota, portal via imagem, formulário escaneado). Para web ao vivo,
agent-browser é melhor (a11y tree limpo, sem modelo de visão). OCR de PDF já é Tesseract.

**Instalação (não trivial no arm64):**
- venv 3.12 via uv; instalado só o NÚCLEO (pulei uiautomation=Windows-only,
  paddlepaddle/paddleocr=quebram no arm64, e as libs de demo/agente cloud)
- `transformers==4.49.0` FIXO (5.x quebra o Florence-2: forced_bos_token_id)
- Patches em `util/utils.py`: paddle preguiçoso (não inicializa no import) +
  Florence em float32 no MPS/CPU (float16 só CUDA → dtype mismatch)
- Pesos: microsoft/OmniParser-v2.0 via `hf download` (YOLO 39MB + Florence 1GB)

⚠️ **LICENÇA:** o modelo icon_detect é **AGPL** (herdado do YOLO). Uso comercial no
produto do Perito (IPCMS é empresa) pode disparar obrigações AGPL — avaliar antes de
embutir em produção. O caption (Florence) é MIT.
