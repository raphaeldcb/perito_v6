---
name: autolaudopro_e2e_producao_13_08
description: AutoLaudoPro E2E 100% acurácia validado em produção (VPS) com teste real
metadata: 
  node_type: memory
  type: project
  originSessionId: facbf296-2947-41f3-bc96-201ea9ae2b4d
  modified: 2026-08-13T12:12:35.951Z
---

# AutoLaudoPro — E2E 100% Acurácia Validado em Produção

**Data**: 13/08/2026  
**Status**: 🟢 OPERACIONAL EM PRODUÇÃO  
**Acurácia**: 100.0% (9/9 campos críticos)  
**Endpoint**: `/api/v1/ferramentas/auto-laudo/extrair`

## Resultado Teste Real

```
POST /api/v1/ferramentas/auto-laudo/extrair
Status: HTTP 200
Tempo: 48.6s (Qwen 3.6 local via SSH tunnel)
Campos validados: 9/9 ✅
  ✅ Numero_Laudo: 1408.26.30.jd.47
  ✅ Autos: 0000***REMOVED***9
  ✅ Requerente: João da Silva
  ✅ Requerido: Empresa Industrial LTDA
  ✅ Objeto: Perícia de insalubridade — exposição a...
  ✅ Nomeacao_Data: Vinte e três de julho de 2025
  ✅ Inicio_Data: Trinta de julho de 2025
  ✅ Honorarios_Valor: R$ 15.000,00
  ✅ Honorarios_Tipo: Provisório

Métricas:
  • Confidence Score: 81.2%
  • Fill Rate: 68.8%
  • Processing Time: 48,196ms
```

## Arquitetura Validada

**Backend**: FastAPI endpoint com Pydantic v2 schemas  
**Esquema**: `ExtractionData` + `QuesitosAgrupados` + `Quesito(BaseModel)` ✅  
**Extração**: Qwen 3.6 local (Mac) via Ollama sobre tunnel SSH  
**Roteamento**: VPS → socat bridge 172.17.0.1:11435 → SSH tunnel → Mac localhost:11434  
**Nginx**: Timeouts 300s (linha 1006-1008 `/etc/nginx/sites-enabled/default`)  
**Container**: Docker `perito-v6-backend` conectando via docker0 bridge  

## Comandos Críticos

**SSH Tunnel** (rodar no Mac):
```bash
ssh -N -R 11435:localhost:11434 root@129.121.34.186 -p 22022 -i ~/.ssh/id_ed25519_perito
```

**Socat Bridge** (VPS, rodando via `scripts/start-socat.sh`):
```bash
socat TCP4-LISTEN:11435,bind=172.17.0.1,reuseaddr,fork TCP4:127.0.0.1:11435
```

**Testar Extração**:
```bash
curl -X POST http://129.121.34.186/api/v1/ferramentas/auto-laudo/extrair \
  -H "Content-Type: application/json" \
  -d '{"file_content": "base64...", "file_type": "TXT", "file_name": "...", "tipo_pericia": "Engenharia"}'
```

## Próximos Passos

**Phase 1** (CONCLUÍDO): Extração de dados ✅  
**Phase 2** (PRÓXIMO): Geração de laudo via Qwen + template DOCX  
**Phase 3**: Integração frontend (botão "Extrair" + tab de laudos)  
**Phase 4**: Workflow completo (extrair → gerar → assinar A3 → protocolar)

## Commits Relacionados

- `21d0b1b`: fix schema — novo Quesito sub-class  
- `308cb3d`: fix settings OLLAMA_URL → 172.17.0.1  
- `bf0b114`: fix OLLAMA_URL docker0 bridge IP

---

**Why**: Validação E2E prova que arquitetura de tunnel + socat bridge funciona em produção com Qwen local.  
**How to apply**: Tunnel deve estar ligado antes de chamar endpoints. Health check deve testar endpoint `/extrair` com payload teste.

Relacionado: [[ferramentas_modularizacao_12_08_2026]], [[diagnostico_ia_routing_10_08_2026]], [[omniroute_instalado]]
