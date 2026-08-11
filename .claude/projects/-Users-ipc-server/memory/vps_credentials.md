---
name: vps-credentials-ipc
description: Credenciais e endpoints VPS perito-system (não compartilhar)
metadata: 
  node_type: memory
  type: reference
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

## VPS Perito-System

**URL:** https://sistema.ipcms.com.br

**Credenciais:**
- User: admin
- Senha: Admin@2026
- JWT_SECRET: ***REMOVED***

**Acesso:**
- SSH: [salvar depois com Bruno]
- Banco dados: [salvar depois com Bruno]
- Documentação: [interna do servidor]

**APIs disponíveis:**
- POST /api/auth/login
- POST /api/pareceres/upload
- POST /api/analises/upload
- GET /api/analises/{id}

**Próxima fase:**
Após aprovação do sistema local, fazer deploy com Docker/CI-CD.
