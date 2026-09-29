# Task 1 Report — Restaurar Build Context FastAPI

**Repo:** `/Users/ipc_server/projects/ipc-pericias-ai/v6/backend` (branch `develop`)
**Commit:** `d94353f` — "fix: restore build-context integrity — 43/43 routers + 6/7 modules now load clean"

## Contexto importante: o plano assumia uma estrutura que não existe mais

O plano (`docs/superpowers/plans/2026-08-17-perito-v6-fixes-criticos.md`, Task 1)
foi escrito assumindo `backend/main.py` + `backend/routers/*.py` com
`from .routers import X` / `app.include_router(X.router)`. Essa estrutura **não
existe** no código atual. A realidade (confirmada em disco):

- Entrypoint real: `app/main.py` (não `backend/main.py`).
- Routers "legacy" vivem em `app/routes/*.py` (65 arquivos), registrados via
  uma tabela `_ROUTERS` em `app/routes/__init__.py` — **loader resiliente**
  escrito em 27/07/26 ("never again") que faz `try/except` por router e
  **pula silenciosamente** o que falhar ao importar, sem derrubar o app.
- Routers "modularizados" (Wave 1) vivem em `app/modules/*` e são
  auto-descobertos por `app/config/module_loader.py`.
- `git status` já estava limpo no início — não havia routers "stripados" no
  código commitado. O `Dockerfile` faz `COPY . .` (copia tudo).

Ou seja: o problema real não é "routers faltando no main.py" (isso já foi
resolvido em algum momento entre a memória de 25/07 e hoje). O problema real
é mais sutil e mais perigoso: **o loader resiliente mascara silenciosamente
dependências que faltam em `requirements_v6.txt`** — o container de produção
funciona porque alguém instalou pacotes manualmente nele (`docker exec pip
install ...` ou `docker cp`), mas um `docker build` do zero, seguindo só o
que está commitado, perderia routers sem avisar (sem crash, sem erro 500
óbvio — só endpoints que somem).

Adaptei a Task 1 para investigar e corrigir exatamente esse cenário, que é
a essência do que o plano queria resolver.

## Steps (adaptados à estrutura real)

### ✅ Step 1 — Diagnóstico: quantos routers estão faltando no build

Rodei `from app.main import app` num venv (`venv_perito`) só com o que já
estava instalado — **6 routers pulados + módulo `ferramentas` inteiro
falhando** por `ModuleNotFoundError: No module named 'google'` (era venv
desatualizado, não refletia `requirements_v6.txt`). Depois de
`pip install -r requirements_v6.txt` no venv (reproduzindo exatamente o que
o Dockerfile faz), sobraram **2 causas raiz reais**:

1. **`playwright`** ausente de `requirements_v6.txt` — usado por
   `app/services/tjms_downloader.py` (routers `tjms`, `inter_api`). Estava
   rodando em produção porque foi instalado manualmente no container, nunca
   commitado.
2. **Bug real de shadowing em `app/modules/ferramentas/__init__.py`** (linha
   81): `from .auto_laudo_pro import router as auto_laudo_pro_router`.
   `auto_laudo_pro/__init__.py` já expõe o APIRouter correto sob o nome
   `auto_laudo_pro_router` — mas como esse mesmo arquivo também faz
   `from .router import router as auto_laudo_pro_router`, o Python cria,
   como efeito colateral do import, um atributo `router` no pacote
   `auto_laudo_pro` que aponta para o **submódulo** `router.py` (arquivo),
   não para o `auto_laudo_pro_router` (instância de `APIRouter`). O import em
   `ferramentas/__init__.py` pega esse atributo errado. Resultado:
   `app.include_router(router)` explode com
   `AttributeError: module '...auto_laudo_pro.router' has no attribute 'routes'`.

### ✅ Step 2 — Corrigir

- `requirements_v6.txt`: adicionado `playwright==1.61.0` (comentário
  explicando que o Dockerfile ainda não roda `playwright install chromium`
  — ver Concerns) e `croniter==2.0.1` (usado por
  `app/services/cerebro_triggers.py`, achado ao rodar a suíte de testes
  completa — ver abaixo).
- `app/modules/ferramentas/__init__.py`: trocado
  `router as auto_laudo_pro_router` por `auto_laudo_pro_router` (import
  direto do nome já correto — mesmo padrão usado por todos os outros 11
  sub-routers do módulo, ex.: `.cerebro import cerebro_router`).
- `app/services/cerebro_engine.py`: `NodeStatus` (enum) não tinha
  `ROLLED_BACK`, mas sua própria tabela de transição de estado (linha 95-96)
  referenciava `NodeStatus.ROLLED_BACK` — `AttributeError` na definição da
  classe, o que **abortava a coleta inteira do pytest** (`INTERNALERROR`,
  nenhum teste rodava). Adicionado `ROLLED_BACK = "rolled_back"` ao enum
  (espelhando `ExecutionStatus`, que já tinha esse membro). Bug pré-existente
  do commit `5d6981c` (25/07), não relacionado a routers, mas bloqueava
  qualquer `pytest tests/` de rodar — corrigido porque o Step 3 do plano
  exige "testes passando".

### ✅ Step 3 — Validar que a app carrega

```
python3 -c "from app.main import app; print(f'✅ App loaded, {len(app.routes)} routes')"
```
Antes das correções: **347 rotas**, 6 routers pulados, módulo `ferramentas`
inteiro fora do ar.
Depois: **465 rotas**, `43 carregados, 0 pulados: []` (routers legacy) +
`6 modules loaded: auth, processos, ia, laudos, ferramentas, esaj` (só
`infra` fica de fora — por design: `__all__ = []`, "Reserved for future
infrastructure endpoints", não tem router nenhum a carregar).

Criei `tests/test_build_integrity.py` (arquivo pedido no plano) com 5 testes:
`test_app_loads_without_crashing`,
`test_all_legacy_routers_load_with_declared_dependencies`,
`test_ferramentas_module_exposes_all_declared_routers` (regressão específica
do bug do shadowing),
`test_module_loader_loads_all_modules_with_routers`,
`test_route_count_matches_production_baseline` (guarda >= 400 rotas).

```
$ pytest tests/test_build_integrity.py -v
5 passed, 110 warnings in 1.21s
```

### ⚠️ Step 4 — Build Docker local

**BLOQUEADO no sandbox**: `docker` (CLI) está instalado mas o daemon não
está rodando (`/var/run/docker.sock` não existe) e não há Docker Desktop
nem `colima` instalados nesta máquina/sessão para subir o daemon. Não
instalei tooling novo sem esse ser o pedido explícito da task.

**Mitigação**: o `Dockerfile` faz exatamente `COPY . .` +
`pip install -r requirements_v6.txt` + `uvicorn app.main:app`. Reproduzi
essas duas etapas manualmente num venv limpo (`pip install -r
requirements_v6.txt` + `from app.main import app`), o que é funcionalmente
equivalente para o que importa aqui (dependências de import resolvidas,
routers carregando). O que essa mitigação **não cobre**: erros de sistema
operacional dentro da imagem (apt packages, versão de Python 3.11-slim vs.
3.11.15 local, etc.) — recomendo rodar `docker build` de fato assim que
houver um daemon disponível (VPS, ou instalar colima localmente) antes de
confiar 100% num rebuild do zero.

### ✅ Step 5 — Commit

```
commit d94353f (branch develop)
fix: restore build-context integrity — 43/43 routers + 6/7 modules now load clean
4 files changed, 123 insertions(+), 1 deletion(-)
 - app/modules/ferramentas/__init__.py
 - app/services/cerebro_engine.py
 - requirements_v6.txt
 - tests/test_build_integrity.py (novo)
```

## Testes — suíte completa

```
pytest tests/ -q
```
Resultado real (sem excluir nada): **599 passed, 43 failed, 167 errors, 1
skipped**. Isolando os problemas:

- **Corrigidos por esta task**: os 5 erros de coleta que travavam o
  `pytest` inteiro com `INTERNALERROR` (causados pelo bug do `NodeStatus`)
  — resolvido.
- **Pré-existentes, fora do escopo de "routers/build"**, não tocados:
  - `tests/test_cerebro_engine.py`, `tests/test_cerebro_triggers.py`:
    importam `Process` de `app.models`, mas o model atual se chama
    `Processo` (renomeado em algum refactor anterior, código do Cérebro
    (25/07) não foi atualizado). `cerebro_triggers.py` não é importado por
    nenhum router atualmente carregado — código órfão do ponto de vista do
    app rodando.
  - `tests/test_fila_intimacoes.py`, `tests/test_fila_routes.py`:
    `app/models/fila_intimacoes.py` importa `Base` de `app.database`, mas
    `app/database.py` é hoje só um stub (`def get_db(): return None`) sem
    `Base` nenhum.
  - `tests/test_interpretar_decisao.py`: importa `padroes_calculo` de
    `app.routes`, símbolo que não existe mais ali (foi movido para
    `app.modules.ferramentas.padroes` na modularização) — teste não
    atualizado após o refactor.
  - **167 errors / 43 failed** no restante da suíte: na maior parte parecem
    ser **poluição de estado entre módulos de teste** — por exemplo
    `tests/modules/processos/test_processo_module.py::test_processo_creation`
    **passa sozinho** mas aparece como `ERROR` quando a suíte inteira roda
    junto. Não investiguei a fundo (não é causado pelas minhas mudanças —
    confirmado rodando os arquivos isolados antes/depois do meu diff, sem
    diferença), mas é um sinal de fixtures/DB compartilhados sem isolamento
    adequado entre módulos. Recomendo uma task dedicada a isso.

## Concerns / observações para revisão

1. **`playwright install chromium` não está no Dockerfile.** O pacote
   Python agora importa OK (routers `tjms`/`inter_api` carregam), mas
   qualquer código que efetivamente tente abrir um browser vai falhar em
   runtime até alguém decidir se vale a pena inchar a imagem Docker com
   Chromium (~300MB+) ou se esses dois routers são vestigiais (a automação
   real de e-SAJ/TJMS, pela memória do projeto, roda no **Windows com
   A3/WebSigner**, não no VPS). Recomendo decisão explícita do Bruno: manter
   playwright como dependência "morta mas importável" ou remover
   tjms.py/inter_api.py do código se são mesmo legado.
2. **`venv_perito/` está commitado no git** (60+ arquivos de binário de
   virtualenv já rastreados antes desta task, `.gitignore` só ignora
   `venv/` não `venv_perito/`). Não toquei nisso — está fora do escopo desta
   task e é arriscado mexer sem alinhar — mas é dívida técnica real que
   deveria ir para um `.gitignore` em algum momento.
3. **Docker build de fato não foi executado** (daemon indisponível no
   sandbox) — ver Step 4. Recomendo confirmar com um build real antes do
   próximo deploy.
4. **Erros de teste pré-existentes e não relacionados** (167 errors / 43
   failed na suíte completa) — documentados acima, não fazem parte do
   escopo de "routers no build" e não foram introduzidos por esta mudança.
   Recomendo tasks separadas para: (a) sincronizar nomes de model
   (`Process`→`Processo`) no código do Cérebro, (b) decidir o destino de
   `app/database.py` (stub morto vs. real), (c) investigar isolamento de
   fixtures entre módulos de teste.

## Status final

**DONE_WITH_CONCERNS** — o objetivo real da task (garantir que o build
reproduz em produção o que está commitado, sem routers "sumindo" em
silêncio) foi alcançado e verificado (347→465 rotas, 0 routers pulados) e
coberto por teste de regressão automatizado. As concerns acima são
achados legítimos que merecem decisão/priorização do Bruno, não bugs
introduzidos por este trabalho.
