---
name: free_command_lento_ram
description: FREE.command lento/quebrado = 2 causas (35B vaza p/ CPU em 24GB + Claude Code força thinking → modelo sem thinking dá 400); fix TESTADO = qwen3:14b
metadata: 
  node_type: memory
  type: reference
  originSessionId: e7c45933-ce0e-4235-b3f8-5d8d1369984c
  modified: 2026-07-28T01:16:35.414Z
---

27/07/26 — **FREE.command demorando/quebrado teve DUAS causas raiz (ambas resolvidas e testadas):**

**Máquina:** Mac M4 Pro, **24 GB RAM**. Teto GPU (Metal) endereçável ≈ 16-18 GB (`iogpu.wired_limit_mb=0` = default).

**Causa 1 — modelo grande demais (lentidão):** CCR roteava pro `perito-qwen`/`batiai/qwen3.6-35b:iq4` (34,7B, 18-21GB). Não cabe em 24GB → `ollama ps` mostrava **19%/81% CPU/GPU** → vaza pra CPU → arrasta. O `qwen3.6-35b` é `qwen35moe` (**MoE**, geração mais nova, ótimo modelo) — mas MoE que vaza pra CPU perde a vantagem.

**Causa 2 — thinking obrigatório (erro 400):** o Claude Code **sempre manda `thinking:enabled`** (MAX_THINKING_TOKENS=0 NÃO desliga — testado). O CCR 1.0.73 converte isso e manda **`reasoning_effort`** pro Ollama. Modelo SEM capacidade de thinking → `400 "does not support thinking"`. Testado no Ollama direto: `reasoning_effort`→400; `enable_thinking`→200.

**⚠️ CORRIGE nota anterior:** `qwen2.5-coder:14b` e `deepseek-coder-v2:16b` **NÃO servem** pro FREE — cabem na GPU mas dão **400** (não têm thinking). Só a família **Qwen3** aceita o "pensar".

**FIX aplicado e TESTADO ✅:** baixei `qwen3:14b` (dense, thinking-capable, 9,3GB) e apontei TODAS as rotas do CCR (`~/.claude-code-router/config.json`) pra ele. Resultado: request com thinking = **HTTP 200**, `ollama ps` = **100% GPU** (10GB, zero CPU), quente ~7s. Backup em `config.json.bak`. FREE.command com cabeçalho atualizado.

**Tradeoff:** Qwen3 pensa MUITO (177 tokens de raciocínio pra responder "4"). Na GPU tá ok, mas trivial leva alguns segundos. Se pesar: `qwen3:8b` (pensa mais rápido) ou forçar no_think. Bruno escolheu **manter o 14b — "qualidade sempre"**.

**Carregamento a frio resolvido:** FREE.command agora pré-carrega e FIXA o modelo em background ao abrir — `curl .../api/generate -d '{"model":"qwen3:14b","keep_alive":-1}' &`. `ollama ps` mostra `UNTIL: Forever`. Custo: 10GB fixos na RAM enquanto o Ollama roda; soltar = `ollama stop qwen3:14b` (re-fixa no próximo FREE).

**Se quiser o 35b MoE (melhor modelo) COM velocidade:** `sudo sysctl iogpu.wired_limit_mb=21504` faz os 18GB caberem ~100% GPU (reseta no reboot; deixa só ~2,5GB pro macOS — arriscado com Chrome/Docker abertos).

Relacionado: [[free_command_local]] · [[claude_code_router_ccr]] · [[perito_qwen_modelo]]
