---
name: piloto-teste-cego-laudos
description: "Piloto Passo 3 — teste cego de laudos (pasta BRUNO): gerar laudo dos autos e comparar com o protocolado"
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Piloto teste cego de laudos (Passo 3) — 09/07/26

**Objetivo do Bruno:** o sistema gera um laudo "do seu jeito" (TESTE CEGO — sem ver o
protocolado) a partir dos autos, e depois compara com o laudo real protocolado. Loop
de aprendizado: onde errar, vira gabarito no RAG.

**Pasta:** `~/Library/CloudStorage/OneDrive-...IPCMSPERICIASLTDA/IPCMS - GERENCIA/DIRETORIA/Testes IA/BRUNO`
- **20 casos contábeis** (L2019.032 ... L2024.151). Grafotécnica é mais difícil de
  padronizar (análise em si) — começar por contábil.
- Cada pasta: **autos** (PDF grande, ex. 62 MB — `<CNJ>.pdf`) + **laudo protocolado**
  (ex. `L2019-032-33.pdf`).

**Estrutura NOVA do laudo (alvo) — em blocos** (ex. `IPCMS - ARQUIVOS/LAUDOS/1077.25.10.JD.47`):
`I - INTRODUÇÃO`, `II - ANÁLISES E CÁLCULOS (fixa/variável)`, `III - QUESITOS`,
`IV - CONCLUSÃO`, `V - ANEXOS`, + `RESPOSTA TÉCNICA ÀS IMPUGNAÇÕES` + REFERENCIAS + xlsx.
(Estrutura antiga = laudo único; nova = separada por blocos.)

**Plano:** por caso — extrair texto dos autos (pypdf/OCR) → RAG puxa trechos
relevantes → perito-qwen gera laudo nos 5 blocos → diff vs protocolado → Bruno
corrige → gabarito no [[rag-pgvector-pipeline]]. Autos são enormes: usar
recuperação (não enfiar tudo no contexto). Começar por 1 caso (o de autos menor)
como prova, ajustar prompt, escalar p/ os 20.

Relacionado: [[perito-qwen-modelo]], [[acervo-laudos-onedrive]] (área no nome).
