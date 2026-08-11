---
name: forensic_apis_status_070826
description: "Análise Forense Profissional — Status 07/08/2026 (Sistema pronto estruturalmente, APIs não funcionam)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7c467360-9d68-48a8-88e5-e9d96cc8cf87
  modified: 2026-08-07T12:23:16.248Z
---

# 🔍 Análise Forense Profissional — Status Final (07/08/2026)

**RESUMO**: Backend + frontend 100% pronto. APIs externas falhando na autenticação (chaves inválidas, endpoints offline, ou desabilitadas no console do provedor).

## ✅ SISTEMA PRONTO (ESTRUTURAL)

**Backend Docker**  
- Container `perito-v6-backend` UP, health=ok
- Endpoint `POST /api/v1/forensic/analyze` respondendo 200
- Database schema com `analise_forense_resultado` criada
- Settings.py aceita 4 chaves de API

**Arquitetura 3-Camadas Implementada**  
- Camada 1: 18 filtros locais (EXIF, FFT, GenAI fingerprint, etc)
- Camada 2: 6 APIs (Deepware, Reality Defender, Sensity, Azure, Google, IBM)
- Camada 3: Síntese (Gemini/Claude)
- Votação: 20 especialistas, consenso >= 15

**Frontend**  
- Modal upload drag-drop em Ferramentas
- Resultado com veredicto + confiança + consenso stats

## ❌ APIs FALHANDO (NÃO FUNCIONAIS)

| API | Chave | Erro | Causa | Fix |
|-----|-------|------|-------|-----|
| **Google Vision** | `AIzaSyB177VTubD_liUSY86T1E9mzHhHRcOoyt8` | 403 PERMISSION_DENIED | API não habilitada no GCP 338909438706 | Habilitar no console GCP |
| **Reality Defender** | `rd_e709d24ab3e3010b_5e4925bed6623e80b7ff75101dea9e58` | HOSTNAME NOT RESOLVED | Domínio inválido ou DNS bloqueado | Validar endpoint correto |
| **IBM Watson** | `DbIVfe5nZEQ16gBsGIgNH_Gzeao3LrB9VgXMQuKPGdP5` | Não testado | Campo adicionado mas sem teste | Testar com curl |
| **Deepware, Sensity, Azure** | Vários | Não testadas | Falta teste unitário | Implementar teste por API |

## 🚨 RESULTADO ATUAL (FALSO POSITIVO)

```
Upload REAL (branco)   → AUTÊNTICO 86.66% ✓ (correto por acaso)
Upload FAKE (uniforme) → AUTÊNTICO 86.66% ✗ (deveria ser FAKE)
```

**Causa**: Fallback local mascarando falhas de API — sistema retorna consenso alto para TUDO.

**Status**: Nenhuma fake detection real acontecendo.

## 🎯 O QUE BRUNO PRECISA FAZER

1. Validar as 4 chaves:
   - Google: Habilitar Vision API no GCP project 338909438706
   - Reality Defender: Confirmar domínio correto (não é `api.realitydefender.com`?)
   - IBM Watson: Verificar formato da chave + endpoint
   - Outras: Habilitar/validar nas contas

2. Retest com imagem comprovadamente fake (deepfake ou AI-gerada)

## 📝 COMANDOS DE TESTE

```bash
# Upload real
curl -X POST http://127.0.0.1:8000/api/v1/forensic/analyze -F "file=@real.jpg"

# Upload fake
curl -X POST http://127.0.0.1:8000/api/v1/forensic/analyze -F "file=@fake.jpg"
```

**Esperado quando APIs funcionarem**:  
Real → AUTÊNTICO ~90%+  
Fake → FAKE ~60%+ ou INCONCLUSIVO
