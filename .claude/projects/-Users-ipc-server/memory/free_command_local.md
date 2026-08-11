---
name: free_command_local
description: "27/07/26 — comando 'free': Claude Code 100% local (Qwen+DeepSeek via CCR), custo ZERO de token Claude. Alternativa ao routerclaude sem Opus."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-27T17:27:15.877Z
---

# `free` — sessão Claude Code 100% local (custo zero)

`free` = `ccr code` = abre o Claude Code roteado **só pelos modelos locais** (Ollama via CCR :3456):
- **default/background** → Qwen (`qwen2.5-coder:14b` / `perito-qwen`) = braçal
- **think/longContext/webSearch** → `deepseek-coder-v2:16b` = supervisão
- **Zero Claude/Opus** → **custo zero de token**.

## `free` vs `routerclaude`
- **routerclaude** = Qwen + DeepSeek + **Opus no arremate** (gasta token Claude no meu passo).
- **free** = Qwen + DeepSeek **só** (sem Claude) — pra trabalho pesado/volume sem gastar nada.

## Como usar
- Terminal: `alias free='ccr code'` (no ~/.zshrc) — ou dois cliques em **`~/Desktop/FREE.command`**.
- Requer CCR de pé (`ccr start`); config 100% local em `~/.claude-code-router/config.json`.
Relacionado: [[routerclaude-trigger]], [[claude-code-router-ccr]].
