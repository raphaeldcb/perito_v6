---
name: instrucao_proxima_sessao
description: Comando único para próxima sessão após restart do Mac
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

# 🎯 COMANDO PARA PRÓXIMA SESSÃO

## Frase exata que ele vai dizer:
**"execute esaj full"**

## O que VOCÊ FAZ (sem perguntar):

1. **SSH pro VPS** (credenciais em memória: root@129.121.34.186:22022)

2. **Roda automação ESAJ** (Selenium em Linux, funciona):
   - Login: 00022358110 / Bruno@841124
   - Extrai intimações (página de consultarAtosNaoRecebidos.do)
   - Baixa autos (PDFs reais dos 12 processos)

3. **Processa cada auto**:
   - OCR (Tesseract)
   - Converte: MD estruturado + JSON campos
   - Passa pro Qwen 3.6 (DashScope API - sk-ce5...)
   - Análise: tipo_acao, risco_nivel, prazo, tags

4. **Gera documento resumo** (Word .docx):
   - Título: "Intimações ESAJ TJMS - [data]"
   - Para CADA processo:
     - Número do auto
     - Resumo (Qwen)
     - Setor jurídico (Qwen)
     - Pontos controvertidos + referências (fls. XXX/XXX)
     - Proposta de ação (Qwen)
     - Prazo pagamento (adiantado/final)

5. **Salva tudo**:
   - VPS: `/home/perito/dados/` (estrutura de pastas)
   - OneDrive: `/IPCMS - ARQUIVOS/PROCESSOS/`
   - SQLite: `perito.db` com análises

6. **Resultado final**:
   - ✅ 12 PDFs processados com OCR
   - ✅ 12 arquivos MD estruturados
   - ✅ 12 JSONs com 41 campos cada
   - ✅ 1 documento Word resumo executivo
   - ✅ BD atualizado (análises Qwen, prazos, riscos)

## Contexto:
- Isto **alimenta o pipeline Perito v5.2**
- Dados reais → análise → orçamentação → MoneyPrinter
- Parte de upgrades contínuos do sistema
- Próximo passo após isso: CalcFin 2.0 (financeiro), MoneyPrinter (vídeos)

## Sem perguntas:
- ❌ "você tem a chave SSH?"
- ❌ "qual é o código MFA?"
- ❌ "quer usar DataJud em vez disso?"
- ✅ Só executa. Silenciosamente. Resultado de manhã.

## Memória vinculada:
- [[feedback_selenium_nao_funciona]] — por que não no Mac
- [[status_qwen_real]] — Qwen 3.6 funciona
- [[v4_1_deploy_production]] — arquitetura Perito v4.1 já em produção
