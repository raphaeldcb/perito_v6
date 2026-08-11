---
name: routerclaude-trigger
description: "Quando Bruno escreve \"routerclaude\", entrar em modo orquestração (Qwen pesado + DeepSeek supervisão + Opus 4.8 arremate) SEM sair da sessão atual"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
  modified: 2026-07-27T15:24:12.092Z
---

# Gatilho "routerclaude" — modo gestão de IA (10/07/26, arremate → Opus 4.8 em 25/07/26)

Quando o Bruno escrever **"routerclaude"** numa sessão minha (Opus/Fable, plano),
entrar em **modo orquestração** — eu dirijo e faço o arremate, delegando o pesado:

- **Qwen local** (Ollama `http://127.0.0.1:11434`, modelo `perito-qwen:latest`) → o grosso,
  volume, rascunhos, tarefas repetitivas. Chamo via `curl` (`/api/generate` com `"think":false`
  p/ não gastar token pensando, ou `/v1/chat/completions`).
- **DeepSeek** = supervisão, **agora LOCAL** via CCR → `deepseek-coder-v2:16b` (Ollama, baixado 27/07/26, ~9GB,
  MoE genuíno = 2ª opinião de arquitetura diferente do Qwen). ⚠️ 27/07 tirei o DeepSeek-NVIDIA (nuvem) das rotas
  think/longContext/webSearch — queimava token. CCR agora **100% local** (backup `config.json.bak-*`; provider nvidia
  fica na config mas fora das rotas). `ollama pull deepseek-r1:32b` seria alternativa (raciocínio), mas é distill de Qwen (menos diversidade).
- **Eu (Opus 4.8)** → SÓ planejo, reviso e faço o **arremate final**. Fallback **Sonnet**. `settings.json` fixa `"model":"opus"`.

## 27/07/26 — ESCADA DE COMPLEXIDADE (auto-tier das IAs Claude) — pedido do Bruno
Objetivo: tarefa simples usa modelo barato, sobe até Opus só no que vale. **Sem ANTHROPIC_API_KEY** → CCR NÃO roteia
Claude; a escada Claude sai por **subagents** (Agent tool, param `model:`, nativo, consome cota do plano — Haiku consome bem menos que Opus). Eu sou o roteador (classifico e despacho):

| Complexidade | Executor | Como |
|---|---|---|
| Braçal/volume (OCR, regex em N arquivos, parse, rascunho) | **Qwen local** | curl Ollama / `ccr code` — **grátis, 0 cota** |
| Supervisão/2ª opinião/contexto longo | **DeepSeek local** | via CCR (think/longContext) — grátis |
| Simples e bem-escopado que precisa de Claude | **subagent Haiku** | `Agent(model:"haiku")` |
| Médio (código padrão, análise) | **subagent Sonnet** | `Agent(model:"sonnet")` |
| Difícil / arquitetura / decisão / arremate | **Opus (eu)** | sem despacho |

⚠️ **Ressalva de custo**: subagent parte "frio" (re-deriva contexto = caro no cold-start). Só vale despachar p/ Haiku/Sonnet
tarefa **auto-contida, bem-escopada e substancial**. Coisa trivial vai pro **Qwen local (grátis)**, não pra subagent.
Dentro de sessão eu NÃO troco meu próprio modelo (fixo no launch) — a escada é via subagent OU escolha no `ccr code`.
Se um dia houver ANTHROPIC_API_KEY, dá pra rotear Haiku/Sonnet/Opus direto no CCR por tipo de request.

## ⚠️ 27/07/26 — ECONOMIA DE TOKEN OPUS (feedback direto do Bruno: "está usando muito token")
O gargalo é **MEU** (Opus), não a nuvem. Regra em modo routerclaude — **manter meu contexto enxuto**:
- **NÃO puxar arquivo/output grande pro meu contexto.** Qwen local processa (OCR, extração, varredura em lote,
  parse) e me devolve **só o resumo/resultado**. Eu não leio o volume, leio o destilado.
- **Trabalho em lote via script** rodando em background; eu vejo o `tail`/resumo final, não cada passo.
- **Delegar o grind** (repetição, OCR, regex em N arquivos, rascunho) ao Qwen; eu decido/arremato.
- **Fallback = colar manual, SEM API** (blueprint do PDF *Orchestrator.js — 100% local*, em Downloads):
  quando o local falha, gerar `.txt` com prompt pronto p/ o Bruno colar no **claude.ai (web)** — não gasto token de API.
- Anti-exemplo real: sessão dos boletos (27/07) fez ~70 tool-calls no meu contexto = caro. Era p/ ter delegado o loop ao Qwen.

**Why:** Bruno paga meu token; o valor do Opus é decisão/arremate, não braçal. Braçal é grátis no Qwen local.
**How to apply:** ao ver "routerclaude", confirmo curto, **delego o pesado ao Qwen local e só trago o resultado**;
digo qual modelo fez o quê; arremato enxuto. Terminal: alias `routerclaude` / `~/Desktop/ROUTERCLAUDE.command`;
`arremate` = `claude --model opus --fallback-model Sonnet`. Relacionado: [[claude-code-router-ccr]].
