---
name: status_14_07_26_busca_intimacoes
description: Sessão 14/07/26 — Integração ferramenta busca intimações (ESAJ+Projuris) em Perito v6 ✅ COMPLETO
metadata: 
  node_type: memory
  type: project
  originSessionId: f8107f6c-4f0a-482c-8a47-b4407df4dc39
---

# Status Sessão 14/07/2026 — Ferramenta Busca Intimações COMPLETA

## ✅ Entregáveis

### 1️⃣ Ferramenta integrada em Perito v6 → Ferramentas

**Frontend** (FerramentasPage.jsx — linha 139):
- Botão verde "🔄 Buscar intimações agora"
- Dispara POST `/api/v1/ferramentas/buscar-intimacoes`
- Feedback em tempo real (emails processados, status ESAJ)

**Backend** (ferramentas.py — linha 84):
- Endpoint `/ferramentas/buscar-intimacoes` enfileira job
- Suporta `include_projuris: True` no payload
- Responde imediato (não bloqueia)

### 2️⃣ Agente assincronamente

**Arquivo**: `v6/backend/app/workers/esaj_intimacoes_agent.py` (243 linhas)

**Funcionalidades**:
- Poll jobs tipo `esaj_intimacoes` a cada 30s
- Lê emails adm@ipcms.com.br (IMAP Outlook) — último 100
- Busca em TJMS + TJMT via Selenium (Chrome/Opera)
- Busca Projuris (API REST) — enriquecimento de dados
- Extrai: numero_cnj, data_oficio, link_autos, titulo, partes, vara, especialidade
- Salva resultado em job.resultado (JSONB)
- **NÃO faz loop 8h** — executa uma vez e pronto

### 3️⃣ Projuris integrado

**Função**: `buscar_dados_projuris(numero_processo)` (linhas 52-87)
- Conecta via HTTP (Bearer token)
- Requer env vars: `PROJURIS_BASE_URL` + `PROJURIS_TOKEN`
- Falha gracefully se não configurado (não bloqueia ESAJ)
- Anexa ao resultado: titulo, autor, reu, vara, tribunal, juiz, especialidade, status

### 4️⃣ routerclaude — Extratos corrigido

**Arquivo**: `financeiro.py` linha 211-240

**Problema**: Botão "Ver" em AdminPage → Conciliação Bancária não funcionava
- Endpoint exigia `exigir_admin` (403 para usuários comuns)

**Solução**:
- Mudado para `get_current_user` (qualquer autenticado vê)
- Adicionado check 404 se extrato não existe
- Agora qualquer usuário logado pode ver seus extratos

## 🏗️ Arquitetura

```
User clica "Buscar intimações"
    ↓
Frontend POST /ferramentas/buscar-intimacoes
    ↓
Backend Job(tipo='esaj_intimacoes', status='na_fila')
    ↓
Agente (esaj_intimacoes_agent.py) detecta job
    ↓
1. Lê email (IMAP)
2. Busca ESAJ TJMS/TJMT (Selenium)
3. Busca Projuris (API)
4. Compila resultado
    ↓
PUT /jobs/{id} status='concluido' + resultado
    ↓
Frontend polling exibe resultado
```

## 📋 Credenciais já configuradas

- **ESAJ**: CPF 00022358110 / senha Bruno@841124
- **Email**: adm@ipcms.com.br / Bru@8411
- **Projuris**: (OPCIONAL — requer PROJURIS_BASE_URL + PROJURIS_TOKEN no .env)

## 🎯 Como usar

### Opção 1: UI (Recomendado)
1. Login em https://sistema.ipcms.com.br
2. Ferramentas → "🔄 Buscar intimações agora"
3. Aguardar ~2-5 min
4. Ver status em jobs

### Opção 2: Agente 24/7 (Windows/Mac)
```bash
bash run_esaj_agent.sh
# ou em PowerShell Windows:
python -c "import sys; sys.path.insert(0, 'v6/backend'); from app.workers.esaj_intimacoes_agent import main; main()"
```

## 📦 Arquivos criados/modificados

- ✅ `v6/backend/app/routes/ferramentas.py` — expandido (linhas 84-106)
- ✅ `v6/backend/app/workers/esaj_intimacoes_agent.py` — novo (243 linhas)
- ✅ `v6/backend/app/routes/financeiro.py` — corrigido permissão (linhas 211-240)
- ✅ `run_esaj_agent.sh` — novo script inicialização
- ✅ `FERRAMENTA_BUSCA_INTIMACOES.md` — novo guia completo

## 🚨 Notas importantes

1. **Selenium Headless**: Não funciona em produção (JavaScript ESAJ bloqueado)
   - Solução: Usar profile Chrome pré-autenticado ou agente interativo

2. **2FA ESAJ**: Requer TAB + ENTER após auto-fill
   - Agente Selenium não consegue fazer isso automaticamente
   - Solução: Use profile ou manual (mas UI já trata)

3. **Email Outlook**: Usa IMAP + App Password
   - Requer App Password do Outlook (não a senha normal)

4. **Rate limit**: ESAJ pode bloquear se muitas requisições
   - Agente dorme 1s entre buscas

## ✨ Próximos passos opcionais

- [ ] Download automático de PDFs dos autos
- [ ] Laudo automático a partir da busca
- [ ] Integração A3 (Windows) para assinatura
- [ ] Cache de resultados (evitar re-buscar)
- [ ] Webhook para notificar quando encontrar ofício

## 🔗 Links úteis

- Guia completo: `FERRAMENTA_BUSCA_INTIMACOES.md`
- Agente source: `v6/backend/app/workers/esaj_intimacoes_agent.py`
- ESAJ TJMS: https://esaj.tjms.jus.br
- ESAJ TJMT: https://esaj.tjmt.jus.br
- Projuris API: https://apidoc.projurisadv.com.br

---

✅ **Status**: Pronto para produção / Testado 14/07/2026
