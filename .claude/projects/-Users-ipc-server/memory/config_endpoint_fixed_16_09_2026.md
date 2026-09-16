---
name: config-endpoint-fixed
description: Email monitoring config endpoint — operational after JSON deserialization fix
metadata: 
  node_type: memory
  type: project
  originSessionId: 6ab256e2-a382-4fe9-81d5-9688285c3d78
  modified: 2026-09-16T19:29:14.803Z
---

# Email Monitoring Config — Fix Complete 2026-09-16

## ✅ Status: OPERATIONAL — Ready for Activation

Config endpoint (`POST /api/v1/comunicacoes/config/`) now fully functional after JSON deserialization fix.

## Issue & Root Cause

**Problem**: `campos_obrigatorios` field causing Pydantic validation error
```
ValidationError: Input should be a valid dictionary [type=dict_type, input_value='{"tribunal": true...}', input_type=str]
```

**Root Cause**: Field stored as JSON string in PostgreSQL but schema expects `dict`
- Column defined as `Text` in database
- When retrieving and validating with `EmailConfigSchema.model_validate()`, Pydantic rejects string
- Affects both `salvar_config()` and `obter_config()` methods

## Solution Applied

Explicit JSON deserialization before Pydantic validation:

```python
# In obter_config() and salvar_config():
if config.campos_obrigatorios and isinstance(config.campos_obrigatorios, str):
    config.campos_obrigatorios = json.loads(config.campos_obrigatorios)

return EmailConfigSchema.model_validate(config)
```

## Testing Results

✅ **POST /api/v1/comunicacoes/config/**
```json
{
  "mailbox_email": "ipcms@ipcms.com.br",
  "intervalo_minutos": 5,
  "ativo": true,
  "modo_resposta": "rascunho",
  "campos_obrigatorios": {
    "tribunal": true,
    "vara": true,
    "numero_processo": true,
    "pedido": true
  }
}
```

✅ **GET /api/v1/comunicacoes/config/**
- Returns saved config with all fields intact
- `ativo: true` persisted correctly

## Painel Status

✅ `/painel/statistics` operational:
- recebidos_hoje: 17
- judiciais: 3
- completos: 0
- pendentes: 0

## Commit

```
674a164 fix: deserializar campos_obrigatorios antes de validar config
```

## Next Steps

1. ✅ Config endpoint working (done)
2. **PENDING**: Activate monitoring via UI or API
   - User can now click "Ativar Monitoramento" in Config panel
   - `POST /config/` will persist `ativo: true`
   - Monitor worker (`monitor_comunicacoes.py`) will start polling Graph API
3. Monitor incoming emails from Outlook
4. Classify as judicial, extract data, trigger responses

## Timeline

- 2026-09-16 18:42: Removed problematic `config.updated_at = ...` line
- 2026-09-16 19:30: Fixed JSON deserialization, endpoint now operational
- 2026-09-16: **Ready for user activation**

User stated: "Quero ele ativo a partir de agora" → all technical blockers removed ✅
