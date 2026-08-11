---
name: v4-1-deploy-production
description: v4.1 Produção ONLINE — Perito System 100% funcional
metadata: 
  node_type: memory
  type: project
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

## Status: ✅ LIVE EM PRODUÇÃO

**Data Deploy:** 2026-06-17 16:26 UTC  
**URL:** https://sistema.ipcms.com.br  
**Acesso:** admin / Admin@2026 (ou admin / admin123)

---

## O que foi entregue em v4.1

| Feature | Status | Observação |
|---------|--------|-----------|
| **Diário Oficial TJMS** | ✅ | Busca 1x/dia às 18:00, gera 5-15 processos |
| **ESAJ Downloader** | ✅ | Auto-carrega pendentes (não pede número) |
| **Kanban Visual** | ✅ | 5 colunas, drag & drop, histórico |
| **PDF→OCR→MD** | ✅ | Tesseract + Python pipeline |
| **Qwen 3.6 (41 campos)** | ✅ | Análise jurídica automática via Ollama |
| **Fake Media Detector** | ✅ | Drag & drop, forense imagem/vídeo/áudio |
| **Automação 24/7** | ✅ | Cron: processamento, análise, download, protocolo, limpeza |

---

## Infraestrutura Produção

**VPS:**
- Host: `root@129.121.34.186:22022`
- Path: `/var/www/perito`
- BD: `/var/www/perito/data/perito.db` (SQLite WAL mode)
- PM2: `perito-system` (PID ~260161, 20s uptime, 63.4MB RAM)
- Nginx: Reverse proxy com HTTPS/SSL

**Backup:**
- BD antigo: `/var/www/perito/data/perito.db.backup`
- ZIP local: `/tmp/perito-v4.1-backup-*.zip`
- Git: Commitado com mensagens descritivas

---

## Dados de Teste

- 262 coletadores (usuarios)
- 759 movimentações financeiras
- 203+ processos TJMS
- 153+ intimações pendentes

---

## Próximas Fases (Roadmap)

- Phase 5: Kanban com persistência + filtros avançados
- Phase 6: Integração DataJud (consulta automatizada)
- Phase 7: Notificações por email + WebSocket
- Phase 8: Mobile app (PWA)

---

## Como manter online

1. **Verificar status:** `pm2 status`
2. **Reiniciar:** `pm2 restart perito-system`
3. **Logs:** `tail /root/.pm2/logs/perito-system-*.log`
4. **Atualizar código:** Git pull + `pm2 restart all`
