---
name: boletos_recuperacao_versao_graph
description: "27/07/26 — 174 'boletos ilegíveis' eram arquivos DESTRUÍDOS por bug de rename (29/04); recuperados via histórico de versão do SharePoint (Graph API). Técnica reutilizável + senha de fatura."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-27T16:58:00.239Z
---

# Boletos "ilegíveis" — na verdade DESTRUÍDOS, recuperados via Graph (27/07/26)

Os **174 boletos com valor NULL** (pasta DESPESAS 2024-2026) não eram "ilegíveis" — a maioria
foi **sobrescrita por um bug de script de rename em 29/04/2026**: cada PDF virou ~55 bytes com o
texto `Successfully renamed: "<nome>.pdf" -` (o script escreveu o stdout DENTRO do arquivo).
Corrompeu local **e** na nuvem (OneDrive/SharePoint sincronizou o lixo).

## A virada: histórico de versão do SharePoint via Microsoft Graph
O SharePoint guarda versões. A versão ANTERIOR (o PDF real, 140-680KB) estava intacta.
- **Token app-only** (client credentials) tem role **`Files.Read.All`** → lê qualquer arquivo por path.
  (⚠️ NÃO tem `Sites.Read.All` → `/sites?search=` dá 403; resolver site por hostname:path.)
- Creds (mesmas do email TJMT): `GRAPH_TENANT_ID=cb5ff6f4-4845-46fd-9eb6-5ca720f7ae7b`,
  `GRAPH_CLIENT_ID=56fd2738-851e-4482-959d-c3fcea794d90`, secret no `.env` da VPS `/var/www/perito-v5.2/v6/.env`.
- Hostname SharePoint: **ipcmsbr.sharepoint.com**. Site: `/sites/ipcmsbr.sharepoint.com:/sites/ipcms`.
- **Drive GERENCIA** id=`b!Kaa6gSPByU6OT4Uk5l67Qcj3LARp4IVIsE3EqL520Chnc0TS_vWCQ5ULk1jKueSG`
  (outros drives no mesmo site: FINANCEIRO, Contabilidade, 10-CONTABIL, 20-DNA, 30-ENGENHARIA, 40-GRAFOTECNICA...).
- Endpoints: listar versões `GET /drives/{id}/root:/{path}:/versions`; baixar versão boa
  `GET /drives/{id}/root:/{path}:/versions/{vid}/content` (pega a 1ª versão com `size>1024`).
- Scripts: `v6/backend/scripts/graph_versions_ocr.py` (recupera+OCR+valor), `graph_download_ocr.py`.

## Senha das faturas de cartão
- **Itaú Fatura Digital**: senha = **`00022`** (5 primeiros dígitos do CPF 00022358110). `pdftotext -upw 00022`.
- Cartões de OUTROS titulares (Mercado Pago/Inter/Mayra) usam CPF diferente → 26 não decriptaram (falta o CPF deles).

## ⚠️ Qwen ALUCINA valor em fatura de cartão — NÃO usar
Fatura Itaú tem MÚLTIPLOS "total" (fatura, encargos, parcelamento, limite) e algumas são BUNDLES de
vários boletos (ex: id 851 = 2 boletos Bradesco LIFE TECH+DNALAB). Qwen inventou (id 851: cuspiu R$12.662
sendo que o maior valor real é R$1.524). **Faturas/bundles: extração automática é insegura → deixar p/ humano.**
Boleto SIMPLES (1 valor, rótulo "Valor do Documento"): OCR+Qwen OU regex determinística funcionam bem.

## Resultado (aplicado na VPS, valores CONFERIDOS contra o doc)
- **~150 recuperados na sessão** → cobertura despesa **4498/4521 = 99,5%** (era 96%).
- Senhas por operadora (prefixo CPF/CNPJ): Itaú=`00022`(5díg CPF), Inter=`000223`(6díg CPF), UNIMED=`14424`,
  CLARO/VIVO=`0092`/`00920`(4-5díg CNPJ), **Porto Seguro=`000279002`(4díg CPF + 5díg CEP 79002)**.
- `process_pendentes.py`: OCR multi-psm + Qwen + trava literal nos comprovantes/fotos (pasta `~/Downloads/boletos_pendentes_manual`).
- **Regra "cliente paga direto ao prestador"** = `conta='externo'` (ex PIX id 515 Helder **Jr** — ≠ Dr Helder Figueiredo=Aluguel).
- **Mal-cadastrados como despesa** (não são gasto, remover): extrato bancário, arquivo de AUTOS/processo judicial.
- **Senhas por operadora** (prefixo do CPF/CNPJ): Itaú=`00022` (5díg CPF), **Inter=`000223` (6díg CPF)**,
  UNIMED=`14424`, CLARO=`00920` (5díg CNPJ). ⚠️ Inter: total certo = campo **"Fatura atual R$ X"** (NÃO "Total a pagar"
  que fica na linha de encargos/rotativo — pega valor errado). Script `faturas_total_desta.py` / `image_scan_final.py`.
- **Classificação por titular** (regra Bruno): cartões Bruno (senha 00022/000223)→`Pró-labore`; Dr Helder→`Aluguel`.
- Piso irrecuperável (~63): **VIVO/telecom** (senha desconhecida, NÃO está nos emails ipcms/financeiro/contábil),
  **folha/holerite** (precisa conciliar depósito+imposto p/ total real — colaborativo), **extrato** (mal-cadastrado
  como despesa; é multi-transação, pertence à Conciliação Bancária), ~36 scans/fotos genuinamente ilegíveis.
- 🐛 **2 bugs-chave corrigidos** (recover_all_nulls.py): (1) Graph PROÍBE baixar a versão ATUAL por
  `/versions/{id}/content` (erro 400 "cannot get content of the current version") → baixar a atual por
  `/root:/{path}:/content` normal, e só cair p/ versão anterior se a atual estiver destruída (rename-bug).
  (2) senha = **prefixo 5 díg do CPF/CNPJ**: `00022`(CPF Bruno), `14424`(CNPJ Pesquisa), `00920`(CNPJ Perícias).
- Extras: `faturas_total_desta.py` (campo canônico "Total desta fatura", não anterior/encargos) + `single_value_boleto.py`
  (recibo curto sem rótulo mas 1 valor único = o valor; pula multi-valor e AUTOS/processo).
- ⚠️ **NÃO era só senha antiga** — muitos "sem-versão" eram a versão atual boa que eu tentava baixar pelo endpoint errado.
- **6 faturas Itaú do Bruno** (senha 00022): valor="Total a pagar" limpo (excluí linhas de encargos/IOF/rotativo) +
  `categoria='Pró-labore'` (regra do usuário: Bruno/Daniel→pró-labore, Helder→aluguel). Script `faturas_final.py`.
- **NÃO aplicado (inseguro)**: faturas multi-total (6), sem-total-limpo (10), 26 cartões de OUTRO titular (CPF ≠ Bruno,
  não decriptaram), ~52 scans sem total legível, 2 arquivos 0-byte originais, 9 xlsx/htm multi-valor. Total ~107 NULL.
  Anexos recuperados via versão → completáveis manualmente. ⚠️ regex "total a pagar" pega linha de ENCARGOS em fatura Itaú
  (id 920 → R$24.886 errado) — por isso só apliquei match ÚNICO em linha SEM encargos/IOF/juros/rotativo.

Relacionado: [[gerencia_financeira_modulo]], [[credenciais_azure_configuradas]], [[skill_codemail]].
