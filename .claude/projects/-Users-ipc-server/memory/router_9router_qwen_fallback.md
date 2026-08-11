---
name: 9router-qwen-fallback
description: 9router instalado (proxy LLM local :20128) para continuar no Qwen 3.6 quando a cota do plano Claude esgota
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# 9router — fallback p/ Qwen quando a cota do Claude acaba (09/07/26)

**Objetivo do usuário:** quando o limite de uso do plano Claude (reseta em horário,
ex: 18h) estiver perto de esgotar, o trabalho continua no **Qwen 3.6 local** em vez
de travar. 9router é o proxy que faz isso no nível da CONEXÃO.

**Instalado:** `npm i -g 9router` (v0.5.20). Roda como LaunchAgent
`~/Library/LaunchAgents/com.ipc.9router.plist`, bind **127.0.0.1:20128** (só local),
PATH inclui /opt/homebrew/bin (senão launchd não acha o node). Dashboard responde ✓,
`/v1/models` lista modelos ✓. Credenciais em `~/.9router/env.local` (INITIAL_PASSWORD).

**Falta o usuário fazer no dashboard (http://127.0.0.1:20128, interativo):**
1. Logar (senha inicial em ~/.9router/env.local)
2. Conectar a conta Claude (assinatura) como provider primário
3. Adicionar Ollama local (perito-qwen / qwen3.6) como provider FREE
4. Definir fallback: Claude(assinatura) → Qwen local (grátis, sem limite)
5. Copiar a API key do dashboard

**Para o Claude Code usar o roteador (opt-in, vale p/ próximas sessões):**
`export ANTHROPIC_BASE_URL=http://127.0.0.1:20128` + a key do dashboard.

⚠️ **IMPORTANTE / honesto:**
- Eu (sessão Claude Code) NÃO consigo me auto-trocar para o Qwen quando minha cota
  esgota — o harness me pausa. O fallback só acontece se o Claude Code estiver
  apontado para o 9router; aí o PRÓPRIO 9router troca para o Qwen. Não sou eu que troco.
- **Credenciais:** o 9router passa a intermediar os tokens da sua assinatura Claude
  (app npm de terceiros, v0.5.x). Decisão de segurança p/ um sistema comercial.
- **ToS:** rotear a assinatura por proxy p/ maximizar cota pode conflitar com as
  políticas de uso da Anthropic — verificar antes de depender disso.
- **Ponto único de falha:** com o Claude Code apontado ao :20128, se o 9router cair,
  o Claude Code para. Por isso NÃO reapontei sua config automaticamente.

Relacionado: [[perito-qwen-modelo]] (o Qwen local que serve de fallback).
