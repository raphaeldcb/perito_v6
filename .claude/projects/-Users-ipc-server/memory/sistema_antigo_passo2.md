---
name: sistema-antigo-passo2
description: Sistema Perito ANTIGO (SQLite) — fonte da migração do Passo 2; dados ricos que o v6 não tem
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Sistema antigo (Passo 2) — fonte de migração (09/07/26)

**Onde:** SQLite `/var/www/perito/data/perito.db` no VPS (VIVO, atualizado 01/07 —
mais novo que os backups). Backups diários no OneDrive
`IPCMS - GERENCIA/SISTEMA/backups/perito_YYYY-MM-DD.db` (script PowerShell roda no
Windows do bruno, `C:\Users\bruno\...`, faz scp do VPS). Codebase antigo em
`/var/www/perito/` (auth_coletadores, atualizar_sistema_automatico.py, SQL, certs).

**É MUITO mais rico que o v6** — resolve o "DOC/TIPO/ÁREA vazios":
- `processos` (35): já tem **area** ("Contábil"...), **doc_tipo**, autor, reu (com
  representação), objeto, valor_honorarios/recebido, quesitos/quesitos_reu/juizo,
  advogados/adv_autor/adv_reu, assistentes_tecnicos, campos_dna, tags, datas.
- `intimacoes` (906): processo_id (linkado), conteudo, **prazo_calculado**,
  **acao_recomendada**, **fundamentacao_legal**, tipo_ato — histórico com IA já aplicada.
- `rag_juridico` (60): padrao→tipo_ato, prazo_dias, acao_recomendada,
  fundamentacao_legal, fonte, confianca, usos = base APRENDIDA de classificação
  intimação→prazo/ação. Semente perfeita p/ o [[rag-pgvector-pipeline]].
- coletadores (262 + 348 CPF + 228 pgtos), prestadores (363), financeiro (1935),
  calc_padroes (168), indices_monetarios (256), usuarios (27), empresas (2).

**Migração Passo 2:** legacy SQLite → v6 PostgreSQL (perito_v6). Mapear
processos.area→especialidade, doc_tipo→doc, autor/reu/honorarios direto; intimacoes;
coletadores/prestadores/financeiro; rag_juridico→RAG. Upsert por numero_cnj/CPF
(idempotente, sem duplicar). Backup antes.

Conecta: área classificada (aqui + nomes dos laudos [[acervo-laudos-onedrive]]) é o
gabarito p/ o Qwen classificar DOC/TIPO/ÁREA. Ver [[vinculo-intimacao-processo]].
