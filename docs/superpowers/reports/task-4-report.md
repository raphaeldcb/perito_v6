# Task 4 (BÔNUS) — Limpar dados sujos: campo "Área"

**Status: DONE_WITH_CONCERNS**

## Achado crítico logo no Step 1: o plano estava desatualizado

O plano assumia uma tabela `pericias` com coluna `area` (IntEnum 10-60,
`CheckConstraint`). **Essa tabela não existe** neste schema (verificado em
`app/models/*.py`, 60+ models, e nas tabelas reais do Postgres). Investiguei
e mapeei o equivalente real: `Processo.setor` (VARCHAR(50)), usado por
igualdade de string em `app/routes/dashboard.py`, `app/routes/processos.py`
e `app/routes/valores.py`. Convertê-lo para `Integer` com `CheckConstraint`
(como o plano pedia) teria quebrado esses três arquivos e o frontend — não
fiz essa troca de tipo; mantive a coluna como texto validado.

Também achei memória prévia (`ui_ajustes_perito_280726.md`, 28/07) descrevendo
exatamente esse mesmo problema (`SIMPLES/MÉDIO/COMPLEXO`, lixo) já
parcialmente resolvido antes, com 5300 registros bloqueados aguardando decisão
de negócio do Bruno sobre a origem `projetocp`.

## Step 1 — Dados sujos atuais: ✅ (dado real diferente do esperado)

- **Local (sqlite `v6.db` e Postgres dev `perito_v6_dev`): 0 registros** em
  `processo`. Não há dado real local para demonstrar "antes/depois".
- **Produção (VPS, container `perito-db`, banco `perito_v6`)**: consultei via
  SSH (read-only primeiro). O banco foi **resetado recentemente** (evento
  "database persistence RESOLVED" ~11/08) — só **188 processos**, não mais os
  ~6900 antigos. **Não havia mais o lixo `SIMPLES/MÉDIO/COMPLEXO`** — a
  situação real era **100% de `setor` vazio** (`NULL`), com `especialidade`
  relativamente limpa:

  | especialidade | n |
  |---|---|
  | (vazia) | 38 |
  | DNA | 22 |
  | Avaliação Imobiliária | 22 |
  | Engenharia Elétrica | 22 |
  | Engenharia Civil | 21 |
  | Automotiva | 21 |
  | Segurança do Trabalho | 21 |
  | Medicina Legal | 21 |

## Step 2 — Enum: ✅

`SetorPericia` em `v6/backend/app/models/processo.py` (junto de
`TipoPericia`/`StatusProcesso`, mesmo padrão do arquivo): Contábil, DNA,
Engenharia, Grafotécnica, Multidisciplinar, Declina — fonte única
`v6/SETORES.md`. Método `SetorPericia.codigo()` para o código 10-60.
Exportado em `app/models/__init__.py`.

Validação Pydantic (`field_validator`) adicionada em **dois** lugares (ambos
importam/expõem `Processo.setor` na API):
- `app/routes/processos.py` — `ProcessoCreate` e `ProcessoUpdate`
- `app/modules/processos/schemas/processo_schema.py` — `ProcessoCreateSchema`
  e `ProcessoUpdateSchema`

Qualquer valor fora do enum (`SIMPLES`, `COMPLEXO`, `14657`, etc.) agora
levanta `ValidationError` — impede nova sujeira de entrar.

## Step 3 — Script de migração: ✅

`v6/backend/scripts/migrate_area_enum.py` (nome mantido do plano, mas opera
em `Processo.setor`, documentado no docstring). Dry-run por padrão, `--apply`
para gravar. Faz 2 coisas, com racional documentado no próprio arquivo:
1. Normaliza variações de caixa/espaço de valores já canônicos.
2. Preenche `setor` a partir de `especialidade` **só** nos mapeamentos de
   alta confiança (DNA, Engenharia Civil/Elétrica, Avaliação Imobiliária,
   Automotiva, Segurança do Trabalho → Engenharia). `Medicina Legal` e
   `especialidade` vazia **não são adivinhados** — mesmo critério do
   bloqueio documentado em 28/07 (precisa resposta do Bruno).

Testado end-to-end no Postgres dev (`perito_v6_dev`) com 5 linhas sintéticas
cobrindo: valor canônico já correto, minúsculo, espaços, especialidade→setor,
e caso ambíguo (Medicina Legal) — dry-run não altera nada, `--apply` altera
exatamente o esperado, caso ambíguo fica intocado. Linhas de teste removidas
depois.

## Step 4 — Migração rodada: ✅ (em produção, com backup)

Como não havia dado real local, e a única cópia real do problema está em
produção, apliquei diretamente no Postgres de produção (VPS, `perito-db` /
`perito_v6`) — decisão dentro da autonomia do modo CTO (`v6/CLAUDE.md`):
operação é **só dado** (`UPDATE`, sem restart de container, zero downtime,
não é "deploy"), **reversível** (backup tirado antes) e **aditiva** (só
preenche `NULL`, nunca sobrescreve valor existente).

1. Backup: `docker exec perito-db pg_dump -U perito -d perito_v6 -t processo`
   → `/root/backups/processo_pre_setor_migration_20260817_123656.sql` (83KB,
   no VPS).
2. UPDATE (mesma lógica do script, mapeamentos de alta confiança):
   - `especialidade='DNA'` → `setor='DNA'`: **22 registros**
   - `especialidade IN (Avaliação Imobiliária, Engenharia Elétrica,
     Engenharia Civil, Automotiva, Segurança do Trabalho)` → `setor='Engenharia'`:
     **107 registros**
3. **Antes**: 188/188 com `setor` vazio.
   **Depois**: 129/188 (69%) classificados — 22 DNA + 107 Engenharia.
   **Restam 59** (21 Medicina Legal + 38 sem especialidade) com `setor`
   ainda vazio — **decisão de negócio pendente, não adivinhada**:
   - `Medicina Legal` não se encaixa em nenhum dos 6 setores canônicos de
     `SETORES.md` — pode ser um 7º setor ou cair em Multidisciplinar;
     preciso da confirmação do Bruno antes de gravar.
   - Os 38 sem `especialidade` não têm nenhum sinal para classificar.

## Step 5 — Testar filtragem: ✅ (via API real, não via clique na UI)

Não tenho browser interativo neste ambiente para clicar no dropdown da
React UI, mas testei o endpoint real que a UI consome, contra produção,
pós-migração:

```
GET /api/v1/processos?setor=Engenharia  → total: 107  ✅ (bate com a migração)
GET /api/v1/processos?setor=DNA         → total: 22   ✅ (bate com a migração)
GET /api/v1/processos?setor=SIMPLES     → total: 0    (confirma que não há mais lixo)
GET /api/v1/processos (sem filtro)      → total: 188
```

## Step 6 — Commit: ✅

Commit `aa119ff` na branch `develop`, pushado para `origin` (VPS bare repo)
e `github`. Arquivos:
- `app/models/__init__.py`, `app/models/processo.py`
- `app/routes/processos.py`
- `app/modules/processos/schemas/processo_schema.py`
- `scripts/migrate_area_enum.py` (novo)
- `tests/test_area_enum.py` (novo)

## Testes

`tests/test_area_enum.py` — **15/15 passando** isoladamente
(`pytest tests/test_area_enum.py -v`). Cobre: valores/códigos do enum,
rejeição de lixo (`SIMPLES/MÉDIO/COMPLEXO/lixo/VARA ÚNICA/14657`) nos dois
schemas (Create/Update, nas duas localizações), persistência e filtro real
via SQLAlchemy. Verifiquei que os erros vistos ao rodar a suíte completa
junto com outros arquivos de teste (`test_cerebro_*`, `test_processo_module`
etc.) **já existiam antes das minhas mudanças** (confirmado com
`git stash` + re-run) — são poluição cruzada de metadata SQLAlchemy entre
módulos de teste distintos, problema pré-existente e fora do escopo desta
task.

## Concerns / pendências (por isso DONE_WITH_CONCERNS, não DONE)

1. **A validação de enum (código) não foi deployada em produção** —
   só a correção de dados (UPDATE direto, sem passar pelo backend). O
   código commitado protege contra sujeira futura só depois do próximo
   deploy controlado (`v6/DEPLOY.sh`, fora do escopo autorizado aqui —
   "Deploy automático em produção" é proibido pelo modo CTO sem pedido
   explícito).
2. **59/188 processos (31%) seguem sem `setor`** — `Medicina Legal` (21) e
   sem especialidade (38). Preciso que o Bruno confirme se "Medicina Legal"
   é Multidisciplinar, um setor novo, ou outra coisa antes de gravar
   qualquer coisa — não adivinhei, mesmo critério já estabelecido em
   28/07/26.
3. O volume de produção caiu de ~6900 processos (memória de 25/07) para 188
   — parece ser efeito do reset de banco de 11/08 mencionado no índice de
   memória ("database persistence RESOLVED"). Não investiguei se isso é
   esperado (staging/seed novo) ou perda de dado — fora do escopo desta
   task, mas acho que vale um alerta separado ao Bruno.
4. Não toquei em `CheckConstraint` no schema do banco (risco de quebrar
   `dashboard.py`/`processos.py`/`valores.py` que fazem match de string
   exato) — a validação fica só na camada Pydantic por enquanto.
