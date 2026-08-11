---
name: plugins-claude-code
description: "Plugins do Claude Code instalados no Mac — pyright-lsp, frontend-design, superpowers; critério de seleção e o que foi descartado"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Plugins Claude Code instalados (09/07/26)

Instalados via `claude plugin install` (CLI não-interativa). Ativam na próxima sessão.

**Do marketplace oficial `claude-plugins-official`:**
- `pyright-lsp` — LSP Python (type-check/intel) p/ backend FastAPI. **~0 tokens** (out-of-process). Win puro.
- `frontend-design` — UI React de qualidade produção (meta: superar ProjurisADV). ~54 tok/sessão, 1 skill.

**Do marketplace `superpowers-marketplace` (obra) — pedido explícito:**
- `superpowers` v6.1.1 — metodologia de dev (14 skills: brainstorming, TDD, systematic-debugging,
  subagent-driven-development, writing-plans, using-git-worktrees etc). ~482 tok/sessão + hook SessionStart.
  ⚠️ Sobrepõe filosoficamente com [[ponytail-skill-instalada]] (ambos metodologia de dev) — coexistem.

**Descartados de propósito (critério ponytail, não instalar bloat):**
- code-review, code-simplifier → já são skills nativas (/code-review, /simplify)
- playwright, chrome-devtools-mcp, desktop-commander → cobertos por [[agent-browser-instalado]]
- neon/prisma/supabase/cloud-sql-* → Postgres deles é Docker self-hosted (SQLAlchemy+psql), não cloud
- legalzoom → direito dos EUA, não perícia judicial BR
- feature-dev/pr-review-toolkit → redundante c/ review nativo + roster de subagents jurídicos

**Gerenciar:** `claude plugin list|disable|enable|details <nome>@<marketplace>`.
Marketplaces registrados em `~/.claude/plugins/known_marketplaces.json`.
