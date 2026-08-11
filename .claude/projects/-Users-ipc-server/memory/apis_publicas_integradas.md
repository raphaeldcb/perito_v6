---
name: apis-publicas-integradas
description: "APIs públicas gratuitas integradas ao Perito v6 (rotas /api/v1/publico/*) — prazos, CNPJ, CEP, PTAX, câmbio, FIPE, municípios"
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# APIs Públicas no Perito v6 (09/07/26, commit 4649e3c — LIVE)

Curadoria do public-apis/public-apis. Catálogo completo: `v6/docs/APIS-PUBLICAS.md`.

**Rotas novas (JWT) em `/api/v1/publico/`:**
- `prazo?inicio&dias&uteis` — data fatal CPC 219/224 com feriados nacionais reais (BrasilAPI)
- `feriados/{ano}`, `cnpj/{cnpj}` (fallback ReceitaWS, traz QSA), `cep/{cep}` (fallback ViaCEP)
- `cambio/{par}` (AwesomeAPI, aceita BTC-BRL), `ptax?data=` (dólar OFICIAL BCB p/ laudo)
- `fipe/marcas|modelos|anos|valor` (avaliação de veículos), `municipios/{uf}` (IBGE)

**Arquivos:** `services/apis_publicas.py` (cache TTL + fallbacks), `routes/publico.py`.

**Não duplicar:** índices de atualização (SELIC/IPCA/INPC/IGP-M/TR/Poupança) JÁ existem
em `services/indices_bcb.py` (BCB SGS persistido, worker atualiza a cada 10 dias).

**Candidatas futuras (exigem chave):** Boleto.Cloud (cobrança de honorários),
BB Developers (conciliação bancária), CPFHub (⚠️ LGPD), OCR.Space (fallback Tesseract),
MercadoBitcoin (perícia cripto), Nager.Date (fallback feriados).

**Aprendizados:** BrasilAPI dá 429 fácil — fallbacks obrigatórios (ReceitaWS/ViaCEP
já acionaram em teste real). PTAX não existe em fim de semana/feriado (endpoint avisa).

Relacionadas: [[fluxo_completo_20260709]], [[fable5_contexto_20260709]]
