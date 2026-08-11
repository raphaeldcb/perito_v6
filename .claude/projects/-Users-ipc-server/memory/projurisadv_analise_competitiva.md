---
name: projurisadv-analise-competitiva
description: Raio-x do ProjurisADV (concorrente) feito no login do Bruno — features que faltam no Perito v6 e onde o Perito já ganha
metadata:
  type: reference
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# ProjurisADV — análise competitiva (10/07, login do Bruno via agent-browser)

Menus: GESTÃO · ATIVIDADES · PROCESSOS · FINANCEIRO · DOCUMENTOS + agenda + "Projuris IA com ChatGPT".
Sub-features vistas:
- PROCESSOS: andamento-processual, **central-captura (Monitoramento Push, por CRÉDITOS pagos)**, intimações, processo, relatórios.
- FINANCEIRO: extrato, receita-despesa, solicitações, relatórios.
- DOCUMENTOS: listagem + **modelos-documento** (biblioteca de templates).
- ATIVIDADES: kanban, lista, **painel-tarefas**, relatórios.
- GESTÃO: **atendimentos (intake/CRM)**, **contratos (honorários)**, dashboard, **pessoa/lista-pessoas (CRM)**, **timesheet (horas)**, relatórios.
- Config: Área do cliente (**portal do cliente**), Cadastros Gerais, Config. Notificação, Personalização/branding, Importação de Dados, Registro de Acesso (audit), **Workflow** (automação de etapas).

## Ideias que FALTAM no Perito v6 (worth stealing) — priorizado
1. **Timesheet / apontamento de horas** por perícia → alimenta honorários e produtividade.
2. **Contratos de honorários** (gerar/guardar/cobrar, vincular ao processo).
3. **Atendimento/funil** ligando as Oportunidades (captação) → lead → contatado → contratado.
4. **Portal do cliente/advogado** (estender o ColetadorPortal): o advogado do lead recebe link e vê status.
5. **Workflow configurável** (etapas por tipo de caso) — hoje o Perito tem fila de jobs fixa.
6. **Biblioteca de modelos de documento** (além de ofício/laudo).
7. **Relatórios dedicados** por módulo (hoje só o dashboard Valores).

## Onde o Perito JÁ GANHA
- IA: Qwen local + Fable (privado, sem custo por uso) vs "Projuris IA com ChatGPT" (nuvem, metered).
- Captação: DJEN **grátis + análise Qwen** (área/mérito/advogado/score) vs Push por créditos pagos.
- Especialização em PERÍCIA: vistorias de engenharia (PWA), cadastro DNA, geração de laudo,
  deslocamento c/ pedágio, análise forense de mídia — ProjurisADV é jurídico genérico.

⚠️ Senha do ProjurisADV foi colada no chat (1234adv) — recomendei trocar.
