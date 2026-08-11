---
name: mattpocock-skills
description: mattpocock/skills — 7 curados instalados (mp-*), 28 completos no vendor p/ on-demand
metadata:
  type: reference
---

# mattpocock/skills instaladas (09/07/26)

28 skills do Matt Pocock. Instalados **7 curados** (genéricos, não-redundantes) em
`~/.claude/skills/` com prefixo `mp-`; os 28 completos em
`~/.claude/vendor/mattpocock-skills/` para on-demand.

**Curados:** mp-diagnosing-bugs, mp-research, mp-domain-modeling, mp-codebase-design,
mp-implement, mp-git-guardrails-claude-code (bloqueia git perigoso via hooks),
mp-handoff (compacta contexto — casa com "não perder contexto/token").

**Descartados:** pessoais do Matt (obsidian, edit-article), presos ao issue-tracker
dele (to-spec/to-tickets/triage/wayfinder/ask-matt), TS-específicos (shoehorn, husky),
redundantes (tdd→[[superpowers]], code-review→nativo, grilling×3).

**Adicionar mais:** `cp -R ~/.claude/vendor/mattpocock-skills/<cat>/<nome> ~/.claude/skills/`.
