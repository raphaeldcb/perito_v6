---
name: acervo-laudos-onedrive
description: Acervo de ~9.725 laudos reais no OneDrive (LAUDOS) já rotulados por área/tipo — ouro para RAG e classificação de área pelo Qwen
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Acervo de laudos (OneDrive) — a "coisa boa" (09/07/26)

Pasta: `~/Library/CloudStorage/OneDrive-BibliotecasCompartilhadas-IPCMSPERICIASLTDA/IPCMS - ARQUIVOS/`

**LAUDOS/** — ~**9.725 arquivos** de laudo (docx+pdf), organizados por processo.
O nome codifica a classificação (dataset rotulado):
`NNNN.AA.<AREA>.<TIPO>.NN (Autos <CNJ>).docx`
- **ÁREA** (3º campo): 20=contábil (1317), 30=engenharia (189), 10=(132),
  **40=grafotécnica/documentoscópica (71 — "perícia na assinatura")**, 50=(7), 00=(2)
- **TIPO**: JD=judicial (1538), EX=extrajudicial (135)

**MODELOS_SISTEMA/** — `template_mapping.json` + `templates/` + `originais/`
(mapeia área→template de laudo). **IPCMS - 40-GRAFOTECNICA/** = laudos de assinatura.

## Por que importa (o que o Bruno cobrou)
DOC/TIPO/ÁREA **NÃO são entrada manual** — são o que o **Qwen+RAG devem classificar**
a partir da intimação (ex: juiz diz "perícia na assinatura" → área 40 grafotécnica).
Este acervo é o gabarito: alimentar o [[rag-pgvector-pipeline]] com esses laudos
ensina estrutura + área + linguagem real; e o loop do Passo 3 (Bruno corrige → vira
gabarito) refina. Indexar em lote via job `indexar_rag` (origem="laudo", com a área
do nome como metadado).

Relacionado: [[perito-qwen-modelo]], [[vinculo-intimacao-processo]].
