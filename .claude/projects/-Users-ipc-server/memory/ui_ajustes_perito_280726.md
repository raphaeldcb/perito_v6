---
name: ui_ajustes_perito_280726
description: "Revisão UI Perito v6 (28/07) — 7 ajustes do Bruno; itens 1,2,3,6 feitos em branch fix/ui-ajustes-perito; item 7 = campo área poluído (grande); itens 4,5 pendentes de input"
metadata: 
  node_type: memory
  type: project
  originSessionId: e7c45933-ce0e-4235-b3f8-5d8d1369984c
  modified: 2026-07-28T17:22:19.888Z
---

28/07/26 — Bruno passou 7 ajustes na UI do Perito v6 ("vai ajustando, chegando no ipc reviso").

**✅ FEITOS — branch `fix/ui-ajustes-perito` (commit 01d6673), NÃO deployado, build front OK:**
- **1 (formatação BR):** dashboard (`pages/Dashboard.jsx`) não usava o helper; agora usa `reais()` (util/format.js) → R$ 1.234,56.
- **2 (setores):** dropdown de setor da dashboard só tinha Contábil+Eng; agora os 6 (SETORES.md: Contábil/DNA/Eng/Grafo/Multi/Declina).
- **3 ("o que é 7,5s"):** era FAKE — `tempo_medio=7.5` hardcoded em `backend/app/routes/dashboard.py` (TODO nunca feito) numa caixa amarela sem rótulo. A seção de stats inteira era debug (divs coloridas "TEST:"). Troquei pelos `StatCard` reais + 4º KPI real = **Intimações Pendentes** (`Intimacao.status=='pendente'`).
- **6 (filtro despesas):** `pages/DespesasPage.jsx` ganhou barra de filtro client-side (busca + recorrência/forma/conta), reusando classes `ger-form`/`ger-sel`.

**🔴 7 (classificação de área) — GRANDE, o print revelou:** tela "Gestão de Valores → Honorários por área" (`backend/app/routes/valores.py:28`) agrupa por `Processo.especialidade`, campo texto-livre PODRE: `SIMPLES/simPLES/siMPLES` (caixa aleatória = buckets dup), `MÉDIO/COMPLEXO` (complexidade ≠ área!), lixo (`VARA ÚNICA`, `CAMPO GRANDE`, `2`, `14657`).

**✅ TAXONOMIA CANÔNICA ACHADA + EXTRAÍDA (28/07):** OneDrive está montado LOCAL no Mac (`~/Library/CloudStorage/OneDrive-BibliotecasCompartilhadas-IPCMSPERICIASLTDA/IPCMS - ARQUIVOS/MODELOS/Tabelas/`) — **sem precisar Graph/VPS**. Fonte = `TABELAS DE HONORARIOS 2026 -GERAL completa.xlsx`, aba **`TABELA`**: col A=SETOR, col B=CÓDIGO, **col C=Tipo de Perícia**, col D=referência cobrança. **105 tipos**: ADM 12, Contábil 30, Eng 38, Grafo 3, DNA 22. Ex DNA: PD0101=Mãe+criança+suposto pai, PD0201=criança+suposto pai, RD/RI/AM/VP/ES/2V/KIT/COL. Eng.01-40 (trânsito, imóvel, rural, dano ambiental, insalubridade Eng.15-16, elétrica, degravação, informática). Grafo.01-03. Extração salva em scratchpad `taxonomia_tipos_pericia.csv`. (Openpyxl no venv `backend/venv_perito`.)

**Item 7 — PARTE 1 FEITA (28/07):** `valores.py` agora agrupa "Honorários por área" por `Processo.setor` (limpo) em vez de `especialidade` (lixo). Populei `setor` (era 100% vazio) p/ **1620 determinísticos** (especialidade limpa + acervo): DNA 1063, Contábil 266, Eng 205, Grafo 84, Multi 2. Gráfico limpo, deployado (docker cp + re-commit v6-backend:consolidado-27jul). Excel `~/Downloads/classificacao_setor_processos.xlsx`.

**Item 7 — os 5300 restantes: NÃO há atalho barato (testado à exaustão):** especialidade=complexidade; acervo/laudo por nome de arquivo não tem CNJ (só 163/7613); L-code legado não bate com acervo (1%); import copiou area→especialidade (=lixo, migrar_legado.py:68); Qwen no texto do banco = **4/2415 (0,2%)** pq não há sinal nos campos. **DEFINITIVO: a área dos legados só existe no conteúdo do documento, e não há link limpo processo→documento.**

**🎯 MELHOR LEAD (aguarda resposta do Bruno):** cruzando `source_system` — **`projetocp` = 4722 sem classificação, TODOS graduados SIMPLES/MÉDIO/COMPLEXO = UM projeto/setor só.** Se Bruno disser qual setor é o ProjetoCP → resolve 4722 (68%) num UPDATE. Palpite: Contábil (revisão bancária). Os DNA (1063) etc. vieram do `projuris`.

**Task 2 FEITA (setor obrigatório no cadastro):** backend `ProcessoCreate.setor` sem default (obrigatório); frontend cadastro com dropdown de setor obrigatório; `sync_tjms.sh` manda `setor="Sem classificação"` p/ não quebrar. Deployado (backend+frontend dist+re-commit v6-frontend:gerencia-live). `saude`=15/15 VERDE.

**⏸️ 5 (coluna Setor em Processos):** `/processos` (processos.py) NÃO retorna setor por item; pronto p/ add coluna + serialização, mas depende de saber se `setor` está limpo em prod (mesmo bloqueio do 7).

**❓ 4 (Gerência "nada clicável"):** no código os cards Receita/Despesa JÁ navegam (cursor+hover) e conciliação também — perguntei ao Bruno se quer **drill-down** (setor/categoria/mês) ou se é bug de rota.

⚠️ Inconsistência a resolver: `processos.py` comenta setor como código "01/02", SETORES.md usa nomes — meu dropdown usa nomes; conferir valor real no banco antes de confiar no filtro.

Relacionado: [[setores_empresa]] · [[tipos_pericia]] · [[deploy_vps_docker_cp]] · [[feedback_nada_fake_producao]]
