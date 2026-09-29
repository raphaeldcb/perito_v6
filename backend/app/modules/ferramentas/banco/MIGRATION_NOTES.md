# Banco Module — Migration Summary

**Date**: 2026-08-12  
**Task**: Move banking integrations to isolated module  
**Status**: ✅ Complete

## Migration Details

### Source Files (Consolidated)
- ✅ `v6/backend/app/routes/inter_banco.py` → Deprecated wrapper
- ✅ `v6/backend/app/routes/inter_api.py` → Deprecated wrapper
- ✅ `v6/backend/app/routes/tjms.py` → Deprecated wrapper

### Target Module
- ✅ `v6/backend/app/modules/ferramentas/banco/` — New isolated module

### Files Created/Modified

#### 1. **router.py** (16 KB)
Consolidated all endpoints from three original files:
- **Inter OAuth & Account Management** (1 endpoint)
  - `POST /api/v1/banco/inter/connect` — OAuth callback
  
- **Inter Balance & Statements** (2 endpoints)
  - `GET /api/v1/banco/inter/saldo` — Check balance
  - `POST /api/v1/banco/inter/extrato` — Query statement with auto-reconciliation
  
- **Inter Boletos** (1 endpoint)
  - `POST /api/v1/banco/inter/boleto/emitir` — Issue boleto (stub — not fully implemented)
  
- **Inter Webhooks** (1 endpoint)
  - `POST /api/v1/banco/inter/webhook` — Handle Inter account notifications (PIX, payments, boletos)
  
- **PIX Transfers** (4 endpoints)
  - `POST /api/v1/banco/pix/transfer` — Execute PIX transfer
  - `GET /api/v1/banco/balance` — Admin-only balance check
  - `POST /api/v1/banco/webhook/pagamento-confirmado` — Handle payment confirmations
  - `GET /api/v1/banco/transacoes` — List all transactions (admin-only)
  
- **TJMS Document Download** (1 endpoint)
  - `POST /api/v1/banco/tjms/download-autos` — Download court documents from TJMS

**Total: 10 endpoints**, all consolidated under `/api/v1/banco` prefix

#### 2. **schemas.py** (2.8 KB)
Consolidated all Pydantic request/response models:
- `InterConnectRequest` — OAuth connection
- `ExtratoBuscaRequest` — Statement search parameters
- `BoletoEmitirRequest` — Boleto issuance parameters
- `PixTransferRequest` — PIX transfer parameters
- `WebhookPagamentoConfirmado` — Payment confirmation webhook
- `DownloadRequest` — TJMS download parameters

#### 3. **__init__.py** (654 B)
Proper module exports:
- Router re-export
- Schema re-exports for type hints

#### 4. **service.py** (119 B)
Placeholder for module-specific services (future expansion)

### API Endpoint Changes

#### Old Endpoints (via deprecated wrappers)
```
/api/v1/inter/connect
/api/v1/inter/saldo
/api/v1/inter/extrato
/api/v1/inter/boleto/emitir
/api/v1/inter/webhook
/api/v1/inter/pix/transfer
/api/v1/inter/balance
/api/v1/inter/webhook/pagamento-confirmado
/api/v1/inter/transacoes
/api/v1/tjms/download-autos
```

#### New Endpoints (via consolidated module)
```
/api/v1/banco/inter/connect
/api/v1/banco/inter/saldo
/api/v1/banco/inter/extrato
/api/v1/banco/inter/boleto/emitir
/api/v1/banco/inter/webhook
/api/v1/banco/pix/transfer
/api/v1/banco/balance
/api/v1/banco/webhook/pagamento-confirmado
/api/v1/banco/transacoes
/api/v1/banco/tjms/download-autos
```

### Integration Strategy

**Backwards Compatibility**: The original route files now act as wrappers, re-exporting the router from the consolidated module. This ensures:

1. **No breaking changes to route discovery** — The routes/__init__.py loader still loads all three original files
2. **Clean module architecture** — All logic lives in the modular structure
3. **Zero code duplication** — Single source of truth for all endpoints
4. **Easy migration path** — Clients can gradually update to new `/api/v1/banco/*` endpoints

### Dependencies

**Imports Required**:
- `app.services.inter_api` — OAuth, balance, statement services
- `app.services.inter_api_client` — PIX transfer client
- `app.services.inter_reconciliation` — Statement reconciliation
- `app.services.tjms_downloader` — TJMS document download
- `app.models.inter` — Database models for Inter accounts/transactions/webhooks
- `app.models.inter_transacao` — Database models for transactions

All dependencies are stable and have no circular references.

### Known Issues & TODOs

1. **`emitir_boleto` function not implemented** (line 190)
   - The endpoint `POST /api/v1/banco/inter/boleto/emitir` currently returns 501 Not Implemented
   - Service function `emitir_boleto()` needs to be created in `app.services.inter_api`

2. **Webhook validation incomplete** (lines 310-312, 370-371)
   - HMAC signature validation not implemented
   - IP origin validation not implemented
   - TODO markers left in code for future implementation

### Testing Checklist

- [x] Syntax validation (Python 3.9+)
- [x] Module imports work correctly
- [x] Router consolidation (10 endpoints)
- [x] Schema consolidation (6 schemas)
- [x] Wrapper files re-export correctly
- [x] No circular dependencies
- [ ] Endpoint integration tests (requires full environment)
- [ ] Webhook signature validation (blocked by TODO)

### Migration Complete

This module can now be independently:
- **Tested** (unit tests for each endpoint)
- **Documented** (OpenAPI auto-generated from router)
- **Scaled** (add new banking integrations without touching main.py)
- **Maintained** (schemas + router only exports)

---

**Next Steps** (if needed):
1. Implement missing `emitir_boleto()` service function
2. Add webhook HMAC validation
3. Add IP allowlist for webhook security
4. Create integration tests for banking flows
5. Migrate clients from `/api/v1/inter/*` to `/api/v1/banco/*`
