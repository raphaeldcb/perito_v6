---
name: diario-captacao-oportunidades
description: Feature de captação por Diário (DJEN) — busca + análise Qwen + oportunidades; JÁ CONSTRUÍDA e verificada funcionando 10/07
metadata:
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Diário (DJEN) → Captação de oportunidades — ✅ VERIFICADO FUNCIONANDO (10/07)

Feature de "buscar serviço pelos diários dos TJs com análise + inclusão/exclusão" **já estava
construída ponta a ponta** e foi testada ao vivo (agent-browser + API) — funciona:
- Busca DJEN real (`services/diario_djen.py`, API `comunicaapi.pje.jus.br`) → 100 pubs no teste.
- Análise pelo **Qwen** (job `analisar_captacao` → `mac_agent` executa) → cria `Oportunidade`
  com área, resumo, ressalvas, advogado+OAB, defensoria/empresa_grande/oab_antiga, mérito
  sem×com perícia (%), `oportunidade` (bool) e **score** (ranqueia). Testado: job 90 concluiu em
  ~78s e criou 3 oportunidades; o Qwen acertou marcar como NÃO-oportunidade casos onde o IPC
  já é o perito nomeado (score negativo).
- E-mail ao advogado: job `rascunho_email_captacao` (Qwen redige).
- UI `pages/DiarioPage.jsx`: incluir/excluir termos, tribunais, Buscar, Salvar termos,
  Analisar oportunidades, painel ranqueado, gerar e-mail, descartar.
- Rotas `routes/diario.py`: /config, /consultar, /sincronizar, /analisar-captacao,
  /oportunidades, /descartar, /gerar-email.

## Config semeada (10/07)
incluir: nome do escritório (INSTITUTO DE PERICIAS CIENTIFICAS, IPC MS) + especialidades
(perícia grafotécnica/contábil/engenharia/médica). excluir: arquivado, trânsito em julgado,
baixados os autos. tribunais: TJMS, TJMT. (Ajustar termos = decisão de estratégia do Bruno.)

## Gaps / refinamentos (A DECIDIR com Bruno)
1. **Estratégia de busca**: buscar pelo nome do escritório acha casos onde o IPC JÁ é perito
   (rastreio), não leads novos. Pra captar SERVIÇO novo, mirar termos de necessidade de perícia.
2. **Automação total**: o worker (`workers/main.py`) roda `consultar_e_salvar` a cada ciclo
   (salva pubs como intimação), MAS não dispara sozinho a análise de captação — hoje é 1 clique.
   Se quiser hands-off, wire o loop p/ enfileirar `analisar_captacao` das novas (cap de volume,
   Qwen é lento). Relacionado: [[status_fluxo_completo_20260709]], [[perito_qwen_modelo]].
3. Cosmético: Qwen às vezes formata OAB repetida ("8586/8586/MS") — ajuste de prompt no
   `executar_analisar_captacao` do mac_agent.
