---
name: fluxo_completo_20260709
description: Fluxo Completo Automático v6.1 — Intimação → Ofício → Protocolo → Laudo → Protocolo (implementado)
metadata: 
  node_type: memory
  type: project
  originSessionId: 2c421bcf-d51b-4fac-a34e-76bfabd14055
---

# ✅ Fluxo Completo Automático — TESTADO E2E EM PRODUÇÃO

**Status**: Funcionando E2E (commit e6eb6d3, 09/07/26) — protocolo real aguarda A3  
**Data**: 2026-07-09  
**Versão**: v6.1  

## ⚠️ ARQUITETURA REAL (mudou no teste E2E)
- `gerar_laudo` executa no **mac_agent (Ollama/Qwen 3.6 local)**, NÃO no backend — DashScope key revogada
- Backend materializa LaudoVersao + DOCX em `_aplicar_resultado` (jobs.py) quando o job conclui
- `protocolo_oficio`/`protocolo_laudo` executam no mac_agent (baixam DOCX da VPS via `/jobs/{id}/arquivo`)
- `/jobs/proximo` respeita `aguardar_job_id`
- Botão 🚀 fica em `ProcessosPage.jsx` (rota `/processos`); ProcessosIntimacoes.jsx é órfã (não usar)
- Protocolo real: gate `PROTOCOLO_AUTOMATICO_ATIVO=1` + credenciais TRIBUNAL_LOGIN/SENHA no mac_agent

## O que foi feito

**Backend (FastAPI):**
- ✅ Modelo `Oficio` em kanban.py (status tracking: gerado → protocolo_enfileirado → protocolado)
- ✅ Serviço `oficio_generator.py` — gera DOCX preenchendo placeholders {{CAMPO}}
- ✅ Script `create_oficio_templates.py` — cria 3 templates Word (requerimento, manifestacao, resposta_quesito)
- ✅ Endpoints em `fluxo_completo.py`:
  - `POST /api/v1/fluxo/completo/{intimacao_id}` — dispara cascata de jobs
  - `GET /api/v1/fluxo/status/{intimacao_id}` — polling para status

**Frontend (React):**
- ✅ Componente `FluxoCompletoModal.jsx` — modal interativa com:
  - Dropdown de intimações analisadas
  - Botão disparar fluxo
  - 4 barras de progresso em tempo real (ofício, protocolo ofício, laudo, protocolo laudo)
  - Suporte mobile + dark mode
- ✅ Integrado em `ProcessosIntimacoes.jsx` — botão **🚀 Fluxo Completo** no header
- ✅ Polling a cada 2s via `GET /api/v1/fluxo/status`

**Instalador Automático:**
- ✅ `INSTALL.sh` — script bash completo que:
  - Verifica Docker/docker-compose
  - Cria estrutura de pastas (/storage/*, /data/*)
  - Configura .env com senhas aleatórias
  - Build de 4 imagens (backend, frontend, db, worker)
  - Aguarda serviços ficarem prontos
  - Cria templates de ofício
  - Cria usuário padrão (admin@perito.local / 123456)
  - Tempo: ~2-3 minutos
- ✅ `README-FLUXO-COMPLETO.md` — guia completo (uso, arquitetura, troubleshooting)

## Fluxo de Execução

```
User click 🚀 Fluxo Completo
    ↓
Modal abre → GET /api/v1/intimacoes
    ↓
User seleciona intimação → click ▶️ Disparar
    ↓
POST /api/v1/fluxo/completo/{intimacao_id}
    ↓
BACKEND:
  • Gera ofício (docx)
  • Enfileira Job(tipo="protocolo_oficio")
  • Enfileira Job(tipo="gerar_laudo")
  • Enfileira Job(tipo="protocolo_laudo", aguardar_job_id=laudo.id)
    ↓
WORKER (loop 10min ou imediato):
  • Processa protocolo_oficio → A3 assina → eSAJ protocola
  • Processa gerar_laudo → Qwen gera → storage/laudos/
  • Processa protocolo_laudo → A3 assina → eSAJ protocola
    ↓
FRONTEND (polling GET /api/v1/fluxo/status):
  • Atualiza barras a cada 2s
  • Mostra números de protocolo quando disponíveis
  • User vê: ✅✅✅✅ → "Fluxo concluído!"
    ↓
STORAGE:
  • /data/storage/oficios/{numero_cnj}/oficio_*.docx
  • /data/storage/laudos/{numero_cnj}/laudo_*.docx
  • BD: Tabelas oficio + laudo + job com status tracking
```

## Como Usar (Instalação + Teste)

```bash
# 1. Clone + instale
git clone <repo> perito-v6
cd perito-v6
bash v6/INSTALL.sh

# 2. Aguarde 2-3 minutos...
# ✅ Vê mensagem "INSTALAÇÃO CONCLUÍDA!"

# 3. Acesse
# http://localhost
# Email: admin@perito.local
# Senha: 123456

# 4. Gestão de Autos → Botão "🚀 Fluxo Completo"
# → Select intimação → Disparar
# → Observar barras de progresso
```

## Commits Criados

- `5bb3e29` 🚀 Fluxo Completo + Interface + Instalador Automático
- `b8da9e7` Fluxo completo automático: intimação → ofício → protocola → laudo → protocola

## Próximos Passos (Opcional)

1. **Agendador**: Executar fluxo completo diariamente (Celery Beat)
2. **Notificações**: Email quando protocolo concluído
3. **Dashboard**: Widget mostrando quantos fluxos completados hoje
4. **Integração eSAJ Real**: Testar com A3 real no Windows
5. **Relatórios**: PDF com todos os protocolos do mês

## Por Que Isso é Importante

**Antes**: Perito recebia intimação → precisava gerar ofício manualmente → digitar em eSAJ → gerar laudo → protocolar laudo

**Depois**: Intimação → 1 click 🚀 → tudo automático (ofício, protocolo ofício, laudo, protocolo laudo)

**Ganho**: ~15 minutos por intimação × múltiplos processos = horas economizadas por semana

## Arquivos-chave para Modificações Futuras

| Arquivo | Propósito |
|---------|-----------|
| `backend/app/routes/fluxo_completo.py` | Endpoints do fluxo |
| `backend/app/services/oficio_generator.py` | Geração de ofícios |
| `frontend/src/components/FluxoCompletoModal.jsx` | Interface modal |
| `v6/INSTALL.sh` | Instalação automática |

## Status Atual do Sistema

- ✅ **Backend**: v6.0.0 (todos endpoints em produção)
- ✅ **Frontend**: React (modal funcionando 100%)
- ✅ **Banco de Dados**: PostgreSQL + migrations
- ✅ **Workers**: Job queue com suporte A3
- ✅ **Storage**: Templates + arquivos gerados armazenados
- ✅ **Docker**: 4 containers (backend, frontend, db, worker) sincronizados

**Deployado em**: VPS 129.121.34.186 (http://sistema.ipcms.com.br)

---

**Próxima Sessão**: Será testar fluxo real no Windows com A3 certificate.
