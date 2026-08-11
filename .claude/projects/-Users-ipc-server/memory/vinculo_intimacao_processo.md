---
name: vinculo-intimacao-processo
description: Corrigido o bug recorrente intimação↔processo↔partes — cadastro auto-preenche do dados_estruturados do Qwen
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Integração intimação→processo→partes — CORRIGIDO E VERIFICADO NA UI (09/07/26, commit 08638ff)

Era o "resolve sem resolver" do Passo 1. Causa real: a análise do Qwen preenchia
`intimacao.dados_estruturados` (partes, vara, juiz) mas **nada ia para o processo** —
`processo.autor/reu/vara/juiz` ficavam vazios → processos viravam cascas na tela.

**Correção (UPDATE, não rebuild):**
- `backend/app/services/vinculo.py`: `classificar_partes()` (tolera formato do Qwen
  `{nome:papel, tipo:nome}` e `{papel,nome,doc}`) + `propagar()` que preenche
  autor/reu/vara/juiz/titulo/classe **só se vazio** (não sobrescreve edição manual).
- `jobs.py` (`_aplicar_resultado` analise_ia): propaga ao concluir → novos automáticos.
- `processos.py` `POST /api/v1/processos/reprocessar-vinculos`: backfill dos existentes
  E reconciliação de sistemas legados (Passo 2).
- `frontend/ProcessosPage.jsx`: linha da tabela mostra "autor × reu" sob o CNJ.

**Verificado na UI real** (agent-browser + screenshot): backfill preencheu 4/6;
lista e detalhe mostram partes (Bradesco × Energisa; IPC × Maria Martins). Os 2 sem
partes são intimações genéricas (listas/cartas).

**Ainda falta (não é esse bug):** colunas DOC/TIPO/ÁREA/RESPONSÁVEL/HONORÁRIOS/PRAZO
são dados do fluxo do perito (entrada manual/outros flows), não vêm da intimação.
Cadastro de partes MÚLTIPLAS (aba 👥 Partes usa array `partes`, mas modelo vivo só
tem autor/reu string) — enhancement futuro se quiser multi-parte com CPF/doc.

Regras aplicadas: [[feedback_nao_refazer_frontend]] (verificar na UI antes de dizer feito).
