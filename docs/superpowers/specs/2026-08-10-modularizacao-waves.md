# Modularização PERITO V6 — Waves Paralelas Seguras

**Data:** 10 de agosto de 2026  
**Objetivo:** Eliminar acoplamento excessivo ("cobertor curto") através de isolamento modular, dados reais desde o início, validação contínua.  
**Estratégia:** 3 waves (0 sequencial, 1 paralelo, 2 sequencial crítico) = 4-5 semanas total.

---

## 1. Problema & Contexto

**Estado Atual:**
- 31 páginas frontend, 112 endpoints backend, 80+ serviços em single FastAPI process
- 6915 processos reais em produção (Projuris 2182 + ProjetoCP 4733)
- 14 workers, 25 integrações externas (ESAJ, Inter, Google, BCB, PTAX, FIPE)
- **Sintoma:** "Peço pra arrumar ferramenta X, quebra ESAJ" → acoplamento circular

**Objetivo de Sucesso:**
- Modificar um módulo (ex: Ferramentas) sem quebrar outros
- Staging roda com dados reais (estrutura idêntica a prod, anonimizado)
- Cada module independente (imports unidirecionais, DTOs compartilhados, event-driven)
- Primeiro teste: "Arruma uma coisa, sistema não cai"

---

## 2. Estratégia de Waves

### Wave 0: Base & Dados Reais (1 semana, Sequencial)

**Objetivo:** Setup completo pra work paralelo.

**Tasks:**
1. **Audit Dados Reais** — Exporta 6915 processos, mapeia dependências (código + BD)
2. **Estrutura Modular Backend** — Cria pastas modularizadas (`modules/auth`, `modules/processos`, etc)
3. **Staging Docker + Data Clone** — Anonimiza dados reais, setup DB staging, CI/CD pipeline
4. **CI/CD Gates** — Auto-deploy develop → staging, testes rodam em staging, health checks

**Dados Reais:**
- `scripts/export_production.py` — Extrai 6915 processos + intimações do VPS (perito_prod)
- `scripts/anonymize_data.py` — Faker para CPF/nomes, reduz valores 10-50%, respeita dates
- Staging DB (`perito_staging`, port 5433) roda com dados anônimos
- Cada task subsequente testa contra staging (volume real, relacionamentos reais)

**Deliverables:**
- ✅ Staging BD estável, 6915 processos presentes (anonimizados)
- ✅ Dependency map: quais módulos importam quais (audit_imports.py output)
- ✅ CI/CD rodando: develop → staging auto-deploy, testes passam
- ✅ Estrutura modular criada, zero acoplamento entre `app/modules/*`

**Gate Wave 0 → Wave 1:**
```
✅ Staging health: GET /health retorna 200 OK
✅ Audit: Zero circular imports detectadas
✅ Dados: 6915 processos no staging, anonymization validada
✅ CI/CD: develop branch push → staging deploy → tests pass
```

---

### Wave 1: Modularização Backend (2 semanas, 4 Times Paralelos)

**Objetivo:** Refatorar backend pra 8 módulos isolados, testes com dados reais.

**Times Paralelos:**

| Time | Módulos | Deps | Risk |
|------|---------|------|------|
| **A** | Ferramentas, Processos | None, Ferramentas | Low |
| **B** | Financeiro, IA | Processos, Ferramentas | Medium |
| **C** | Laudos | Processos, Financeiro, IA, ESAJ | Medium-High |
| **D** | Auth, Infra, Shared DTOs | None (core) | Low |

**Cada Time:**
- Extrai módulo da monolito atual
- Cria `models/`, `schemas/`, `repositories/`, `services/`, `routes/`
- Escreve testes com dados reais (staging DB, 6915 processos)
- Valida contrato: shared DTOs (`app/shared/schemas.py`)
- Merge em feature branch, CI validado em staging

**Módulos & Endpoints:**

| Módulo | Endpoints | Descrição |
|--------|-----------|-----------|
| **auth** | BE-01 a BE-13 | Login, tokens, RBAC, 2FA |
| **processos** | BE-14 a BE-30 | CRUD processos, intimações, kanban |
| **esaj** | BE-49 a BE-60 | Login tribunal, sync, protocolo |
| **laudos** | BE-34 a BE-40 | CRUD laudos, download, geração IA |
| **financeiro** | BE-41 a BE-48 | Boletos, notas, conciliação Inter |
| **ferramentas** | BE-61 a BE-82 | Calculadora, CNJ lookup, prazos |
| **ia** | BE-105 a BE-107 | Análise Qwen, fake detector, RAG |
| **infra** | BE-85 a BE-112 | Health checks, logs, auditoria, parametros |

**Data Strategy:**
- Cada módulo testa com subset real (ex: Financeiro testa boletos dos 6915 casos)
- Staging BD é source of truth, não fake data
- Migrations (Alembic) aplicadas em staging antes de qualquer code

**Deliverables:**
- ✅ 8 módulos refatorados, zero cross-module imports (audit_imports.py valida)
- ✅ 70%+ code coverage por módulo (pytest)
- ✅ E2E tests passam em staging (com 6915 dados reais)
- ✅ OpenAPI docs auto-geradas, todos 112 endpoints documentados
- ✅ DTOs compartilhados versionados em `shared/schemas.py`

**Gate Wave 1 → Wave 2:**
```
✅ Audit: Zero circular dependencies
✅ Coverage: 70%+ por módulo (pytest --cov)
✅ E2E: Staging tests passam com dados reais
✅ Docs: OpenAPI /docs atualizado com 112 endpoints
✅ Contracts: DTO schemas validados pra cross-module communication
```

---

### Wave 2: Resiliência & Integração (2 semanas, Sequencial)

**Objetivo:** Conectar módulos sem acoplamento, proteger integrações externas.

**Tasks Sequenciais (críticas):**

1. **ESAJ Module Finalização** (3 dias)
   - Integra com tribunal real (sandbox antes de prod)
   - Login 2FA, sincronização processos, protocolo automático
   - Circuit breaker pra falhas de tribunal (INT-01)
   - Gate: ESAJ testa com tribunal sem quebrar outros módulos

2. **Event Bus (Redis Pub/Sub)** (3 dias)
   - SVC-59: Barramento de eventos (ProcessoAtualizado, LaudoGerado, etc)
   - SVC-60: Idempotency manager (evita duplicate eventos)
   - Módulos publishem eventos, outros consomem sem import direto
   - Gate: Evento Processo criado → Financeiro recebe notificação

3. **Circuit Breakers & Fallbacks** (4 dias)
   - 25 integrações externas (ESAJ, Inter, Google Maps, BCB, PTAX, FIPE, etc)
   - Fallback strategy (ex: Google Maps down → Vialog, Ollama 100% VRAM → Fable)
   - SVC-01 rate limiting, SVC-56 mTLS certificates
   - Gate: Simula tribunal down, sistema degrada gracefully

4. **Monitoring & Logs** (2 dias)
   - SVC-58: Correlation ID cross-modules, logs estruturados
   - SVC-67: Frontend RUM (Core Web Vitals, JS errors)
   - BE-112: Health check granular (DB, Redis, Ollama, externa APIs)
   - Dashboard FE-28: Status de cada módulo em tempo real
   - Gate: Dashboard mostra saúde de cada módulo, alertas funcionam

**Deliverables:**
- ✅ ESAJ module integrado, testa com tribunal sandbox
- ✅ Events fluem (Processo criado → Financeiro criado boleto automaticamente)
- ✅ Circuit breakers testados (simula falhas externas, sistema continua)
- ✅ Health check /health retorna status de 25 integrações
- ✅ Logs estruturados com correlation IDs, rastreamento end-to-end

**Gate Wave 2 → Launch:**
```
✅ ESAJ: Login 2FA, sync, protocolo funcionam em sandbox
✅ Events: Pub/Sub publica/consome sem imports circulares
✅ Circuit Breaker: Tribunal down → sistema degrada, não cai
✅ Health: /health retorna status granular, alertas funcionam
✅ Logs: Correlation ID rastreia request de frontend → backend → workers
```

---

## 3. Estrutura de Diretórios Final

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py (settings, environment)
│   │   ├── security.py (JWT, RBAC)
│   │   └── database.py (SQLAlchemy, session)
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   └── routes.py
│   │   ├── processos/
│   │   ├── esaj/
│   │   ├── laudos/
│   │   ├── financeiro/
│   │   ├── ferramentas/
│   │   ├── ia/
│   │   └── infra/
│   ├── shared/
│   │   ├── schemas.py (DTO global, ApiResponse, etc)
│   │   ├── exceptions.py
│   │   ├── repositories.py (base class)
│   │   └── utils.py
│   ├── events/
│   │   ├── bus.py (Redis Pub/Sub)
│   │   └── schemas.py (event DTOs)
│   └── main.py (FastAPI app, register routers)
├── alembic/
│   ├── versions/ (migrations)
│   └── env.py
├── scripts/
│   ├── export_production.py
│   ├── anonymize_data.py
│   └── deploy_safe.sh
├── tests/
│   ├── modules/
│   │   ├── auth/
│   │   ├── processos/
│   │   └── ...
│   ├── integration/
│   └── e2e/
├── docker-compose.staging.yml
├── Dockerfile
└── requirements.txt (pinned versions)

frontend/
├── src/
│   ├── core/
│   │   ├── api.ts (API client com interceptors)
│   │   ├── auth.tsx (Auth context)
│   │   └── theme.ts (design system já existente, mantém)
│   ├── features/
│   │   ├── auth/ (login, perfil)
│   │   ├── processos/ (CRUD, kanban)
│   │   ├── laudos/ (geração, download)
│   │   ├── financeiro/ (boletos, notas)
│   │   └── ...
│   └── App.tsx (router central)
└── package.json
```

---

## 4. Regras de Dependência (Unidirecionais)

**Permitido:**
- Módulo → `shared/schemas.py` (DTOs globais)
- Módulo → `core/` (config, security, DB)
- Módulo → Event Bus (publish/subscribe)
- Módulo → Circuit Breaker wrapper pra externas APIs

**Proibido:**
- Módulo X → Módulo Y imports diretos (ex: `from app.modules.esaj.services import esaj_service`)
- Módulo → compartilhar models (use DTO do shared)
- Módulo → queries em BD de outro módulo (via repository isolado)

**Validação:** Script `audit_imports.py` roda em CI, bloqueia PR se viola.

---

## 5. Dados Reais & Anonymization

**Estratégia:**
- Production BD: `perito_prod` (129.121.34.186:5432, user=perito)
- Export: `scripts/export_production.py` extrai DDL + dados
- Anonymize: `scripts/anonymize_data.py` Faker + aleatório
- Staging BD: `perito_staging` (localhost:5433)

**Anonymization Rules:**
- CPF: Faker.cpf() (gera CPF válido fake)
- Nomes partes: Faker.name()
- Valores: Reduz 10-50% aleatório (mantém range realista)
- Datas: Mesmos offsets (ex: ofício em T, sentença em T+60)
- Senhas: Hash bcrypt (impossível reverter)

**LGPD Compliance:**
- Anonymization irreversível (Faker, não mapping table)
- Staging DB é "descartável", não contém dados reais sensíveis
- Logging: correlation IDs, sem PII em logs

---

## 6. CI/CD Pipeline

**Trigger: Push to develop**
```
1. Lint & Type Check (pylint, pyright)
2. Run tests (pytest, staging DB)
3. Coverage report (must be 70%+)
4. Build Docker image
5. Deploy to staging (docker-compose up)
6. Run E2E tests (Playwright) contra staging
7. Health checks (all 25 integrations)
8. If all pass → ready for main branch PR
```

**Trigger: PR to main**
```
1. Same as develop + code review
2. Manual approval (change management)
3. Deploy to production (docker-compose up -p prod)
4. Smoke tests (login, GET /processos, etc)
```

---

## 7. Gates & Rollback

**Wave 0 Gate:**
- Staging BD: 6915 processos presentes, anonymization OK
- Audit: Zero circular imports (audit_imports.py)
- CI/CD: develop → staging pipeline roda 100%

**Wave 1 Gate:**
- Coverage: 70%+ per module (pytest --cov)
- E2E: Staging tests passam (Playwright)
- Audit: Zero cross-module imports (CI blocks)
- OpenAPI: 112 endpoints documentados

**Wave 2 Gate:**
- ESAJ: Sandbox login, sync, protocolo OK
- Events: Pub/Sub publica/consome, idempotency OK
- Circuit Breaker: Simula falha tribunal, fallback funciona
- Health: /health granular, alertas disparam

**Rollback Strategy:**
- Wave 0 fail → voltar ao código anterior (git revert)
- Wave 1 fail → rollback database migration (alembic downgrade), keep git commits
- Wave 2 fail → circuit breaker killswitch desativa feature flag, rollback gradual

---

## 8. Métricas de Sucesso

**Técnicas:**
- ✅ Zero circular imports (audit_imports.py)
- ✅ 70%+ code coverage (pytest)
- ✅ 100% 112 endpoints documentados (OpenAPI)
- ✅ E2E tests passam com dados reais

**Operacionais:**
- ✅ Staging health check passa (25 integrações)
- ✅ Deploy staging < 5 minutos
- ✅ Rollback < 2 minutos

**Negócio:**
- ✅ "Arruma ferramenta X, não quebra ESAJ" (primeiro teste)
- ✅ Desenvolvimento paralelo (4 times não bloqueiam uns aos outros)
- ✅ LGPD: Dados sensíveis anônimos em staging

---

## 9. Timeline

| Semana | Wave | Focus | Teams |
|--------|------|-------|-------|
| 1 | 0 | Audit, estrutura, staging, CI/CD | 1 (você) |
| 2-3 | 1 | 8 módulos paralelo, testes, DTOs | 4 times |
| 4-5 | 2 | ESAJ, events, circuit breakers, monitoring | 2-3 |

**Total: 4-5 semanas, paralelo onde possível, sequencial onde crítico.**

---

## 10. Dependências Externas

- PostgreSQL 16 (prod + staging)
- Redis 7.x (event bus, cache)
- Docker & Docker Compose
- Ollama (Qwen local)
- pytest, Playwright (testing)
- Alembic (migrations)

---

## 11. Artefatos Finais

**Código:**
- ✅ `backend/app/modules/*` — 8 módulos isolados
- ✅ `backend/app/shared/*` — DTOs globais, exceptions
- ✅ `backend/app/events/*` — Event bus (Redis Pub/Sub)
- ✅ `scripts/export_production.py`, `anonymize_data.py`
- ✅ `docker-compose.staging.yml`, `docker-compose.prod.yml`
- ✅ `.github/workflows/deploy-staging.yml`, `deploy-prod.yml`

**Testes:**
- ✅ `tests/modules/*` — 70%+ coverage per module
- ✅ `tests/integration/` — E2E cross-module
- ✅ `tests/e2e/` — Playwright contre staging

**Docs:**
- ✅ `/docs/architecture/CURRENT_DEPENDENCY_MAP.md` (audit baseline)
- ✅ `/docs/architecture/MODULAR_DESIGN.md` (referência)
- ✅ OpenAPI /docs com 112 endpoints (auto-gerada)
- ✅ Event schemas documentation

---

## 12. Riscos & Mitigação

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Dados reais vazam em staging | CRÍTICO | Anonymization irreversível, VPN-only access |
| Circular deps não são pegos | ALTO | audit_imports.py em CI, bloqueia PR |
| ESAJ integração quebra | CRÍTICO | Sandbox primeiro, circuit breaker, fallback |
| Migrations falham em prod | CRÍTICO | Teste em staging antes, alembic downgrade pronto |
| Conflitos de merge paralelo | MÉDIO | Feature branches, CR rigoroso, gates entre waves |

---

## 13. Aprovações Necessárias

- ✅ Tech lead: Arquitetura modular OK
- ✅ DevOps: CI/CD pipeline OK
- ✅ Product: Timeline (4-5 semanas) OK
- ✅ User (Bruno): Dados reais, sem encenação, vai começar

---

**Spec Completa. Pronto pra escrever o plano de implementação detalhado (Tasks 1-16).**
