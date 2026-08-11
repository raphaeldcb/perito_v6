---
name: feedback_nada_fake_producao
description: NADA de dado fake/teste em produção — o sistema vai para uso real do pessoal
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# NADA de fake em produção (regra do Bruno, 09/07/26)

O v6 vai para **produção, uso do pessoal**. **Nenhum dado fake/teste** pode ficar
no banco de produção.

**Why:** é o sistema real da empresa; dado fake polui, confunde o time e quebra a
confiança. Bruno é explícito: "nada de fake quero colocar em produção".

**How to apply:**
- Ao testar E2E, se criar laudo/ofício/processo/intimação de teste, **APAGAR depois**.
- Antes de qualquer entrega "de produção", auditar e limpar artefatos de teste meus.
- O banco VIVO do sistema antigo no VPS (/var/www/perito/data/perito.db) é SEED de
  teste (188 fake) — NUNCA migrar dele. Dado real = backup OneDrive/checkpoint.
- Já limpei nesta sessão: laudos 1-3 e ofícios 1-4 (meus testes do Fluxo Completo).

**Estruturar dado real com lógica:** ao migrar, não deixar pilha de pendentes.
Ex: as 694 "oportunidade" (leads de captação DJE) foram separadas do painel de
intimações (só 141 reais aparecem; oportunidades via ?incluir_oportunidades=true).
Ver [[sistema-antigo-passo2]].
