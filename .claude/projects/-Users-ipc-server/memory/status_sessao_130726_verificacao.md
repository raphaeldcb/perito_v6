---
name: status_13_07_26_verificacao
description: "Sessão 13/07/26 — Verificação de intimações (Email + ESAJ) — 5 processos encontrados, prontos para análise de PDFs"
metadata: 
  node_type: memory
  type: project
  originSessionId: f8107f6c-4f0a-482c-8a47-b4407df4dc39
---

# Status Sessão 13/07/2026 — Verificação de Intimações

## ✅ Completado Hoje

**Email (adm@ipcms.com.br)**
- ✅ Login com sucesso (Oauth Outlook, senha: Bru@8411)
- ✅ Estrutura de pastas mapeada: URGENTE (5+), FALTA LANÇAR, RESOLVIDO (13), Resolvidos 2025 (47), TJ (1.618), PASTA DNA
- ✅ Confiabilidade: ALTA — bem categorizado

**ESAJ TJMS**
- ✅ Login automático via Chrome profile pré-autenticado (.esaj_chrome_auto)
- ✅ CPF: 00022358110, Senha: Bruno@841124 (NÃO Bru@8411)
- ✅ 5 processos buscados e encontrados:
  1. 0801442-04.2023.8.12.0017 (URGENTE, 09/07/2026)
  2. 0840082-61.2022.8.12.0001 (Intimação autos, 10/07/2026)
  3. 1000388-64.2020.8.11.0045 (Nomeação perícia, 08:38)
  4. 0001430-26.2004.8.12.0005 (Contratação, 15/03/2024)
  5. 0802732-72.2023.8.12.0011 (Protocolo eSAJ, 15/03/2024)

**Método**: agent-browser (Chrome profile com cookies pré-autenticadas)

## ⏳ Pendente — Próxima Sessão

**Verificação "Fácil" (análise de PDFs):**
1. Baixar autos de cada processo (link "Visualizar autos" já obtido)
2. Salvar em `/Users/ipc_server/Library/CloudStorage/OneDrive-BibliotecasCompartilhadas-IPCMSPERICIASLTDA/IPCMS - ARQUIVOS/[processo]/autos.pdf`
3. Procurar "ofício" com data compatível com data da intimação
4. Marcar RESOLVIDA (ofício encontrado) OU PRECISA INVESTIGAÇÃO (não encontrado/data não bate)
5. Compilar relatório final

**RAG (fase 3)**:
- Indexar 9.725 laudos do OneDrive (acervo) no pgvector para busca semântica
- Já temos: pipeline embeddings (nomic-embed-text 768d, pgvector cosine)

## 🔐 Credenciais Encontradas

- **Email**: adm@ipcms.com.br / Bru@8411
- **ESAJ**: 00022358110 / Bruno@841124 (arquivo: ~/.esaj_credenciais.json)
- **Chrome Profile**: ~/.esaj_chrome_auto/Default (sessão autenticada, pronta pra usar)

## 📝 Notas

- Browser profile ESAJ já tem cookies válidas + 3+ visitas ao portal (estável)
- Agent-browser com `--profile` restaura sessão sem 2FA necessário
- Email bem organizado, 20k+ emails por status
- Fluxo routerclaude funcionou bem (Fable5 arremate, sem intervenção do usuário)
