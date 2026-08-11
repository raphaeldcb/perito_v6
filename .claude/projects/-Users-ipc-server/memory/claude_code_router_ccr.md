---
name: claude-code-router-ccr
description: CCR (claude-code-router) instalado p/ rotear Qwen (pesado) + DeepSeek (supervisão) + Opus 4.8 (arremate, fallback Fable)
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
  modified: 2026-07-27T15:24:23.464Z
---

# claude-code-router (CCR) — roteamento em camadas (10/07/26)

Instalado `@musistudio/claude-code-router` **FIXO na 1.0.73** (a v3.0.3 é toda por UI/SQLite,
inviável de configurar headless → dei downgrade pro formato clássico `config.json`).
Binário: `/opt/homebrew/bin/ccr`. Config: `~/.claude-code-router/config.json` (chmod 600).

## Camadas configuradas (Router) — atualizado 10/07
- `default` → **qwen2.5-coder:14b** (Ollama, Apache-2.0) = melhor coder OSS p/ o `ccr code`. RAM Mac=24GB
  (por isso 14b, não 32b). `background` → **perito-qwen:latest** (geral barato).
- (também baixado **bge-m3** p/ RAG pt-BR — melhor que nomic; migração 768→1024d + reindex é FUTURA, não feita.)
- `think` + `longContext` (>60k) + `webSearch` → ⚠️ **27/07/26 mudado p/ LOCAL** `deepseek-coder-v2:16b` (provider `deepseek-local`, Ollama; baixei ~9GB). Era deepseek-nvidia cloud (queimava token). CCR agora 100% local. Provider NVIDIA fica na config mas fora das rotas (backup `config.json.bak-*`). `default`/`background` = Qwen local.
- **Opus 4.8 = arremate (PLANO MENSAL)** ⚠️ atualizado 25/07/26 (era Fable 5): NÃO há chave
  Anthropic avulsa → CCR não roteia p/ Claude. O arremate é o **`claude` normal** (assinatura).
  Default agora é `model: "opus"` no settings.json. Fallback: **Opus 4.8 → Sonnet** se indisponível/
  no limite, via alias no `~/.zshrc`: `alias arremate='claude --model opus --fallback-model Sonnet'`.
  ⚠️ Fable virou PAGO (exige créditos) → não serve mais de fallback; Sonnet está no plano.
  Tudo no plano, sem gastar API.

## Provider DeepSeek = NVIDIA NIM
- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
- Key (nvapi-…, prefixo NVIDIA) só no config local. ⚠️ Foi colada no chat — rotacionar se vazar.
- Modelos disponíveis testados: `deepseek-ai/deepseek-v4-pro` (forte) e `deepseek-ai/deepseek-v4-flash`.

## Como usar
- **Clicável:** `~/Desktop/ROUTERCLAUDE.command` — sobe o router, entra na pasta do Perito e abre
  `ccr code` JÁ semeado com um resumo do que fizemos/instalamos + ordem de ler MEMORY.md e CLAUDE.md
  (pra não perder contexto / não refazer trabalho). É a forma padrão de abrir a rota Qwen+DeepSeek.
- **Trabalho pesado (Qwen + DeepSeek):** `ccr code` na pasta do projeto → sobe Claude Code apontando
  pro router (:3456). Qwen dirige o grosso; DeepSeek entra no raciocínio/contexto longo.
  Dentro dele, `/model deepseek-nvidia,deepseek-ai/deepseek-v4-pro` força o DeepSeek.
- **Arremate:** rodar `arremate` (= `claude --model opus --fallback-model Sonnet`) — plano mensal.
- Controle: `ccr status`, `ccr restart`, `ccr stop`. Auto-sobe no `ccr code`.

## Testado E2E (10/07)
`default`→ HTTP200 `model: perito-qwen:latest` (Qwen respondeu de verdade com budget ≥2000 tok;
com pouco token vem vazio pois o perito-qwen "pensa"). Rota DeepSeek→ HTTP200 "DEEPSEEK-OK".

## Convivência
Existe também o [[router-9router-qwen-fallback]] (:20128, fallback quando a cota do Claude
esgota) — mecanismo à parte. CCR só afeta sessões abertas com `ccr code`; não mexe no `claude` normal.
