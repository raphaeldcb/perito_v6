---
name: feedback_nao_refazer_frontend
description: NUNCA reconstruir o frontend — só atualizar/incrementar o existente. E verificar na UI real antes de dizer que resolveu.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# NUNCA reconstruir o frontend — atualizar

Bruno já teve que refazer o trabalho **4 vezes** por eu reconstruir em vez de atualizar.

**Regra:** mexer no frontend que já existe, incrementalmente. Nada de página nova
paralela, nada de reescrever do zero. Melhorar layout = editar o componente atual.
Usar as ferramentas dele (react-specialist, frontend-design, mp-codebase-design).

**Why:** ele perde horas revalidando; destrói confiança; é a principal fonte de
irritação ("não quero te xingar").

**How to apply:** antes de tocar em .jsx, ler o componente atual e EDITAR. Nunca
criar `XyzNovo.jsx`. Ver [[feedback_v6_shell_vazio]] (testar o que o usuário VÊ ao logar).

# "Resolve sem resolver" — VERIFICAR na UI real

Eu venho dizendo que conserto e não conserta. Causa: mexo no código e não testo o
que o usuário vê. **Regra:** todo conserto de fluxo tem que ser reproduzido LOGADO
no sistema real (agent-browser) ANTES (para ver o bug) e DEPOIS (para provar que
sumiu). Só digo "resolvido" com evidência da UI, não do código.
