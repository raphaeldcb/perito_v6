---
name: ponytail-skill-instalada
description: "ponytail (DietrichGebert) instalada como skill para todas as sessões — modo \"senior preguiçoso\", força solução mínima"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# ponytail — instalada e fixada (09/07/26)

**O que é:** skill que força a solução mais enxuta que funciona ("lazy senior dev"):
YAGNI → já existe no codebase? → stdlib? → recurso nativo? → dep já instalada? →
cabe em 1 linha? → só então o mínimo viável. Reduz código (~54%, até 94% no bench).

**Fixada para todas as sessões:** cópia durável em `~/.claude/vendor/ponytail-skills/`,
com symlinks em `~/.claude/skills/` (mesmo padrão do [[agent-browser-instalado]]).
6 skills: `ponytail` (principal, níveis lite/full/ultra), `ponytail-review`,
`ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`.
Ativa sozinha em tarefas de código; ou digitar "ponytail"/"lazy mode"/"yagni".

**Outras IAs/tools** (rodar no próprio tool): Claude Code
`/plugin marketplace add DietrichGebert/ponytail` + `/plugin install ponytail@ponytail`;
Codex/Copilot têm comandos equivalentes; Cursor/Windsurf/Cline copiam rule file.

**Always-on real:** o repo traz hook `pre_llm_call` (Hermes). Em Claude Code seria
hook no settings.json — NÃO instalado (rodaria JS em todo prompt). Skill via
description já cobre tarefas de código sem digitar nada.
