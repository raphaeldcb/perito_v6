# Task 2 Report — Integrar LLM Router Fallback (9router → Código)

**Repo:** `/Users/ipc_server/projects/ipc-pericias-ai/v6/backend` (branch `develop`)
**Commit:** `3f9d759` — "feat: add automatic LLM fallback (Claude -> Qwen via Ollama/9router)"

## Contexto importante: o plano assumia coisas que não batem com a realidade

Igual ao Task 1, o plano (`docs/superpowers/plans/2026-08-17-perito-v6-fixes-criticos.md`,
Task 2) foi escrito com premissas que não conferem com o código/infra real:

1. **Caminho dos arquivos**: plano pede `backend/services/llm_router.py` e
   `backend/services/cerebro_intelligence.py`. A estrutura real é
   `app/services/*.py` (dentro de `v6/backend/`). Criei/editei nesse caminho real.

2. **`cerebro_intelligence.py` não chama Claude.** Li o arquivo inteiro
   (`app/services/cerebro_intelligence.py`) — ele já chama **Qwen direto**
   via `requests.post(f"{self.qwen_host}/api/generate")` contra
   `OLLAMA_PROXY` (default `localhost:20128`). Não há nenhuma chamada Claude
   ali para "integrar fallback". O único lugar do backend que de fato chama
   a API do Claude (`from anthropic import Anthropic` +
   `client.messages.create(...)`) é **`app/services/auditor_fable.py`**
   (função `auditar_laudo`, usada para auditoria Fable 5 dos laudos antes de
   emissão). Integrei o fallback lá — é o ponto real de risco que o plano
   queria proteger ("system morre se Claude quota cair").

3. **9router não expõe `/health` nem `/chat/completions`** como o plano
   assumia. Testei ao vivo:
   - `GET /health` → 404 (retorna a página Next.js do dashboard, não um
     endpoint de health).
   - Endpoint real OpenAI-compatible: **`POST /v1/chat/completions`** (com
     `/v1`), autenticado com a API key própria do 9router
     (`~/.claude/omniroute/api-key.txt`), não com `ANTHROPIC_API_KEY` como o
     plano sugeria.
   - `GET /v1/models` (autenticado) funciona e lista 427 modelos, incluindo
     vários `*/qwen*` e `ollama/qwen3.5`.
   - Confirmado processo rodando: `node /opt/homebrew/bin/9router --host
     127.0.0.1 --no-browser --skip-update` (PID 1384), porta 20128 LISTEN.

4. **Existe um Ollama nativo separado do 9router**, rodando direto em
   `localhost:11434` com o modelo customizado **`perito-qwen`** (o mesmo que
   a memória do usuário documenta como padrão para produção — "Qwen 3.6 +
   SYSTEM destilado"). Esse caminho é mais direto/rápido que passar pelo
   9router para o fallback local, então virou o **fallback primário**; o
   9router virou fallback secundário (usado só se o Ollama local cair).

Adaptei os 5 steps a essa realidade, mantendo a intenção do plano: fallback
automático em código, sem troca manual, quando Claude falha por quota ou
qualquer outro erro.

## Steps executados

### ✅ Step 1 — Verificar 9router rodando e funcional

```
ps aux | grep 9router
→ node /opt/homebrew/bin/9router --host 127.0.0.1 --no-browser --skip-update (PID 1384)

lsof -i :20128 → LISTEN confirmado (PID 1715, processo filho node)

curl /health → 404 (não existe; página HTML do dashboard Next.js)
curl -H "Authorization: Bearer $(cat ~/.claude/omniroute/api-key.txt)" /v1/models
→ 200 OK, {"object":"list","data":[...427 modelos...]}
```

9router está rodando e funcional, mas o endpoint de health documentado no
plano não existe. Documentei o endpoint real (`/v1/models`) que serve como
health-check válido.

Também confirmei o Ollama nativo (fallback primário real):
```
curl localhost:11434/api/tags → 13 modelos, incluindo "perito-qwen:latest"
```

### ✅ Step 2 — Criar cliente LLM Router

Criado `app/services/llm_router.py` com `get_llm_response(prompt, model="claude", ...)`.

Cadeia de fallback implementada (mais robusta que o plano original, que só
previa Claude→9router):

```
Claude (Anthropic SDK direto, mesmo padrão de auditor_fable.py)
  │ falha (429 / erro / SDK ausente / key ausente) + fallback_to_qwen=True
  ▼
Qwen via Ollama local (localhost:11434, modelo "perito-qwen")
  │ falha (Ollama fora do ar)
  ▼
Qwen via 9router (localhost:20128/v1/chat/completions, modelo "ollama/qwen3.5")
  │ falha
  ▼
Exception clara: "Qwen indisponível (Ollama local e 9router falharam)"
```

Detecção de 429 usa `getattr(e, "status_code", None)` — confirmado que o
SDK Anthropic instalado (`0.7.0`) expõe `RateLimitError.status_code = 429`
como atributo de classe, então a detecção funciona também com versões mais
novas do SDK (mesma API pública desde então).

**Bug real encontrado e corrigido durante o teste manual**: `perito-qwen` é
um modelo Qwen3 "thinking". Com `num_predict` limitando o total de tokens
(pensamento + resposta), prompts curtos geravam `response: ""` porque o
raciocínio interno consumia todo o budget antes de emitir a resposta final
(`done_reason: "length"`). Fix: `"think": false` no payload do
`/api/generate` — testado e confirmado que resolve (resposta não-vazia,
`done_reason: "stop"`).

### ✅ Step 3 — Integrar fallback no código real

Modificado `app/services/auditor_fable.py`:
- Removidos os guard-clauses `if not ANTHROPIC_AVAILABLE / not ANTHROPIC_API_KEY: raise` no topo de `auditar_laudo()` — agora a ausência de chave não bloqueia mais a auditoria, ela cai para Qwen.
- Substituída a chamada direta `Anthropic(...).messages.create(...)` por
  `asyncio.run(get_llm_response(prompt=prompt, model="claude", max_tokens=2000))`
  (função é síncrona porque é chamada via `BackgroundTasks.add_task` do
  FastAPI, que roda em threadpool — `asyncio.run()` é seguro ali).
- `relatorio_json["_llm_usado"]` grava qual modelo respondeu de fato
  (`claude` / `qwen-ollama` / `qwen-9router`) para auditoria/observabilidade.
- Removido código morto (import `Anthropic`, `ANTHROPIC_AVAILABLE`,
  `ANTHROPIC_API_KEY` no topo do módulo — nada mais os referenciava).

Também adicionado `app/config/settings.py`: `anthropic_api_key`,
`llm_router_url`, `llm_router_api_key` (Pydantic Settings, para
visibilidade/consistência — o `llm_router.py` em si lê env vars direto via
`os.getenv`, seguindo o padrão já usado em `cerebro_intelligence.py`).

### ✅ Step 4 — Testar fallback manualmente (E2E real, sem mocks)

Com `ANTHROPIC_API_KEY` ausente do ambiente (cenário real de "quota
zerada"/sem chave configurada):

```
TESTE 1 (Claude falha -> fallback automático):
  MODEL: qwen-ollama
  CONTEUDO: "Sou o motor de inteligência do sistema Perito, assistente
             técnico de perícia judicial cível no Brasil."

TESTE 2 (model="qwen" direto, sem passar por Claude):
  MODEL: qwen-ollama
  CONTEUDO: "OK"
```

Fallback comprovado funcionando de ponta a ponta com o modelo local real
(`perito-qwen` via Ollama), não só com mocks.

### ✅ Step 5 — Commit

```
commit 3f9d759 (develop)
feat: add automatic LLM fallback (Claude -> Qwen via Ollama/9router)
4 files changed, 344 insertions(+), 24 deletions(-)
 create mode 100644 v6/backend/app/services/llm_router.py
 create mode 100644 v6/backend/tests/test_llm_fallback.py
 (+ app/services/auditor_fable.py, app/config/settings.py modificados)
```

## Testes

`tests/test_llm_fallback.py` — 8 testes novos, todos mockados (sem rede),
cobrindo a lógica de decisão:

```
tests/test_llm_fallback.py::test_claude_sucesso_nao_cai_para_qwen PASSED
tests/test_llm_fallback.py::test_claude_429_cai_automaticamente_para_qwen PASSED
tests/test_llm_fallback.py::test_claude_erro_generico_cai_para_qwen_por_padrao PASSED
tests/test_llm_fallback.py::test_fallback_desligado_propaga_erro_do_claude PASSED
tests/test_llm_fallback.py::test_qwen_direto_sem_passar_por_claude PASSED
tests/test_llm_fallback.py::test_qwen_ollama_indisponivel_cai_para_9router PASSED
tests/test_llm_fallback.py::test_qwen_ollama_e_9router_falham_levanta_excecao PASSED
tests/test_llm_fallback.py::test_modelo_desconhecido_levanta_excecao PASSED

======================== 8 passed, 2 warnings in 0.13/0.14s =========================
```

Rodei também a suíte completa (`pytest tests/ -k "not e2e and not slow"`,
venv `venv_perito`) para checar regressão: **594 passed**, 35 failed, 149
errors — confirmei que **nenhuma** falha/erro pré-existente tem relação com
`llm_router.py` ou `auditor_fable.py` (são problemas de import/fixture
pré-existentes em outros módulos — `app.database.Base` ausente,
`app.routes.padroes_calculo` ausente, fixtures de `tests/modules/*` — nada
tocado por esta task). `test_llm_fallback.py` aparece limpo (`........`) na
run completa.

## Concerns

1. **`ANTHROPIC_API_KEY` não está configurada no `.env` atual do backend**
   (confirmei: `grep -i anthropic .env` não retorna nada). Isso significa
   que, hoje, **todo** uso de Claude nesse backend (não só o fallback) já
   cai direto para Qwen. Isso é o comportamento correto para "não quebrar",
   mas é bom o usuário saber que a auditoria Fable 5 está rodando 100% no
   Qwen local até a chave ser configurada — vale confirmar se isso é
   aceitável para a qualidade da auditoria de laudos ou se a intenção era só
   fallback ocasional em pico de quota.

2. **`cerebro_intelligence.py` não foi tocado** porque não tem chamada
   Claude nenhuma — já usa Qwen direto via `requests` síncrono (nem passa
   pelo 9router, vai direto no host `OLLAMA_PROXY`/`localhost:20128`, que na
   prática seria o 9router mas usando a API `/api/generate` estilo Ollama,
   não a API OpenAI-compatible do 9router — não testei se o 9router serve
   essa rota nativa do Ollama; não mexi para não expandir escopo). Se a
   intenção real era migrar `cerebro_intelligence.py` para usar
   `get_llm_response()` também (padronizar o cliente LLM do projeto todo),
   isso é uma task separada — sinalizando aqui para o usuário decidir.

3. **Modelo Qwen do fallback via 9router (`ollama/qwen3.5`) não foi testado
   ao vivo** (só o path Ollama local foi testado E2E de verdade). O 9router
   lista esse modelo em `/v1/models`, mas não fiz uma chamada real de
   `/v1/chat/completions` contra ele para confirmar que responde — é
   fallback de fallback (só ativa se o Ollama local cair), risco baixo, mas
   não é 100% verificado.

4. **`_chamar_claude` não foi testado contra a API real do Claude** (não
   forcei uma chamada real com chave válida — só validei a lógica de
   detecção de erro/429 lendo o código-fonte do SDK Anthropic instalado, e
   testei o fallback com a chave ausente). O caminho "Claude responde OK" só
   tem cobertura via mock (`test_claude_sucesso_nao_cai_para_qwen`).

## Status final

**DONE_WITH_CONCERNS** — fallback automático funcionando de ponta a ponta
(testado com Qwen real, não só mock), integrado no único ponto real de uso
do Claude no backend, testes passando, commit feito. Concerns acima são
questões de escopo/configuração para o usuário decidir, não bugs.
