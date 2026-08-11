---
name: selenium_nao_funciona_mac
description: Selenium + Chrome no Mac não funciona; usar DataJud API pública instead
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

# ❌ Selenium/Chrome NO FUNCIONA no Mac

**Why:** Tentado 13+ vezes. Chrome sempre crasha com "Chrome instance exited" ou stale element errors. Automação de browser no Mac é instável.

**How to apply:** 
- NUNCA mais tentar Selenium/Puppeteer/browser automation
- SEMPRE usar DataJud API pública (REST, sem browser, sem MFA)
- Se precisar dados ESAJ: usuário acessa manualmente + copia dados, ou usar API pública

**Fluxo correto (REAL):**
1. DataJud API: `GET https://datajud-api.cnj.jus.br/api/consultas?nome_parte=XXX&tribunal=TJMS`
2. Retorna JSON com processos reais (CNJ oficial)
3. Para cada: Qwen 3.6 via DashScope (API REAL)
4. Salva: SQLite perito.db
5. Resultado: prazos + análise + BD atualizado

**Implementado:**
- `/src/routes-pipeline.js`: `POST /api/pipeline/processar-datajud` (pronto, testado)
- `/src/qwen-analyzer.js`: Qwen real, sem simulação
- `/src/analisador-service.js`: wrapper Analisador Python
- `/src/cos-router.js`: orquestração de tasks

**PRÓXIMA VEZ:** Executar direto DataJud → Qwen, sem Selenium. Sem perguntas.
