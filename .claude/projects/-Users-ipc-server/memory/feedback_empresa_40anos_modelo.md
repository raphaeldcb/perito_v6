---
name: feedback_empresa_40anos_modelo
description: "Empresa de 40 anos — modelos, estética e conhecimento são SAGRADOS. Sistema serve o trabalho, não inventa."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d7666017-a728-4e1e-bf53-5b132199ec90
  modified: 2026-08-14T11:35:07.330Z
---

# 🛡️ Empresa de 40 Anos — Respeitar o Modelo

**Data**: 14/08/2026  
**Contexto**: Aprovação arquitetura pipeline de laudo  
**Status**: CRÍTICO PARA TODO DESENVOLVIMENTO

---

## Regra de Ouro

Sistema **SERVE** o trabalho estabelecido. Não inventa, não muda, não "melhora".

### 1️⃣ Nunca Limitar Entrada
- Não dizer "tome apenas esses 4 campos"
- Flexibilizar: se precisa 20 campos, suporta 20
- Se precisa dados manualmente inseridos (planilhas contábeis), aceitar e preservar
- Arquitetura: extensível, não restritiva

### 2️⃣ Respeitar Padrões Manuais (Até Automação Chegar)
**Exemplo**: Contábil depende de planilha manual
- RAG busca laudos contábeis anteriores para estrutura
- MAS: Se não houver padrão automatizado, permitir input manual
- Futura ferramenta de cálculos vai automatizar isso
- Até lá: Sistema acomoda, não força

**Fórmula**:
```
RAG (busca padrão) + INPUT MANUAL (dados específicos) 
+ FERRAMENTA FUTURA (automação) = Perfeito
```

### 3️⃣ SEMPRE Preservar Formatação 100%
- Arial permanece Arial, não vira Times
- Cores, tamanhos, estilos: INTOCÁVEIS
- Font "Umbrella 25pt BOLD" = "Umbrella 25pt BOLD"
- Se algo muda, o documento **não saiu do Perito**

**Não negociar**: Formatar é trabalho de editor de texto, não de IA.

---

## Por Que Isso Importa

**Empresa de 40 anos**:
- Tem identidade visual
- Tem padrão consolidado
- Tem credibilidade baseada em qualidade/estética
- Clientes reconhecem pelo jeito (não genérico)

Se sistema muda formatação ou força entrada, **quebra a credibilidade**. 

---

## Implicações para Código

1. **Aceitação de Entrada**
   - `@router.post("/laudos")` aceita dict/JSON livremente
   - Não validar que "deve ser apenas esses campos"
   - Deixar ser extensível

2. **Formatação DOCX**
   - Cada run preserva propriedades (font.name, font.size, bold, italic, color)
   - Zero "correção automática"
   - Se user quer verde neon 36pt, user tem verde neon 36pt

3. **RAG + Manual**
   - Se RAG acha padrão: ótimo, usa
   - Se não acha: Permite input manual de campos
   - Se ferramenta de cálculos não existe: Acep ta manualmente preenchido

---

## Checklist de Respeito ao Modelo

- [ ] Entrada flexível (não restrita)
- [ ] Formatação SEMPRE preservada
- [ ] Sem "melhorias automáticas" não pedidas
- [ ] Padrão do perito = lei
- [ ] Manual + automático = coexistem
- [ ] Código nunca muda o que user criou (só preenche {{)

Este é o **contrato técnico com a empresa**.
