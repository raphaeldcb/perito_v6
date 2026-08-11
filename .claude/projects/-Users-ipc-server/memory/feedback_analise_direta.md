---
name: feedback-analise-direta-sem-inferencia
description: "Regra: nunca inferir dados de processo — sempre baixar autos reais, transformar em MD/JSON, depois analisar"
metadata:
  type: feedback
---

Nunca inferir dados de processo (partes, valores, escopo) sem acessar os autos.

**Why:** O usuário detectou que a proposta para 0800472-51.2017 usou estimativas (R$ 3.500, documentos necessários) sem acesso real ao processo. Isso é inaceitável em contexto pericial profissional.

**How to apply:**
1. Baixar autos completos do ESAJ via certificado A3 (não apenas PDF de intimação)
2. Transformar PDF em MD/JSON com agente estruturador (já existe: `analisador.py` ou agente dedicado)
3. Só então analisar com Ollama/IA e gerar proposta

Fluxo: ESAJ download → PDF → MD/JSON (agente) → análise → proposta
