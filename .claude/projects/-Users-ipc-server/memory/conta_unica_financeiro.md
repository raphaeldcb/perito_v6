---
name: conta-unica-financeiro
description: Integração futura TJMS Conta Única (alvarás/perícia paga) — credenciais salvas nos parâmetros; fonte do financeiro
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Conta Única TJMS — perícia paga (frente financeira, 10/07/26)

Site para acompanhar **alvarás / perícias pagas pela conta única** do TJMS — importante
para o **financeiro** (saber o que já foi pago).

**URL:** https://www5.tjms.jus.br/login/?forwardTo=/contaunica/alvara_listagem.php

**Credenciais salvas nos parâmetros do sistema** (tabela `parametro`, senha `secreto=true`):
- `conta_unica_login` = 54040/crbio-01
- `conta_unica_senha` = ••• (Bru@8411)
- `conta_unica_url` = (acima)
- `conta_unica_data_inicial` = 01/01/2015
- `conta_unica_situacao` = paga

**Fluxo que o Bruno usa (roteiro p/ automação futura):** logar → filtrar por
**data de expedição de 01/01/2015 até hoje**, **número do processo**, e **situação da
guia = "paga"** → listar os alvarás pagos. Isso alimenta o financeiro (conciliar
perícia recebida). Automação estilo eSAJ (Selenium), mas SEM A3 (login user/senha) —
pode rodar na VPS ou no Windows.

A FAZER: automação de scraping dos alvarás pagos + entrada no financeiro do Perito.
Relacionado: [[esaj-automacao-existente]] (padrão de automação Selenium).
