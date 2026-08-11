---
name: vps-ssh-prod
description: "Credenciais SSH VPS Perito-System produção (seguro, não compartilhar)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

## VPS SSH — Perito-System Produção

**Host:** `root@129.121.34.186`  
**Porta:** `22022`  
**Chave SSH:** `/Users/ipc_server/.ssh/id_ed25519_perito`  

**Comando rápido:**
```bash
ssh -i /Users/ipc_server/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186
```

**Diretórios importantes:**
- Sistema: `/var/www/perito/`
- Versão 5.2: `/var/www/perito-v5.2/`
- Logs: `/var/www/perito/logs/`
- Banco: `/var/www/perito/data/perito.db`

**Processos:**
```bash
# Listar node.js rodando
ps aux | grep node

# Matar processo
pkill -f "node src/server.js"

# Iniciar
cd /var/www/perito-v5.2 && npm start
```

**URL produção:** https://sistema.ipcms.com.br:3000
