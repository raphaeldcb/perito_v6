---
name: feedback_docx_template_imutavel
description: "Template DOCX é SAGRADO — só atualizar {{}} placeholders, ZERO mudanças de formatação"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d7666017-a728-4e1e-bf53-5b132199ec90
  modified: 2026-08-14T11:20:58.544Z
---

# 🔒 TEMPLATE DOCX — IMUTÁVEL

**Data**: 14/08/2026  
**Status**: CRÍTICO

## Regra de Ouro
Quando gerar/atualizar laudo em DOCX:

✅ **FAÇA**:
- Encontrar `{{campo}}` no documento
- Substituir APENAS o conteúdo dentro das chaves
- Preservar 100% da formatação original (fontes, cores, espaçamento, estilos)

❌ **NUNCA FAÇA**:
- Mudar fonte (Arial → Times, Calibri → qualquer coisa)
- Mudar tamanho
- Mudar cor
- Mudar espaçamento
- Reformatar linhas
- Tocar em cabeçalhos/rodapés
- Alterar estrutura do documento

## Problema Atual
- Bruno criou template com formatação específica
- Sistema está **mudando a formatação** ao gerar
- Resultado: laudo com problemas de apresentação
- Frustração: "Dei ordem EXPRESSA, só atualiza {{}}"

## Solução Técnica
Usar `python-docx` com **cuidado extremo**:

```python
from docx import Document

doc = Document("template.docx")

# Iterate paragraphs
for para in doc.paragraphs:
    for run in para.runs:
        if '{{' in run.text:
            # Replace ONLY text, PRESERVE all formatting
            run.text = run.text.replace('{{campo}}', 'valor_real')
            # run.font.* e run.style NÃO TOCAM

# Iterate tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    if '{{' in run.text:
                        run.text = run.text.replace('{{campo}}', 'valor_real')
```

## Checklist Antes de Deploy
- [ ] Abrir template original no Word
- [ ] Gerar novo laudo
- [ ] Comparar lado a lado: fontes, cores, espaçamento
- [ ] Se algo mudou → REVERT, investigar, corrigir código
- [ ] SÓ ENTÃO confirmar que está ok

---

## Relação com RAG + Referências
Template é o "esqueleto" do laudo. RAG deve preencher os `{{}}` com:
- Dados do processo (folhas, partes)
- Referências a laudos anteriores
- Padrão de escrita

Mas formatação = INTOCÁVEL.
