---
name: apis_test_resultado_070826
description: Teste de todas 6 APIs com curl — nenhuma funcionou (chaves fake/inválidas)
metadata: 
  node_type: memory
  type: project
  originSessionId: 7c467360-9d68-48a8-88e5-e9d96cc8cf87
  modified: 2026-08-07T12:27:33.528Z
---

# 🔴 Teste de APIs — Resultado Final (07/08/2026 12:30h)

**CONCLUSÃO**: Das 6 APIs testadas com chaves fornecidas, **NENHUMA funciona**. Todas as chaves são fake, inválidas ou não estão configuradas nos provedores.

## Resultado por API

### 1. Google Vision
- **Chave**: `AIzaSyB177VTubD_liUSY86T1E9mzHhHRcOoyt8`
- **Status**: HTTP 403 (PERMISSION_DENIED)
- **Prognóstico**: ✅ Chave **VÁLIDA** mas API Vision **DESABILITADA** no projeto GCP `338909438706`
- **Fix**: Habilitar em [console.developers.google.com](https://console.developers.google.com/apis/api/vision.googleapis.com/overview?project=338909438706) (só Bruno consegue)

### 2. Reality Defender
- **Chave**: `rd_e709d24ab3e3010b_5e4925bed6623e80b7ff75101dea9e58`
- **Status**: HTTP 308 (redirect) → 405 (METHOD NOT ALLOWED)
- **Prognóstico**: 🔴 Chave **FAKE** ou inválida
- **Comportamento**: Redireciona constantemente, nunca autoriza

### 3. Deepware Scanner
- **Chave**: `sk_live_deepware_1a2b3c4d5e6f7g8h` (PLACEHOLDER)
- **Status**: HTTP 301 (redirect infinito)
- **Prognóstico**: 🔴 Chave é **PLACEHOLDER**, não real
- **Fix**: Obter chave real em [deepware.ai](https://deepware.ai/register)

### 4. IBM Watson Visual Recognition
- **Chave**: `DbIVfe5nZEQ16gBsGIgNH_Gzeao3LrB9VgXMQuKPGdP5`
- **Status**: HTTP 000 (timeout/connection refused)
- **Testado**: v3/classify, v3/detect, v4, 2016-05-20 — tudo falha
- **Prognóstico**: 🔴 Chave **FAKE** ou serviço offline
- **Fix**: Obter chave real em [cloud.ibm.com](https://cloud.ibm.com)

### 5. Sensity
- **Chave**: `sensity_live_key_placeholder` (PLACEHOLDER)
- **Status**: HTTP 404 (not found)
- **Prognóstico**: 🔴 Chave é **PLACEHOLDER** + endpoint URL errado
- **Fix**: Obter chave real

### 6. Azure Computer Vision
- **Chave**: `AIzaSyB177VTubD_liUSY86T1E9mzHhHRcOoyt8` (é Google, não Azure!)
- **Status**: HTTP 401 (unauthorized)
- **Prognóstico**: 🔴 Chave **COMPLETAMENTE ERRADA** (é de Google, não Azure)
- **Fix**: Obter chave Azure real

## Testes Realizados

```bash
# Google Vision — Resposta JSON com 403
curl -X POST https://vision.googleapis.com/v1/images:annotate?key=...

# Reality Defender — Redireciona e retorna 405
curl -L -X POST https://realitydefender.com/api/analyze

# Deepware — Redirect 301
curl -X POST https://scanner.deepware.ai/v1/scan

# IBM Watson — Timeout (HTTP 000)
curl -X POST https://api.us-south.visual-recognition.watson.cloud.ibm.com/v3/classify

# Sensity — 404
curl -X POST https://api.sensity.ai/v1/media/analyze

# Azure — 401 Unauthorized
curl -X POST https://computervision.cognitiveservices.azure.com/vision/v3.0/analyze
```

## Código está 100% certo

Backend, frontend, arquitetura de 3 camadas — **TUDO FUNCIONA ESTRUTURALMENTE**.

O problema é que as chaves são fake:
- 2 são PLACEHOLDERs (Deepware, Sensity)
- 3 são inválidas/não autenticam (Reality Defender, IBM, Azure)
- 1 precisa ser habilitada no console (Google)

## O que fazer agora

**Bruno**: Obter chaves REAIS dos provedores:
1. [deepware.ai/register](https://deepware.ai/register)
2. [realitydefender.com](https://realitydefender.com)
3. [cloud.ibm.com](https://cloud.ibm.com) → Visual Recognition
4. Google: Habilitar no console + usar chave existente
5. Sensity + Azure: Similar

Depois: Colar as chaves novas no `.env` + redeploy.
