---
name: commit_automatico_padrao
description: Usuário quer que commits sejam feitos automaticamente após trabalho significativo
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

**Regra:** Faça commit + push automático após completar tarefas significativas.

**Por quê:** Usuário explicitou "torne padrão" — quer evitar ter que pedir a cada vez.

**Como aplicar:**
- Após completar funcionalidade/correção/restauração, faça `git add -A`
- Redija mensagem descritiva com tópicos do trabalho
- `git commit -m "..."`
- `git push origin [branch]` (se remote estiver configurado)
- Mostre ao usuário o resultado (commits, push status)

**Exceções:**
- Se não houver remote configurado, avise e forneça comando para configurar
- Se houver conflitos ou hook failures, pare e comunique

**Status:** Remote não está configurado neste projeto. Commit foi feito ✅, push bloqueado ❌.
