---
name: oficios-fluxo-honorarios
description: Blueprint do fluxo de ofícios/honorários do IPC (proposta→impugnação→ratifica/declina) decodificado dos MODELOS_TEMPLATE; base do workflow automático
metadata:
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Ofícios & ciclo de honorários — blueprint do workflow (estudado 10/07)

Acervo: `IPCMS - ARQUIVOS/OFÍCIOS` = **69.963 arquivos** (instâncias reais .docx+.pdf).
Templates canônicos em `IPCMS - ARQUIVOS/MODELOS_TEMPLATE` (~25) e `MODELOS/`.
Nome do arquivo: `NNNN.AA.ÁREA.JD.NN-TT` — **NNNN**=nº do CASO; **AA**=ano; **ÁREA**=código
{10=contábil, 40=grafotécnica…}; **JD**=judicial; **NN**=nº do ofício NAQUELE MESMO caso
(=quantas vezes já atuamos: 01=proposta, 02, 03, 04=4ª interação); **-TT**=código do PRESTADOR
que fez (Bruno=47, Letícia≈57). ⚠️ Padrão mudou em 2025 — ofícios de 2024 vêm em outra forma.
→ Motor: o **NN** é o contador do ofício sequencial por caso (incrementa a cada novo ofício);
o **-TT** dá a autoria (útil pro timesheet/atribuição). Placeholders nos templates: `{{NUMERO_OFICIO}}`,
`{{JUIZ}}`, `{{VARA}}`, `{{COMARCA}}`, `{{NUMERO_PROCESSO}}`, `{{REQTE}}`, `{{REQDO}}`, `{{OBJETO}}`,
`{{VALOR_HONORARIOS}}`, `{{VALOR_MAJORADO_EXTENSO}}`. Cabeçalho fixo IPC (CNPJ 00.920.892/0001-49 e
14.424.142/0001-90, CREA-MS 1.100, art. 466 CPC, Diretor Bruno Boiko).

## Para o Bruno "ofício" = proposta + ofício + contrato (tudo junto). Ele NÃO é advogado,
não tem carteira de clientes — mas quer **alerta de IMPEDIMENTO**: "essa parte já foi meu
cliente/parte em outro processo → não posso ser perito do juízo" (CPC 148/467). Cruzar partes
entre processos e avisar.

## O CICLO (fluxo #5 que o Bruno quer automático — "o mais mastigado possível")
1. **Intimação** chega → classifica **área** (Qwen) → gera **PROPOSTA** de honorários (template
   "PROPOSTA JUDICIAL - PEDE MAJORAÇÃO AO FINAL": dá ciência do valor arbitrado, diz que está
   abaixo do mercado, **requer majoração** para valor X).
2. Ofício **revisado e aprovado** (humano) → **protocolo automático** (A3 Windows) → **guarda o comprovante**.
3. Depois vem **nova intimação** (provável **impugnação de honorários** OU "pagamento só ao final
   pela sucumbente").
4. **DECISÃO pelo HISTÓRICO do juiz + % de redução:**
   - Juiz que **"nunca manda"** (não homologa/paga) **OU** reduziu **≥10%** da proposta → **DECLINA**
     (template "DECLINA AO FINAL": recusa o encargo — fundamento: honorários ao final são reduzidos
     em instância superior sem notificar o perito, e homologação/pagamento não se cumprem →
     insegurança jurídica). Gera o **ofício sequencial** de declínio → **protocola**.
   - Redução pequena / juiz que paga → **RATIFICA** (template "OF padrão ratifica honorários":
     analisa a impugnação e sustenta os honorários — dimensionados pela complexidade, não vinculados
     ao valor da causa; reduzir desestimula peritos de qualidade). → protocola.

## ✅ Motor de DECISÃO — LIVE (10/07, testado E2E)
`models/fluxo_honorarios.py` (HistoricoJuiz) + `services/fluxo_honorarios.py` + `routes/fluxo_honorarios.py`
(`/api/v1/fluxo-oficio/decidir|juizes|juiz/registrar|juiz/{id}/nunca-paga`). Regra confirmada nos 4
cenários: proposta→PROPOSTA(NN01); impugnação corte ≥10% OU juízo "nunca paga"→DECLINA; corte <10%
→RATIFICA; pagamento ao final→DECLINA. NN = qtd de Oficio do caso + 1. `registrar_atuacao` acumula
o histórico do juízo ao longo do tempo. LIMIAR_REDUCAO=10% (ajustável). Retorna qual template usar.

## ✅ GERAÇÃO do ofício preenchido — LIVE (10/07, testado E2E)
`services/oficio_honorarios.gerar_oficio_honorarios()`: motor decide → abre o template real do IPC
(`app/templates/honorarios/{proposta,ratifica,declina}.docx`, copiados do MODELOS_TEMPLATE) →
preenche placeholders via `valores_do_processo`+`_preencher_documento` (JUIZ/VARA/COMARCA/AUTOS/
OBJETO/VALOR/EXTENSO; NUMERO_OFICIO=`CASO.AA.AREA.JD.NN-PRESTADOR`) → salva docx em
`/data/storage/oficios/{cnj}` → cria Oficio. `num2words` p/ valor por extenso. Rotas: POST
`/fluxo-oficio/gerar`, GET `/fluxo-oficio/oficio/{id}/download`. Testado: proposta NN01 +
impugnação 16,7%→declina NN02, zero placeholder pendente, NN incrementa sozinho.
⚠️ Qualidade depende do dado do processo (juiz/vara/partes) — processos com dado ruim do Qwen saem ruins.

## ✅ ENCADEAMENTO intimação→gera→aprova→protocolo A3 — LIVE (10/07, testado)
- Backend: `/fluxo-oficio/pendentes` (fila), `/oficio/{id}/aprovar` (→ status protocolo_enfileirado +
  enfileira Job `protocolo_oficio` com `arquivo_path`+`converter_para_pdf`), `/oficio/{id}/reprovar`.
  O report-back já existente (jobs.py) grava `numero_protocolo`+status `protocolado` quando o agente conclui.
- Front: **`/ferramentas/oficios`** (OficiosPage) — form Gerar + fila "Aguardando aprovação"
  (Revisar .docx / Aprovar→protocola / Reprovar). Card na Ferramentas.
- **Agente Windows** (`agente_perito.py` na pasta ESAJ): agora **converte DOCX→PDF** (docx2pdf→Word COM)
  antes de protocolar (eSAJ exige PDF). ⚠️ Windows precisa de `pip install docx2pdf` (ou Word instalado).
- Testado E2E até o A3: gera NN03 → pendentes → aprova → job 414 `protocolo_oficio` na_fila (o A3 real
  roda quando o Bruno liga o `agente_perito.py` no Windows). Ciclo do NN sequencial confirmado (05/06/07→NN03).

## ✅ HISTÓRICO DOS JUÍZOS montado (varredura noturna 10-11/07, Qwen local)
2.168 ofícios varridos → **370 juízos** (chave comarca+vara), **21 ⛔ NUNCA_PAGA** (≥3 declínios):
ex. Vara Única Inocência (104 atuações, 10 declínios), 2ª Vara Nova Andradina (8), Água Clara,
Itaporã, Cassilândia. O motor agora **declina automático** nesses juízos. Alguns saíram com vara "?"
(qualidade menor num punhado — refinável). Script resiliente/resumível: `scratchpad/juizos_madrugada.py`.

## O que falta pra construir (#5) — próximas fases
- **Histórico do juiz** (tabela: por juiz/vara — costuma homologar? paga? reduz? %). Alimentar com os
  dados dos 69.963 ofícios (Qwen categoriza em lote — routerclaude) + resultados reais.
- Motor de workflow que encadeia intimação→proposta→(protocolo)→impugnação→decide→declina/ratifica.
- Reusar `oficio_generator`/`create_oficio_templates` (já existem) + agente de protocolo A3 (Windows).
- Cálculo de honorários: `MODELOS/000 - TABELA CALCULO PERÍCIA.xlsx`.

## Restrições ditas pelo Bruno
- Funil/CRM só se integrar e-mail + **WhatsApp SEM bloqueio da Meta** → exige **API oficial WhatsApp Business**.
- Portal do cliente: ainda não sabe como encaixar (deixar pra depois).
Relacionado: [[acervo-laudos-onedrive]], [[diario-captacao-oportunidades]], [[esaj-automacao-existente]].
