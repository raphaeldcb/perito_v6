---
name: feedback_memoria_critica_20260713
description: Falha crítica em usar memória do projeto — ignoring existing scripts no Windows de Bruno
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 573b1971-d52b-45c7-967b-d22bf8b6d0a3
---

**ERRO CRÍTICO:** Hoje (13/07/26) tentei acessar TJMS via Python, agent-browser, HTTP — tudo errado.

**Realidade:** Bruno JÁ TEM `intimacoes_v7.py` + `protocolo_v21.py` funcionando no Windows dele com A3 + autenticação real. Está documentado em: [[Automação eSAJ JÁ EXISTE]]

**Por que errei:**
- Não li/usei a memória do projeto antes de agir
- Inventei soluções (agent-browser, regex parsing, simulações) em vez de usar o que EXISTE
- Fiz perguntas idiotas ("você acessa manualmente?") quando deveria ter simplesmente pedido: "roda intimacoes_v7.py"

**Regra nova:** 
Antes de QUALQUER ação:
1. LER memória do projeto (2 minutos)
2. Se ferramenta/script já existe → USE, não reinvente
3. Se é task do Windows → PEÇA para Bruno rodar, não tente no VPS/Mac

**Como aplicar:**
- Leia [[Automação eSAJ JÁ EXISTE]] SEMPRE que processo = TJMS
- Qualquer coisa com A3/certificado → Windows (Bruno)
- Pare de inventar HTTP requests / agent-browser hacks quando a solução já existe

**Custo:** 3 horas perdidas com "para bens".
