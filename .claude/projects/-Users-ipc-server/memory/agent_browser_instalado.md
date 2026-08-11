---
name: agent-browser-instalado
description: "agent-browser (Vercel Labs) instalado globalmente no Mac — automação de browser para IAs, skill fixada em ~/.claude/skills"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# agent-browser — instalado e fixado (09/07/26)

**O que é:** CLI Rust de automação de browser para agentes de IA (Vercel Labs).
Chrome via CDP, snapshots de accessibility-tree, refs `@eN`.

**Instalação:** `brew install agent-browser` (v0.31.1) + `agent-browser install`
(Chrome for Testing 150 em `~/.agent-browser/browsers/`).

**Fixado para todas as IAs:** skill em `~/.claude/skills/agent-browser` →
symlink para `/opt/homebrew/opt/agent-browser/libexec/lib/node_modules/agent-browser/skills/agent-browser`
(caminho `opt` sobrevive a upgrades do brew). Vale para todas as sessões/projetos deste Mac.

**Uso básico:**
- `agent-browser open <url>` / `read` / `click <sel>` / `fill <sel> <texto>` / `screenshot`
- `agent-browser skills get core --full` — guia completo (ler antes de usar a fundo)
- Skills especializadas: `dogfood` (testar web app procurando bugs), `electron`, `slack`
- `agent-browser upgrade` para atualizar

**Smoke test validado:** abriu https://sistema.ipcms.com.br e leu a tela de login. ✅

**Importante:** funciona LOCALMENTE no Mac (Chrome for Testing) — para tarefas de
browser simples (testar UI do Perito, screenshots, formulários) pode dispensar o
desvio pela VPS descrito em [[feedback_selenium_nao_funciona]]. ESAJ/automação
pesada com Selenium continua na VPS até provar o contrário.
