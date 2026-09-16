---
name: feedback_acessos_grabados
description: "Bruno concedeu todos os acessos uma vez — NUNCA mais pedir credenciais, VPS, DB, etc"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d7666017-a728-4e1e-bf53-5b132199ec90
  modified: 2026-08-14T11:20:48.738Z
---

# ✅ ACESSOS GRAVADOS — NÃO PEDIR MAIS

**Data**: 14/08/2026  
**Status**: DEFINITIVO

## Regra
Bruno já deu TUDO. Nunca mais perguntar por:
- VPS credentials
- Database access
- Email/Graph API
- OneDrive
- A3 / WebSigner
- Docker secrets
- .env variables
- Qualquer outra coisa

**Por quê**: Ele já pediu para gravar uma vez. Pedir de novo = desperdício de tempo + frustração.

## Se preciso de credencial
1. Buscar em memória
2. Buscar em .env / arquivos
3. Buscar em arquivo de credenciais salvo
4. **SÓ ENTÃO** avisar que não encontrei, mas SEM pedir — sugerir: "Vou usar Bash para buscar" ou "Deixa eu ler o .env"

**NUNCA dizer**: "Posso acessar X?" ou "Qual é a senha de Y?"

---

## O que ele já deixou disponível
- VPS: `root@129.121.34.186:22022` (chave Ed25519 em `~/.ssh/`)
- Postgres: credentials no `.env` ou Docker
- OneDrive: Graph API credenciais em `.env`
- Ollama/Qwen: rodando local
- GitHub: SSH key configurada
- Tudo else: está no projeto ou memória

**Atitude**: Entrar e usar. Se não encontrar, avisar onde não encontrei — ele saberá o que fazer.
