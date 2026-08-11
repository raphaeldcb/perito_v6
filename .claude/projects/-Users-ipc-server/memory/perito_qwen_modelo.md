---
name: perito-qwen-modelo
description: Modelo Ollama perito-qwen (Qwen 3.6 + SYSTEM destilado do Fable 5) usado pelo mac_agent para análise e laudos
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# perito-qwen — modelo local do Perito (09/07/26)

Derivado de `batiai/qwen3.6-35b:iq4` via Modelfile com SYSTEM destilado dos
princípios de comportamento do Fable 5, adaptados à perícia: comunicação direta,
sem escusa genérica, honestidade técnica absoluta (nunca inventar lei/valor/fls.),
neutralidade, evidência por conclusão. Alinha [[feedback_sem_desculpas_genericas]]
e [[feedback_analise_direta]].

**Definição versionada:** `v6/ollama/Modelfile.perito` (+ README + fable5 de referência).
Compartilha blobs do base (sem disco extra); base mantido como fallback.

**Em uso:** `OLLAMA_MODEL=perito-qwen:latest` no LaunchAgent
`~/Library/LaunchAgents/com.ipc.perito-mac-agent.plist`. Cobre `analise_ia` e
`gerar_laudo` no mac_agent.

**Recriar após editar Modelfile:**
`ollama create perito-qwen -f v6/ollama/Modelfile.perito && launchctl kickstart -k gui/$(id -u)/com.ipc.perito-mac-agent`

**Decisão importante:** o system prompt vazado do Fable 5 (fable-ipc.md, ~34k tokens)
NÃO foi injetado verbatim — é identidade Claude + ferramentas Anthropic, que
inchariam o contexto e confundiriam a identidade. Só os princípios foram destilados.
Backup do vazamento em ~/Downloads/fable-ipc.md e v6/ollama/fable5-system-prompt-referencia.md.
