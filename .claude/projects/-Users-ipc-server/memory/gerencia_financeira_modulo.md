---
name: gerencia_financeira_modulo
description: "26/07/26 — Módulo Gerência Financeira LIVE no site: receitas R$48.8M + despesas 2013-2023, dashboard consolidado"
metadata: 
  node_type: memory
  type: project
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-27T11:29:16.331Z
---

# Módulo Gerência Financeira — LIVE 26/07/26

Spec: `docs/superpowers/specs/2026-07-25-gerencia-financeira-design.md`
Plano: `docs/superpowers/plans/2026-07-25-gerencia-financeira.md`

## No ar (verificado agent-browser em sistema.ipcms.com.br)
- **3 telas** + menu GERÊNCIA: `/gerencia` (dashboard), `/gerencia/receitas`, `/gerencia/despesas`.
- Dashboard: cards Receita/Despesa/Saldo por ano, gráfico Receita×Despesa/mês, por setor, por categoria.
- Ex 2020: Receita R$5,48M · Despesa R$3,48M · **Saldo +R$2,0M** (realista).

## Dados importados (tabelas `receita` e `despesa`) — atualizado 26/07 fim
- **receita** = **R$81,5M**, anos **2007-2026**:
  - `projetocp` 3999 (R$17,2M) + `controle_financeiro` 37009 (2013-2024, R$31,6M)
  - `financeiro_antigo` (HELDER .xls via LibreOffice) 2007-2012 (~R$5-6M/ano). origem_ref=`ano!mes!sigla` (dedup entre versões).
- **despesa** valores reais **2011-2023** (~R$2-4,6M/ano, rateio removido) via `despesas_gerais`.
  `despesas_folder` 1084 (2024-2026) tem data/descrição mas **valor NULL** (está no PDF).
- Coverage: receita 2007-2026 ✓; despesa 2011-2023 ✓ + 2024-2026 valores via routerclaude ✓.
- **Valores 2024-2026 extraídos (routerclaude)**: pdftotext+Qwen (749 de PDFs) + tesseract OCR+Qwen (38 de imagens)
  = **787 valores** (~73% da pasta), R$2,9M. Scripts: `import_despesas_valores.py` (PDF) + `import_despesas_valores_img.py` (OCR).
  ~297 sem valor (boleto ilegível/sem total) mantêm registro+anexo, completáveis na tela (botão editar).
- **TOTAIS FINAIS: Receita R$81,5M · Despesa R$40,5M · 4335/4509 despesas com valor (96%).**
- Extração de valor 2ª passada (v2, routerclaude): valor do NOME (regex BR) + **OCR de PDF escaneado**
  (pdftoppm→tesseract por→Qwen) → +121 valores. despesas_folder 910/1084 (84%). Script `import_despesas_valores_v2.py`.
- P6: **IPC Debitos** (impostos Pis/Cofins/CSLL/IRPJ em aberto) → 10 despesas origem='recorrente'. Unimed = beco (sem coluna de valor).
- Despesa por origem: despesas_gerais R$37,1M (2011-2023) · despesas_folder R$3,33M (2024-2026) · recorrente R$66k (impostos).
- **27/07 os "174 boletos ilegíveis" eram DESTRUÍDOS por bug de rename (29/04)** → recuperados via histórico de versão do
  SharePoint (Graph API). **67 recuperados+aplicados** (cobertura 96%→97,6%, 4414/4521). Ver [[boletos_recuperacao_versao_graph]].
  ~107 ainda NULL: faturas cartão multi-total/outro-titular, scans sem total, xlsx multi-valor — anexos recuperados, completáveis manual.
- Irrecuperável de verdade (fonte): despesa 2007-2010 (.xls corrompido); extratos de cartão xlsx (multi-transação ambíguo).

## Arquitetura (o que foi feito)
- Tabelas canônicas `receita` (nova) + `despesa` (estendida: ano/mes/pago/origem/origem_ref).
- Router `app/routes/gerencia.py` → `/api/v1/gerencia/{dashboard,receitas,despesas,por-relator}` (+POST/PATCH despesa manual).
- Telas React `GerenciaPage/ReceitasPage/DespesasPage` + `Gerencia.css`, menu no TopNav (admin).
- Parsers idempotentes em `v6/backend/scripts/`: `import_lib.py`, `import_controle_financeiro.py` (P2),
  `import_despesas_folder.py` (P4), `import_despesas_gerais.py` (P5). P1 = SQL direto.
- Fontes: ver o spec (CONTROLE FINANCEIRO.xlsx, pasta DESPESAS, DESPESAS GERAIS.rar, financeiro 2009-2012.zip).

## Aprendizados críticos
- **Deploy via docker cp, NÃO rebuild** — ver [[deploy_vps_docker_cp]] (contexto de build está quebrado).
- **created_at/updated_at NOT NULL sem default** no INSERT raw → setei `DEFAULT now()` em receita/despesa.
- Constraint `UNIQUE(origem, origem_ref)` precisa existir p/ `ON CONFLICT` (receita via model; despesa via ALTER).
- **openpyxl read_only**: NUNCA indexar `ws[r]` em loop (O(n²)); usar `iter_rows(values_only=True)` streaming.
- **CONTROLE FINANCEIRO.xlsx**: header linha ~22, receita = coluna VALOR DEP (depósito real), abas por ano; usar `data_only=True`.
- **DESPESAS GERAIS** é matriz categoria×setor com **RATEIO** (ADM GERAL distribuído em ENG/CONTABIL/DNA) →
  somar TODOS os setores conta 2×. Correto: somar só setores operacionais (excluir ADM GERAL/TÉCNICO/TOTAL).

## Extratos bancários: ✅ IMPORTADOS (26/07) — 570 extratos, 44.442 lançamentos (2012-2026)
- Tabelas `extrato_bancario` + `lancamento_bancario`; visível em **Conciliação Bancária** (Admin → Conciliação; API `/api/v1/financeiro/extratos`).
- Fontes: pasta `.../FINANCEIRO/EXTRATO/` (765 arquivos). Parsers: `import_extratos_ofx.py` (138 OFX, 13k lanç, estruturado),
  `import_extratos_csv.py` (28 CSV, 1981), `import_extratos_pdf.py` (BB/Caixa regex data+valor+C/D, 419 extratos/29k lanç),
  `import_extratos_pdf_bradesco.py` (posicional colunas CRÉDITO/DÉBITO, DD/MM/YY).
- Bancos: BB 356/28980 · Inter 79/10517 (via OFX) · Caixa 111/2708 · Bradesco 11/49 · CSV 1981.
- ⚠️ **Inter: só via OFX** — os 80 PDFs do Inter são DUPLICATAS (mesmas transações) → NÃO parsear PDF do Inter (dobraria).
- Idempotente: unique `extrato_bancario.arquivo_path` + delete-before-insert dos lançamentos.
- Ampliado 26/07 (/loop): **580 extratos, 45.721 lançamentos** (créditos R$112,8M / débitos R$66,6M). Inter mudou de layout
  4×: OFX (padrão) + PDF BR-linha ('R$ 280,00'/'-R$..') + PDF US-linha ('R$ 90.98') + PDF agrupado-por-dia ('31 de Março de 2023' + linhas).
  Parsers `import_extratos_inter_pdf.py` (tenta linha e agrupado) + `import_extratos_inter_csv.py`. Dedup por competência (não dobra OFX).
- Restante ~60 arquivos: redundantes (Inter já no OFX, outro formato) ou **escaneados** (2023-04/05/06/10 Inter = imagem, 12 chars;
  OCR de tabela inteira de transações é inviável/não-confiável). Sem perda real de dado único.
- tipo credit/debit: indicador C/D no BB/Caixa (autoritativo); sinal/palavra-chave no Inter. **Revisado 26/07**.
- 🐛 **BUG achado+corrigido na revisão**: `pdftotext -layout` renderiza "SALDO" do BB como "S A L D O" (espaçado);
  essas linhas de saldo viravam crédito falso (até R$1,4M cada) = **R$39,4M de créditos inflados**. Fix: regex
  `s\s*a\s*l\s*d\s*o` nos parsers PDF. **Totais corretos: 45.452 lançamentos, créditos R$73,4M / débitos R$66,2M** (equilibrado por banco).

## Conciliação + Classificação: ✅ FEITO 26/07 (goal god mode)
- **Rulebook**: `v6/docs/REGRAS-FINANCEIRO.md` (formas liquidação/pagamento, recorrência, conta ipc/externo, NF, regras, agendas).
- **Conciliação automática**: casa lancamento_bancario ↔ receita(crédito)/despesa(débito) por valor exato + data (±5d score 1.0,
  ±15d 0.7, sem-data mesmo mês 0.5). **12.611/45.452 = 27.7%** casados. Colunas `receita_id`/`despesa_id` em lancamento_bancario.
  Visível: barra no dashboard Gerência (clica → Conciliação Bancária) + endpoint `/api/v1/gerencia/conciliacao/resumo`.
- **Classificação**: campos em despesa (recorrencia avulsa|mensal, forma_pagamento, conta ipc|externo, tem_nf) e receita
  (forma_liquidacao a_vista|parcelado|conta_unica|ao_final, forma_pagamento, conta, tem_nf). UI inline na tela Despesas (dropdowns salvam via PATCH).
- **Regras**: tabela `regra_financeira` (tipo despesa_recorrente|rateio_honorario|terceirizado|conveniado; valor_mensal, percentual,
  dia_fechamento, dia_pagamento, paga_dia_util). Seed: Terceirizado (fecha 20/paga 15) + Conveniado (fecha último dia/paga 5º útil). Endpoint `/gerencia/regras`.
- ✅ **UI Receitas** (classificação inline à vista/parcelado/conta única/ao final + forma + conta) FEITA.
- ✅ **Regras + automação** FEITAS: página `/gerencia/regras` (CRUD), endpoint `POST /gerencia/regras/{id}/gerar?ano=` gera
  12 despesas mensais (origem='regra', dedup origem_ref). Testado: Aluguel Sede R$8.500 → 12 despesas 2026.
- ✅ **Nada de fora — extratos**: 708 arquivos registrados (todo statement no sistema); scaneados Inter recuperados via
  **OCR** (pdftoppm -r250 + tesseract --psm 6 → parse Inter daily): +685 lançamentos (2023-04/05/06). `import_extratos_inter_ocr.py`.
- **Totais finais: 708 extratos, 46.137 lançamentos, conciliação 12.714 (27,6%).** 124 só-registro = redundantes Inter (dado já via OFX).

## Persistência: ✅ RESOLVIDA (26/07) — ver [[deploy_vps_docker_cp]] (docker commit + compose aponta p/ imagem).
⚠️ Fiz docker cp+commit ANTES dos extratos? Não — extratos são só DADOS (banco/volume, persistente). Código dos parsers está no repo/scripts. Backend não mudou.

## Falta (long tail bespoke, ROI decrescente)
- **Despesa 2007-2010**: formato mais antigo (aba única anual "CONTROLE DE DESPESAS GERAIS 2008", sem meses) — parser próprio.
- **Despesa 2024-2026 valores**: 1084 registros na pasta DESPESAS têm data/descrição mas valor NULL
  (valor dentro do PDF/HTM). Extração via Qwen (routerclaude) — job grande por-arquivo. **Maior valor restante.**
- **P6 recorrentes**: IPC Debitos.xlsx (impostos: Pis/Cofins/CSLL por mês) + Unimed (mensalidade/colaborador) — layouts bespoke.
- Receita 2025 (sem aba no master).
- LibreOffice converte .xls: `/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to xlsx`
  (⚠️ macOS não tem `timeout`; arquivos 130MB são inflados mas convertem ~2min).

Relacionado: [[import_projuris_projetocp_feito]], [[deploy_vps_docker_cp]].
