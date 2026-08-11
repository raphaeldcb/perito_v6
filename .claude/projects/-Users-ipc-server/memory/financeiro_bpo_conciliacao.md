---
name: financeiro-bpo-conciliacao
description: Módulo financeiro/BPO — ingestão de extratos+despesas (PDF) e conciliação por valor corrigido; plano + regra + índice
metadata:
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Financeiro / BPO + Conciliação (plano, 10/07)

Fonte: OneDrive `IPCMS - GERENCIA/FINANCEIRO` — `EXTRATO/` (538 PDFs, por ano 2012→2026),
`DESPESAS/` (989 PDFs 2024→2026), CONTROLE FINANCEIRO.xlsx, IPC Debitos.xlsx.
Já existe no v6: `models/financeiro.py` (ExtratoBancario, LancamentoBancario) + `services/conciliacao.py`
(casa por NOME do favorecido). O NOVO é conciliar por VALOR corrigido ↔ processo.

## ⚠️ LIÇÃO (11/07): DeepSeek nuvem NÃO serve p/ lote grande
Varredura noturna de 530 extratos com DeepSeek/NVIDIA → **342 erros (429 rate limit + timeout)**,
só 80 ok. A NVIDIA rate-limita chamadas seguidas. **Correto p/ LOTE = Qwen LOCAL** (sem limite,
GPU livre após o job dos juízos). Reprocessado com `perito-qwen`. DeepSeek fica p/ 1-poucas chamadas.
Resultado local em `scratchpad/extratos_resultado.json` (não tocou produção).

## ✅ Demonstrado (routerclaude): DeepSeek faz o braçal
DeepSeek V4 Pro leu um extrato BB (PDF) e estruturou as ENTRADAS (data/valor/descrição/proc).
Ex.: 5 entradas de um extrato 2025. É o "braçal pros grátis" que o Bruno pediu.
⚠️ Muitos extratos podem ser escaneados (sem texto) → precisam de OCR (pipeline do mac_agent).

## Regra de conciliação (do Bruno, formalizada)
Sistema "cego" que procura só o valor original FALHA: perícia de 1500 em 2015 pode entrar como
~2156,89 (corrigido). Então: **corrigir o honorário da DATA DA PROPOSTA até a DATA do crédito**
e casar por valor±tolerância.
- Índice: **IPCA-E** como primário (correção monetária judicial mais comum; bate no exemplo:
  1500 × ~1,44 ≈ 2160 ≈ 2156,89). Opcional testar SELIC (pós EC 113/2021, embute juros+correção).
  Já há `services/calculo_atualizacao` (IPCA/SELIC/INPC + juros) e `indices_bcb` p/ reusar.
- Score = 1 − |V − V_esperado|/V_esperado; casa se |dif| ≤ ~12%. Bônus se a descrição traz o nº CNJ
  (BB/CEF às vezes trazem; **Inter não informa**) → casa direto.
- Caso "1499 p/ 1500 de 2015": V≈original mas a proposta é ANTIGA → V_esperado corrigido ~2160 →
  1499 fica MUITO abaixo → score baixo → NÃO casa com esse caso antigo (é outro, recente). ✔ a intuição.

## Fonte de verdade: Conta Única TJMS ([[conta-unica-financeiro]], acesso já salvo)
Lista alvarás pagos com **processo + valor + data** → é o elo ouro pagamento↔processo. Cruzar:
extrato (crédito ~Y em ~Z) ↔ Conta Única (processo X pagou Y em Z) ↔ honorário esperado corrigido.

## Regras de classificação das transações (Bruno, 11/07) — p/ filtrar o "ruído" dos 19,7M
- Transferência p/ **Bruno** ou **Daniel** (ex-sócio) → **pró-labore**.
- **Aplicação** → categoria "aplicação".
- Transferência **Perícia → Pesquisa** (as 2 empresas do grupo) → **empréstimo entre empresas**.
- O resto que não é tamanho de honorário → não é receita de perícia (a conciliação por valor filtra).
Bruno pediu: **esperar a extração terminar** e AÍ rodar a conciliação/categorização.

## Tarefa grande FUTURA: conciliar LAUDOS × pagamentos
Acervo `IPCMS - ARQUIVOS/LAUDOS` = 38.652 arquivos em pastas `caso.ano.área.JD.NN` (nome=caso).
Objetivo: casar cada laudo (perícia feita) com o pagamento (Conta Única/extratos), **principalmente
os "AO FINAL"** (pagos pela sucumbente no fim). Quem tem **"Karyna Hirano"** (advogada que faz as
COBRANÇAS) = caso em cobrança/não pago. Fazer na FILA com Qwen/DeepSeek **sem atrapalhar** os jobs
atuais. Nota técnica: "Karyna" e "ao final" acham-se melhor por BUSCA de texto (grep) que por Qwen;
Qwen/Deep p/ o que for fuzzy (área/honorário). Inventário dos casos = pelos nomes das pastas (rápido).
**Nomenclatura dos laudos (Bruno, 11/07):** ANTIGO = `L#####` (nº do laudo) + "CASO #####" (id interno),
guardados em pastas por ANO (2014-2024, ~2.300 arquivos). NOVO = pastas `caso.ano.área.JD.NN` (2025+).
Inventário de pastas a varrer = 1.730 (1.705 casos novos + 11 pastas-ano antigas). O `CASO #####` e o
CNJ (dentro do doc) são as chaves p/ casar laudo↔pagamento. Accurate (perito-qwen) mantido na extração.

## Mapa dos dados (corrigido 11/07 — onde cada coisa VIVE)
- **Karyna Hirano (advogada de cobrança)**: NÃO está no CONTROLE nem nos laudos (0 menções). Ela é
  a **advogada, só na CAPA dos AUTOS**. Temos **114 autos** baixados (intimacoes_baixadas). Fonte extra:
  a captação DJEN já extrai `advogado_nome`. → grep de Karyna nos laudos foi CANCELADO (inútil).
- **AO FINAL**: coluna existe no **CONTROLE FINANCEIRO.xlsx** (agregado) + nos ofícios ("ao final"/declina).
- **CONTROLE FINANCEIRO.xlsx** = ouro: 16 abas por ano (2013-2024, 2026) + colunas SETOR, NÚM PERÍCIAS,
  CARTÃO/CHEQUE/DINHEIRO/GRATUITO, CEF/BB/BRADESCO, **AO FINAL**, COLETADOR, DNA/CON/ENG/DOC, TOTAL
  ENTRADA/DESPESA, SALDO, CIDADE/ESTADO, DATA CADASTRO. É o controle real de entradas — parsear (xlsx, sem Qwen).
- **IPC Debitos.xlsx** = impostos/despesas (Pis/Cofins/CSLL/IRPJ/ISS/INSS prolabore/Maed).

## TAREFA LONGA (fds/madrugada): processo → baixar → analisar → retornar
Bruno: pra achar Karyna/ao-final/honorário de VERDADE, tem que **entrar em cada processo, baixar
os autos, analisar e retornar**. Pipeline de 2 estágios entre máquinas:
1. **BAIXAR** (eSAJ) = **Windows (A3) ou VPS** — NÃO no Mac (Selenium não roda no Mac). Loop nos
   **1.281 processos com CNJ**, reusando a lógica do `intimacoes_v7`/`baixar-autos-esaj`. Bruno roda no fds.
2. **ANALISAR** (Mac GPU/Qwen) = lê 1ªs+últimas páginas do auto → {advogados, tem_karyna, ao_final,
   honorário, resumo} → retorna pro processo.
3. **PILOTO** já enfileirado: `autos_analise.py` nos 114 autos que já temos (prova o fluxo + acha Karyna
   no que existe), roda após extratos+despesas. Resultado em `scratchpad/autos_analise.json`.
A FAZER: montar o loop de download Windows (lista dos 1.281 CNJs) + o push da análise pro processo.

## ESTEIRA DO FIM DE SEMANA (autônoma, detached, sáb→seg — 11/07)
Rodando sozinha (scratchpad/, nohup, resumível, resiliente):
1. `extratos_local.py` (Qwen) → entradas → `push_loop.sh` ingere no BD (idempotente).
2. `fila_supervisor.sh` → `despesas_local.py` (Qwen) quando extratos acabar.
3. `autos_supervisor.sh` → `autos_analise.py` (Qwen: advogado/Karyna/ao-final) após despesas.
4. `rag_supervisor.sh` → `rag_indexer.py`: indexa o acervo de LAUDOS no RAG (nomic 768d, pgvector,
   origem="laudo", ref_id=pasta). **Depois** da esteira Qwen (nomic × perito-qwen brigam no Ollama).
   ⚠️ ref_id do RAG virou TEXT (era int → 422). Testado: 2 laudos → 13 chunks. RAG estava VAZIO.
⛔ Download eSAJ em massa PAUSADO (instável — "nova aba" flaky; não martelar TJMS). Revisitar com calma.
✅ BD intacto (aditivo, nunca zera). Merge futuro c/ sistemas antigos = por chave, sem sobrepor/deletar s/ certeza.
⛔ NÃO criar contas/API keys de IA sozinho (ToS/impersonation) — Bruno passa as keys. Recursos free atuais bastam.

## Plano (fases)
1. Ingestão extratos: DeepSeek/Qwen (+OCR p/ escaneados) → LancamentoBancario.
2. Ingestão Conta Única (Selenium, sem A3) → pagamentos por processo (ground truth).
3. Motor de conciliação por valor corrigido (IPCA-E) + regra acima → sugere match extrato↔processo.
4. Despesas: extrair → contas a pagar/BPO.
Relacionado: [[claude-code-router-ccr]] (DeepSeek=braçal), [[conta-unica-financeiro]].
