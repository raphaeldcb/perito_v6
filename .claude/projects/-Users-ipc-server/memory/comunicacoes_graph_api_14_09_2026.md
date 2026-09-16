---
name: comunicacoes-graph-api-14-09-2026
description: Serviço Microsoft Graph para Comunicações Judiciais implementado — 560 linhas código, rotas + schemas + worker
metadata:
  type: project
---

# Implementação: Comunicações Judiciais via Microsoft Graph

**Data**: 14/09/2026  
**Status**: ✅ **CÓDIGO COMPLETO — Aguardando testes VPS**

## 🎯 Objetivo

Migrar módulo Comunicações Judiciais de **Gmail SMTP** para **Microsoft Graph API** (email-as-a-service), classificar automaticamente como judicial ou não, extrair dados processuais (Vara, Comarca, Número Processo), e armazenar para acompanhamento via UI.

**Escopo**: Zero impacto em Intimacao, Processos, ou qualquer outro módulo. Isolamento total.

---

## 📦 Arquivos Criados (4 arquivos, ~560 linhas)

### 1. `app/services/comunicacoes_service.py` (~230 linhas)

**Classe**: `ComunicacoesJudiciaisService`

**Métodos**:
- `obter_config()` — Gerencia configuração de monitoramento
- `buscar_emails_nao_processados()` — Reutiliza `graph_mail.listar_nao_lidos()`
- `_classificar_judicial()` — IA local: regex CNJ + palavras-chave → confiança 0-1
- `_extrair_dados_processuais()` — Regex para Vara, Comarca, Tribunal
- `processar_mensagem()` — Armazena email com idempotência via external_id
- `registrar_log()` — Audit trail

### 2. `app/workers/monitor_comunicacoes.py` (~160 linhas)

**Função**: `processar_caixa_entrada(conta_email, limite)`

**Responsabilidades**:
- Verifica configuração Graph
- Busca emails em lote (limite=50 default)
- Processa cada email (classifica + extrai)
- Marca como lido (best-effort)
- Retorna dict com stats: `{emails_processados, judiciais, ignorados, erros}`

**Isolamento**: Código separado de `monitor_emails.py` (que serve Intimacao)

### 3. `app/workers/comunicacoes_monitor.py` (~20 linhas)

**Classe**: `ComunicacoesMonitorWorker`

Wrapper para integração com rotas FastAPI existentes em `routes/comunicacoes_judiciais.py`

### 4. `app/schemas/comunicacoes.py` (~150 linhas)

**Modelos Pydantic** (entrada/saída API):
- `ComunicacaoConfigSchema`
- `ComunicacaoMensagemListSchema`, `DetailSchema`
- `ComunicacaoDadosProcessuaisSchema`
- `ComunicacaoLogSchema`
- `ExecutarMonitoramentoRequest/Response`
- `PainelStatisticsSchema`

---

## 🔗 Reutilização (Zero Refactoring)

| Componente | Tipo | Status |
|-----------|------|--------|
| `graph_mail.py` | Service | ✅ Reutilizado (já existente, 100% funcional) |
| Modelos `comunicacoes_*` | ORM | ✅ Já existem em `models/comunicacoes.py` |
| Rotas `/api/v1/comunicacoes/*` | FastAPI | ✅ Registradas em `routes/__init__.py` |
| Frontend `ComunicacoesJudiciais.jsx` | React | ✅ Aguarda backend (pronto para conectar) |

**Impacto**: Nenhum em `Intimacao`, `Processos`, `Kanban`, `Ferramentas`, etc.

---

## 🧪 Classificação Judicial (Heurística Local)

| Cenário | Confiança | Critério |
|---------|-----------|----------|
| Contém CNJ válido | 95% | `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}` |
| 2+ palavras-chave | 50-90% | `intimação, despacho, sentença, vara, tribunal, ...` |
| 1 palavra-chave | 60% | idem |
| Nenhum sinal | 0% | Classificado como não-judicial |

**Palavras-chave**: 20 termos judiciais (intimação, despacho, sentença, acórdão, apelação, recurso, processo, tribunal, vara, judicial, justiça, juiz, tabelião, cartório, petição, mandado, citação, notificação, ofício, inquérito)

---

## 📊 Extração de Dados Processuais (Regex)

- **Número de Processo**: CNJ formatado `0001234-56.2026.8.26.0100`
- **Vara**: Padrão `\d+[ªª]?\s+Vara(?:s)?[^,\n]*`
- **Comarca**: Padrão `Comarca de\s+([^,\n]+)`
- **Tribunal**: TJMS, TJ-MS ou nome por extenso

---

## 🔐 Segurança

| Aspecto | Status | Detalhe |
|--------|--------|---------|
| Credenciais | ✅ OK | 100% environment vars (`graph_mail.py` gerencia) |
| Autenticação | ✅ OK | Bearer token via FastAPI middleware |
| Idempotência | ✅ OK | `external_id` (internetMessageId) previne duplicação |
| Audit Logs | ✅ OK | Toda execução em `ComunicacaoLog` |
| LGPD | ⚠️ Parcial | Corpo armazenado (necessário IA), sem share externo |

**Pendente**: Criptografia corpo em repouso (Phase 2)

---

## 📋 Endpoints da API

```
GET  /api/v1/comunicacoes/config
PUT  /api/v1/comunicacoes/config
POST /api/v1/comunicacoes/executar         ← Force monitor execution
GET  /api/v1/comunicacoes/mensagens
GET  /api/v1/comunicacoes/mensagens/{id}
GET  /api/v1/comunicacoes/logs
GET  /api/v1/comunicacoes/painel
```

---

## ✅ Checklist de Implementação

- ✅ Código escrito (560 linhas)
- ✅ Sintaxe Python validada
- ✅ Importações verificadas
- ✅ Git commit realizado
- ✅ GitHub push realizado
- ✅ Deploy VPS (arquivos copiados com sucesso)
- ⏳ Testes E2E (container health pending)

---

## 🚀 Próximas Etapas

### Fase 1: Validação VPS (IMEDIATO)
1. Resolver health check do container PostgreSQL
2. GET `/api/v1/comunicacoes/config` = 200 OK
3. POST `/api/v1/comunicacoes/executar` processa ≥1 email
4. Validar classificação judicial
5. E2E: Frontend conecta ao backend

### Fase 2: Melhorias (Após Fase 1)
- [ ] Criptografia de corpos em repouso
- [ ] Retenção automática (30 dias?)
- [ ] Alertas para emails importantes
- [ ] Template resposta automática

### Fase 3: Automação (Futura)
- [ ] Scheduler: a cada 5-10 min
- [ ] Webhooks: notificar judicial encontrado
- [ ] Integração Qwen: análise semântica

---

## 🎯 Critério de Sucesso

✅ **Sistema pronto quando**:
1. Endpoints retornam 200 OK
2. ≥1 email processado com sucesso
3. Classificação judicial ≥80% acurácia
4. Dados processuais extraídos corretamente
5. Frontend conecta sem erro

---

**Commit**: `2fcc930` (main branch)  
**Repositório**: GitHub private (32MB código clean)
