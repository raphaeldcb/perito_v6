---
name: a3-sessao-8h
description: "A3/protocolo roda no WINDOWS com WebSigner (NUNCA no Mac); autorização 1x vale 8h, reusar a mesma sessão"
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# A3 / protocolo — WINDOWS + WebSigner (regra do Bruno, corrigida 09/07/26)

⛔ **O A3 NÃO FUNCIONA NO MAC. NUNCA sugerir plugar A3 no Mac.** Bruno já disse isso
mais de uma vez — insistir nisso é o que mais o irrita.

✅ **Onde o protocolo funciona:** máquina **Windows** com **WebSigner** (extensão de
assinatura do eSAJ/Softplan) já instalado, e o **protocolo já funcionava lá**. Bruno
comprou o Mac e passou a desenvolver aqui (Claude Code), mas a execução do A3/protocolo
tem que ser no Windows.

**Sessão A3:** ao abrir o eSAJ/TJMS, o WebSigner pede autorização do A3; Bruno
autoriza **1x → vale 8h**. Regra: abrir UMA sessão e reaproveitar; **nunca fechar e
reabrir** (cada reabertura força nova autorização). 8h dá de sobra p/ tudo.

**Arquitetura correta:** sistema web acessível de qualquer lugar (VPS) → ações de A3
(protocolar, receber intimações) são delegadas para a **máquina Windows** com WebSigner,
que mantém a sessão de 8h e executa. O Mac é só desenvolvimento.

**Estado:** protocolo real ainda não religado no sistema novo (estava simulado/gate
PROTOCOLO_AUTOMATICO_ATIVO). Próximo: agente no Windows que reusa a sessão WebSigner+A3.

CORRIGE a memória antiga [[feedback_selenium_nao_funciona]] (que dizia "usar VPS" —
a VPS serve para o headless, mas o A3 assinado é no Windows).
