---
name: status_sessao_073026
description: Status da sessão de 07/07/2026 - Integração Perito v6 com dados dinâmicos
metadata: 
  node_type: memory
  type: project
  originSessionId: 2c421bcf-d51b-4fac-a34e-76bfabd14055
---

## STATUS ATUAL

**BLOQUEADO**: Problema de login no sistema (mensagem: "Falha no login — verifique email e senha")

---

## O QUE FOI IMPLEMENTADO HOJE (✅ COMPLETO)

### Backend
- ✅ Modelo `Processo` criado (`/app/models/processo.py`)
- ✅ Endpoints de dados criados (`/app/routes/dados_processos.py`):
  - GET `/api/v1/dados/comarcas` (lista: Campo Grande, Corumbá, Três Lagoas, Dourados)
  - GET `/api/v1/dados/varas/{comarca_id}` (varas vinculadas por comarca)
  - GET `/api/v1/dados/juizes/{vara_id}` (juízes vinculados por vara)
  - GET `/api/v1/dados/tipos-documento` (Ofício, Laudo, Parecer, etc)
  - GET `/api/v1/dados/tipos-pericia` (Contábil, Engenharia, DNA)
  - GET `/api/v1/dados/empresas` (retorna 2 empresas dummy)
- ✅ Rota registrada em `__init__.py`

### Frontend
- ✅ `EditarProcesso.jsx` TOTALMENTE REESCRITO (484 linhas):
  - **Extrajudicial é PRIMEIRA opção** (não mais Judicial)
  - Dropdown Empresas carrega via API
  - Comarcas/Varas/Juízes dinâmicos e vinculados
  - **DNA muda automaticamente**: quando seleciona tipo "DNA", aba de "Partes" desaparece e mostra só "Participantes DNA"
  - Tipos de Documento dinâmicos
  - Tabela de Partes SEM coluna "Lado"
  - Tabela de DNA SEM coluna "Lado"
  - PDF é opção em ABA DOCUMENTOS (não mais em destaque no topo)

---

## PRÓXIMOS PASSOS (QUANDO LOGIN FUNCIONAR)

1. **Testar endpoints** na página `/atividades/novo`:
   - Verificar se comarcas/varas/juízes carregam
   - Clicar em DNA e conferir se Partes desaparece
   - Salvar processo e verificar se vai pro BD

2. **Integrar com BD real** (se precisar):
   - Endpoints atualmente retornam dados dummy
   - Quando login funcionar, conectar a empresas reais do BD
   - Adicionar migrações Alembic para Processo

3. **Ajustes finais**:
   - DNA pode precisar de mais campos (marcadores STR, genótipos, etc)
   - Financeiro/Prazos/Documentos ainda estão vazios
   - Validações e tratamento de erros

---

## ARQUIVOS CRIADOS/MODIFICADOS

**Backend:**
- `/backend/app/models/processo.py` (NOVO)
- `/backend/app/routes/dados_processos.py` (NOVO)
- `/backend/app/routes/__init__.py` (MODIFICADO - import + include_router)

**Frontend:**
- `/frontend/src/pages/EditarProcesso.jsx` (REESCRITO)

---

## NOTAS

- Dados são hardcoded por enquanto (comarcas MS, varas, juízes)
- Backend rebuild feito com `--no-cache` - endpoints devem estar ativos
- Login problem é PRÉ-REQUISITO para testar (precisa estar autenticado)
- DNA/Partes switching é funcional no código (depende só de login)
