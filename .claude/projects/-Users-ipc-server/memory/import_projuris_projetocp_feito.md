---
name: import_projuris_projetocp_feito
description: "25/07/26 ✅ IMPORTADO: 2182 Projuris + 4733 ProjetoCP = 6915 processos LIVE na API/site"
metadata: 
  node_type: memory
  type: project
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-25T15:24:06.284Z
---

# Import Projuris + ProjetoCP — FEITO 25/07/26

## Resultado ✅
- **Projuris**: 2182 processos (source_system='projuris')
- **ProjetoCP**: 4733 laudos (source_system='projetocp')
- **Total na API**: 6915 processos, visíveis em https://sistema.ipcms.com.br
- Acentos UTF-8 corretos end-to-end.

## Fatos NÃO-óbvios do banco (pra próximos imports)
- **psql user é `perito`** (senha `perito_pass`), NÃO `perito_user`. O `.env` diz perito_user
  mas o `docker-compose.yml` sobrescreve o backend com `postgresql://perito:${POSTGRES_PASSWORD}@db`.
  Rodar SQL: `docker-compose exec -T db psql -U perito -d perito_v6`.
- **Tabela `processo`**: numero_cnj é NOT NULL + UNIQUE (ix_processo_numero_cnj). Campos varchar
  são **varchar(200)** — truncar strings longas (partes/autor/reu) senão erro "value too long".
  descricao é TEXT (full). `docker cp`/SQLite dentro do container NÃO acessa /var/www (volume).
  Import via: gerar .sql local → scp /tmp → `psql < /tmp/x.sql` no container db.
- **API filtra `responsavel_id == user.id`** (routes/processos.py:33). Import PRECISA setar
  `responsavel_id=1, empresa_id=1` (admin id=1) senão a API retorna total=0. Tabela usuários = `usuario`.
- Diretório do compose no VPS: `/var/www/perito-v6/backend_broken/v6` (o "broken" é histórico, está OK).

## Projuris (Excel)
- Arquivo: `~/Downloads/Processos_em_planilha_21_07_2026_19_17_56.xlsx` (aba "Processos").
- **Cabeçalho na linha índice 2** (linhas 0-1 são título decorativo), dados a partir da 3.
- Colunas úteis: [1]Identificador PRO.xxx, [3]Assunto→titulo, [8]Descrição, [14]Órgão(TJMS-Comarca),
  [15]**Número CNJ**, [17]Órgão julgador→vara, [20]Área→especialidade, [45]Partes ativas→autor,
  [46]Partes passivas→reu. 2209 c/ CNJ → **2182 únicos** (27 dup).
- Script gerador: scratchpad/gen_projuris_sql.py

## ProjetoCP (Firebird 1.5 — legado Delphi/Pascal)
- Fonte: `~/Downloads/ProjetoCP/Base/SGBD_CP.FDB` (46MB). O .zip só tem o CÓDIGO Delphi.
- **ODS 10.1 = Firebird 1.5** (page size 1024, gerado ~2004). FB 2.5+ NÃO abre direto.
- Tabela principal: **CONTROLE_LAUDOS (4733)** — cols NUM_LAUDO(único, ex L2024.060), NUM_PROCESSO
  (parcial), PARTEA/PARTEB, COMARCA, VARA, CLASSE, VALOR, ANO. Outras: TB_FINANCEIRO(3999),
  LAUDOS_RELATORES(2395), HISTORICO_LAUDO(7842), TB_COMARCAS/VARAS/JUIZ. TB_PROPOSTAS está vazia.
- Encoding do FDB: **Windows-1252/Latin-1** (charset NONE). Extrair com `-ch NONE` e decodificar `cp1252`.
- numero_cnj usado = NUM_LAUDO (NUM_PROCESSO é incompleto/vazio); NUM_PROCESSO vai na descricao.

### Técnica de extração Firebird 1.5 (REUTILIZÁVEL)
1. Copiar .FDB pro VPS, `chmod 666`.
2. `gbak -b` com **Firebird 1.5** num container `i386/debian:bullseye-slim`:
   - baixar `FirebirdCS-1.5.6.5026-0.i686.tar.gz`, extrair `buildroot.tar.gz` → gbak em /opt/firebird/bin
   - precisa `libstdc++5` i386 (archive.debian.org pool gcc-3.3) — senão "libstdc++.so.5 not found"
   - `gbak -b -user SYSDBA -password masterkey /data/SGBD_CP.FDB /data/cp.fbk` → .fbk (backup portável)
3. Restaurar no FB 2.5 (`jacobalberty/firebird:2.5-ss`): `gbak -c cp.fbk cp_v25.fdb` (vira ODS 11.2).
4. Extrair via isql: `SELECT ... || ASCII_CHAR(9) || ...` (tab), `SET HEADING OFF`, `-ch NONE`, redirect > dump.txt.
5. Trazer dump, decodificar cp1252, gerar INSERTs, importar.
- Scripts: scratchpad/fb15_backup.sh, extract.sql, gen_projetocp_sql.py
- ⚠️ ASCII_CHAR(9) no Firebird (não CHR). gstat -h mostra ODS mesmo sem abrir o banco.

## Financeiro + Relatores — FEITO 25/07/26 (nada fica de fora)
Criadas 3 tabelas dedicadas (não mexi nas tabelas vivas `financeiro`/`laudo` — legado tem modelo
diferente: 617 órfãos, data_venc nula, relatores com numeração própria; risco de quebrar app):
- **projetocp_financeiro** (3999): TB_FINANCEIRO. Liga a processo via CONTROLE=NUM_CONTINF→NUM_LAUDO
  →processo.external_id. **3382/3999 linkados** (processo_id). R$ 17,2M total, 1427 quitados.
  Cols: fin_cod, controle, num_laudo, processo_id, valor, parcela, data_vencimento, data_pagamento,
  situacao, tipo_pgto, quitado, conta_unica, pagador, obs.
- **projetocp_laudo_relator** (2395): LAUDOS_RELATORES + nome do relator. 43 relatores, R$ 1,7M pago.
  ⚠️ NUM_LAUDO aqui é série PRÓPRIA (`L2008.0001`, 4 díg) ≠ CONTROLE_LAUDOS (`L2008.009`, 3 díg) →
  só 2 linkam a processo; dados preservados igual (nome relator + valores).
- **projetocp_relator** (63): RELATORES (cd_relator, nome, area). Ex: Dr. Helder (DIREÇÃO), Dr. Alberto (ENG/AGRÁRIA).

Ligações-chave no Firebird: TB_FINANCEIRO.CONTROLE = CONTROLE_LAUDOS.NUM_CONTINF (não NUM_LAUDO!);
LAUDOS_RELATORES.CD_RELATOR → RELATORES.CD_RELATOR. Scripts: scratchpad/gen_fin_rel_sql.py, extract_{fin,rel,relatores}.sql.

**Estado final BD: 6915 processos + 3999 financeiro + 2395 laudo_relator + 63 relatores.**

## Falta (opcional, futuro)
- Expor projetocp_financeiro/relatores na UI/API (hoje só nas tabelas, não no app).
- Vincular laudos ProjetoCP a intimações. RAG dos laudos.
