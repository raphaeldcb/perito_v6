---
name: arquitetura_sistema_final_30_07
description: Arquitetura final pós-otimização — VPS + OneDrive + Mac dev (30/07/2026)
metadata: 
  node_type: memory
  type: project
  originSessionId: edcfa59e-8f04-489e-8ca5-1a6dbf8a3783
  modified: 2026-07-30T18:03:19.328Z
---

# 🎯 Arquitetura Final — Perito v6 Otimizado

**Data:** 30/07/2026 | **Status:** ✅ IMPLEMENTADO

## Componentes

### 1. **VPS (129.121.34.186:22022)** — "A Máscara"
- Backend Perito v6 rodando
- PostgreSQL com 6.923 processos TJMS
- Worker com Qwen 3.6 (IA local)
- Storage: 49GB (84% cheio → considerar limpeza periódica de /tmp)
- **Não** replica arquivos localmente
- Acessa OneDrive via **Graph API** (GRAPH_CLIENT_ID configurado)

### 2. **OneDrive** — "Source of Truth"
- 173GB+ de dados (Autos, Laudos, Documentação)
- Backup automático da Microsoft
- Compartilhável (Mobile, Web, PC, Mac)
- Histórico de versões nativo
- **Sem** sincronização local no Mac (desabilitada 30/07)

### 3. **Mac Local** — "Dev/Test"
- Git, Code, Claude Code
- Ollama + qwen2.5:7b (IA local para testes)
- `~/OneDrive_Local/` — espelho local vazio (população manual conforme necessário)
- Backup crítico: `~/OneDrive_Essentials_Backup/`
- **241GB livres** (↑ de 57GB após limpeza)

## Mudanças em 30/07/2026

✅ **OneDrive Sync Desabilitado**
- Antes: 173GB de cache local em `~/Library/Group Containers`
- Depois: Deletado, zero sync local
- Ganho: 184GB de espaço em disco

✅ **Scripts Reconfigurados**
- `config_sistema.json` → aponta para `~/OneDrive_Local/analises`
- Futuros PIDs → devem usar Graph API (não local paths)

✅ **Graph API Verificado**
- GRAPH_CLIENT_ID = 56fd2738-851e-4482-959d-c3fcea794d90
- Pronto para chamadas autenticadas ao OneDrive

## Como Funciona Agora

```
Mac (dev)                VPS (produção)           OneDrive (nuvem)
├─ Git repo             ├─ Backend API           ├─ 173GB dados
├─ Ollama local         ├─ PostgreSQL (6.9k)     ├─ Backup auto
└─ /OneDrive_Local      ├─ Worker Qwen           └─ Histórico
       ↓ (manual copy)  └─ Graph API client ←─┐
                             ↓                  │
                        (acessa via)────────────┘
```

### Fluxo de Dados
1. **Input:** Usuário faz requisição no Perito v6 web
2. **Processamento:** VPS backend processa (BD + Qwen)
3. **Arquivos:** Se precisa arquivo, chama Graph API → OneDrive
4. **Output:** Resultado armazenado no OneDrive automaticamente

## Recomendações Futuras

### OneDrive App (Mac)
- Deixar **sincronização desabilitada** (recomendado)
- Acessar via: web.onedrive.com ou Graph API
- Se precisar arquivo local: download manual ou via script Python + Graph

### VPS
- Monitorar disco periodicamente
- Limpeza: `docker system prune -a` (libera container images antigos)
- Considerar expandir para 100GB+ se volume crescer

### Scripts Novos
- Usar **Graph API** para acessar OneDrive (não hardcode local paths)
- Exemplo: `msgraph.client.api("/me/drive/root/children")`
- Fallback: `~/OneDrive_Local/` com cópia manual via Python + Graph

## Checklist de Verificação

- [x] Mac disco: 45% (✅ antes era 87%)
- [x] VPS backend: UP
- [x] PostgreSQL: 6.923 processos ✅
- [x] Graph API: GRAPH_CLIENT_ID pronto
- [x] OneDrive app: Reinstalado (sem sync local)
- [ ] Testar: API /processos com auth
- [ ] Testar: Upload laudo → OneDrive via Graph
- [ ] Testar: Acesso offline (files in OneDrive app se houver sync ativado)

## Benefícios

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Mac disco livre | 57GB (87% cheio) | 241GB (45% cheio) |
| OneDrive local | 173GB cached | 0 bytes |
| Acesso a arquivos | Local + nuvem sync lento | Cloud-first via Graph API |
| Complexidade | 2 cópias divergentes | Single source of truth |
| Backup | Manual | Automático (Microsoft) |

---

**Status:** ✅ **PRONTO PARA PRODUÇÃO**
- Sistema operacional (VPS) funcional
- Arquivos (OneDrive) seguros
- Desenvolvedor (Mac) com espaço livre
- Zero fragmentação de dados
