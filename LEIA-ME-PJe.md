# 🚀 PJe TJMT — Automação Completa

## O que é

Sistema automático para **baixar autos do PJe TJMT** quando uma intimação chega no email.

**Você clica 1 botão no Perito** → tudo sai automático → só coloca A3 + Authenticator quando solicitado.

---

## Arquivos

### Mac (já pronto)
- `pje_selenium_downloader.py` — automação Selenium (não usado, só referência)
- Nada mais precisa no Mac

### Seu Windows (use isso)
- **`pjewin.py`** — executor Selenium com A3 (copiar para Windows)
- **`agent_windows.py`** — polling de jobs (copiar para Windows)

### Backend VPS (já live)
- `/api/v1/pje/ferramenta/baixar-autos` — botão dashboard
- `/api/v1/pje/ferramenta/status/{id}` — acompanhar progresso
- `/api/v1/pje/fila` — agent poll (X-Agent-Key)
- `/api/v1/pje/{job_id}/concluir` — agent reporta

---

## Fluxo E2E

```
1. Email TJMT chega em adm@ipcms.com.br
   ↓ (backend monitora)
   
2. Dashboard Perito v6 → Intimações
   [Linha intimação TJMT]
   [Botão "Baixar Autos PJe"]  ← CLICA AQUI
   ↓
   
3. POST /api/v1/pje/ferramenta/baixar-autos
   Backend enfileira Job
   ↓
   
4. Seu Windows (rodar agent_windows.py)
   GET /api/v1/pje/fila
   Detecta Job
   ↓
   
5. pjewin.executar_job()
   Chrome abre automaticamente
   Você coloca A3 + Authenticator
   ↓
   
6. Selenium automático
   • Preenche CNJ (6 campos)
   • Clica Pesquisar
   • Abre Paginador
   • Download Autos
   ↓
   
7. Salva em OneDrive
   ✅ Done — dashboard mostra "✅ Pronto"
```

---

## Como usar

### 1. Copiar arquivos para Windows

```powershell
# Copiar de Mac (via GitHub ou diretamente)
# pjewin.py
# agent_windows.py
```

### 2. Instalar dependências

```powershell
pip install selenium requests
```

### 3. Executar agent (deixar rodando)

```powershell
# PowerShell
$env:PERITO_API_URL = "http://129.121.34.186:8000"
$env:AGENT_API_KEY = "perito-mac-agent-key-v6-2026-07-14"
python agent_windows.py
```

Vai ver:
```
🤖 Agent Windows iniciado
🔗 API: http://129.121.34.186:8000
⏱️  Poll: 30s
============================================================
💤 Nenhum job na fila, aguardando...
```

### 4. Clica botão no Perito (browser)

1. Acessa https://sistema.ipcms.com.br
2. Va em "Intimações"
3. Encontra linha TJMT
4. Clica botão "Baixar Autos PJe" (será adicionado)
5. Vê mensagem "🚀 Enfileirado"

### 5. Agent Windows detecta

No PowerShell, vai ver:
```
▶️  Job 123 (pje_download_autos): {'numero_cnj': '0000038-16.2016.8.11.0019', ...}
  ✓ Preencheu 0000038
  ✓ Pesquisou
  ✓ Abriu paginador
  ✓ Clicou 'Download autos'
  ✓ Clicou 'Download'
  ✓ PDF baixado: C:\Users\...\Downloads\0000038-16.2016.8.11.0019.pdf
  ✓ Salvo em OneDrive: C:\Users\...\OneDrive - Bibliotecas...\intimações baixadas\0000038_16_2016_8_11_0019.pdf
✅ Job 123 concluído
```

### 6. Dashboard atualiza

Página muda para:
```
✅ Autos já baixados — 1.5 MB
```

---

## Detalhes técnicos

### pjewin.py

Executa no Windows com A3 autenticado (8h de token):

- Conecta ao Chrome (ou via `--remote-debugging-port=9222` ou ChromeDriver local)
- Parse CNJ (20 dígitos → 7+2+4+1+2+4)
- Preenche formulário PJe
- Clica sequência: Pesquisar → Paginador → Download Autos → Download
- Busca PDF em `Downloads/`
- Copia para OneDrive sincronizado

### agent_windows.py

Loop infinito:

- A cada 30s: `GET /api/v1/pje/fila` com X-Agent-Key
- Se há job: chama `executar_job()` (pjewin)
- PATCH `/api/v1/pje/{job_id}/concluir` com resultado
- Repete

### Variáveis de ambiente

```
PERITO_API_URL = "http://129.121.34.186:8000"
AGENT_API_KEY = "perito-mac-agent-key-v6-2026-07-14"
AGENT_POLL_SEGUNDOS = "30"  (opcional)
ONEDRIVE_INTIMACOES_PATH = "C:\Users\...\OneDrive - Bibliotecas...\IPCMS - ARQUIVOS\PROCESSOS\intimações baixadas"
```

---

## Troubleshooting

### Chrome não abre
- Verificar se Chrome está instalado
- Ou instalar ChromeDriver no PATH

### A3 não funciona
- Verificar se token está válido (max 8h desde último login)
- Fazer login no PJe antes de rodar agent

### OneDrive não encontra pasta
- Configurar `ONEDRIVE_INTIMACOES_PATH` com caminho completo
- Ou confirmar que OneDrive está sincronizado

### "pjewin não importado"
- Verificar se `pjewin.py` está no mesmo diretório que `agent_windows.py`

---

## Próximos passos

1. ✅ Código pronto (pjewin.py + agent_windows.py)
2. ⏳ Copiar para Windows seu
3. ⏳ Rodar agent_windows.py
4. ⏳ Clique botão no Perito → teste E2E

---

**Pronto para testar?** 🚀
