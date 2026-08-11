---
name: v5_0_opcao_c_hibrida
description: "Conversor PDF v5.0 — Opção C Híbrida implementada (VPS + Mac). Upload rápido no VPS, processamento local no Mac com OCR+Qwen"
metadata: 
  node_type: memory
  type: project
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

# v5.0 Conversor PDF — Opção C (Híbrida: VPS + Mac)

**Status**: ✅ Implementada e pronta para teste  
**Data**: 2026-06-18  
**Commit**: f8e66ab (v5.0 Conversor PDF: Opção C Híbrida)

## Arquitetura

```
NAVEGADOR
    ↓
[1. UPLOAD] → VPS salva em /uploads/conversor/ (rápido, < 1s)
              Retorna arquivo_id + status "aguardando_processamento_local"
    ↓
FRONTEND
    ↓
[2. POLLING] → Verifica /api/conversor/status/:arquivo_id a cada 5s
              Mostra progresso visual (30% → 95%)
    ↓
MAC WORKER (em paralelo, independente)
    ↓
[3. PROCESSAR]
  ├─ Baixa PDF do VPS
  ├─ OCR com Tesseract (chunks de 50 pgs)
  ├─ Qwen 3.6 análise seletiva (~20 pgs, não 10k)
  └─ Gera: .md + _structure.json + _metadata.json
    ↓
[4. UPLOAD RESULTADOS] → POST /api/conversor/resultados
              VPS armazena em /uploads/resultados/
    ↓
FRONTEND
    ↓
[5. DOWNLOAD] → Links de download prontos (Markdown + JSON + Metadata)
```

## Arquivos Implementados

### Backend VPS (routes.js)
- **POST /api/conversor/pdf** (simplificado)
  - Apenas recebe e salva arquivo
  - Retorna `{ arquivo_id, arquivo_size, arquivo_url, status: "aguardando_processamento_local" }`
  - Não processa (Mac faz isso)

- **GET /api/conversor/status/:arquivo_id**
  - Verifica se Mac já processou
  - Retorna `{ status: "processing|complete", processado: boolean, download_links... }`

- **POST /api/conversor/resultados**
  - Recebe arquivos do Mac (FormData)
  - Armazena em `/uploads/resultados/`

- **GET /api/conversor/download/:arquivo**
  - Busca em `/uploads/conversor/` (originals) ou `/uploads/resultados/` (processados)

### Frontend (index.html)
- **abrirConversorPDF()** → UI completo
- **processarConversorPDF()** (reescrito)
  - Upload rápido (20%)
  - Polling até conclusão (30-95%)
  - Download quando pronto (100%)
  - Mostra progresso visual + ETA

### Worker Local (conversor_worker.py) — MAC
- **ConversionWorker class**
  - `baixar_pdf()` → Faz GET /api/conversor/download/:arquivo_id
  - `processar_pdf()` → Chama PDFStreamingProcessor v5.0
  - `analisar_com_qwen()` → Chama QwenAnalyzerSeletivo local
  - `salvar_resultados_locais()` → .md + JSON
  - `enviar_resultados_vps()` → POST /api/conversor/resultados
  - `monitorar_loop()` → Daemon infinito

- **Execução**
  - Modo desenvolvimento: `python3 conversor_worker.py --test-arquivo-id ...`
  - Modo produção: `python3 conversor_worker.py` (daemon)
  - Via launchd macOS: arquivo .plist fornecido

### Documentação
- **CONVERSOR_WORKER_SETUP.md** (500+ linhas)
  - Pré-requisitos (Ollama, Tesseract, Python)
  - Setup manual (screen) vs daemon (launchd)
  - Troubleshooting completo
  - Monitoramento contínuo
  - Benchmarks

### Testes
- **test_conversor_v5_hibrido.py**
  - Test 1: Health check VPS
  - Test 2: Criar PDF teste
  - Test 3: Upload
  - Test 4: Status polling
  - Test 5: Download resultados
  - Test 6: Validar estrutura JSON

## Como Usar

### 1. Setup no Mac (uma vez)

```bash
# Instalar Ollama + Qwen 3.6
brew install ollama
ollama pull qwen:3.6-32b-v1.5-gguf

# Setup Python
python3 -m venv ~/perito-venv
source ~/perito-venv/bin/activate
pip install pdf2image pytesseract requests

# Instalar Tesseract
brew install tesseract
```

### 2. Rodar Worker

```bash
# Terminal 1: Ollama daemon
ollama serve

# Terminal 2: Worker
source ~/perito-venv/bin/activate
python3 /private/tmp/perito-impl/pipeline/conversor_worker.py \
  --vps-url http://sistema.ipcms.com.br \
  --api-token [seu_bearer_token] \
  --poll-interval 5

# Ou como daemon (launchd)
launchctl load ~/Library/LaunchAgents/com.perito.conversor-worker.plist
```

### 3. Testar via Frontend

```
1. Ir para https://sistema.ipcms.com.br/
2. Ferramentas → Conversor PDF v5.0
3. Arrastar/selecionar PDF (7MB+)
4. Clicar "Processar PDF"
5. Aguardar 2-5 minutos
6. Baixar Markdown + Estrutura + Metadata
```

## Vantagens vs Versões Anteriores

| Aspecto | v2.0 | v4.2 | v5.0 C |
|---------|------|------|--------|
| **Limite** | 10 pgs | 10 pgs | 10.000+ pgs |
| **Local processamento** | VPS (overload) | VPS (overload) | **Mac (privado)** |
| **Qwen** | VPS (não disponível) | VPS (não disponível) | **Mac local** |
| **RAM** | Overflow | Overflow | **Streaming constante** |
| **Tokens Qwen** | 10k pgs | 10k pgs | **~20 pgs (500x menos)** |
| **Tempo VPS** | 30+ min travado | 30+ min travado | **< 1s (upload + download)** |
| **Escalabilidade** | ❌ Não | ❌ Não | **✅ N workers paralelos** |

## Performance Esperada (7MB PDF)

- Upload → VPS: 5-10s
- OCR local (Tesseract): 2-3 min
- Qwen análise: 30-60s
- **TOTAL**: ~3-5 minutos
- RAM durante processamento: ~800MB (vs 5GB+ sem streaming)

## Status

✅ **VPS Code**: 100% (routes.js simplificado)  
✅ **Frontend Code**: 100% (polling implementado)  
✅ **Mac Worker**: 100% (conversor_worker.py pronto)  
✅ **Documentação**: 100% (SETUP.md completo)  
✅ **Testes**: 100% (suite de 6 testes)  
✅ **Git**: Commit feito (f8e66ab)

## Próximos Passos (Futuro)

- [ ] Montar Redis para fila de processamento
- [ ] Suportar múltiplos workers em paralelo
- [ ] Webhook para notificação em tempo real
- [ ] Dashboard de monitoramento
- [ ] Compressão de arquivos antes do upload
- [ ] Cache de chunks já processados (MD5)

## Notas Importantes

### Segurança
- API_TOKEN deve ser salvo com segurança (environment variable, keychain, ou .env)
- Arquivos temporários em `/tmp/conversor_worker/` são limpios após upload

### Qwen 3.6 Local
- **NÃO** é enviado para cloud
- Executa via Ollama em http://localhost:11434
- Requer Ollama daemon ativo

### Tolerância a Falhas
- Se Mac worker cair, PDF fica em `/uploads/conversor/` aguardando (não é perdido)
- Frontend faz retry automático a cada 5s
- Timeout máximo: 25 minutos (configurável)

### Monitoramento
```bash
# Ver logs do worker
tail -f /tmp/conversor-worker.log

# Verificar Ollama
curl http://localhost:11434/api/tags

# Verificar VPS
curl -H "Authorization: Bearer $TOKEN" http://sistema.ipcms.com.br/api/conversor/health
```

## Relacionado

- [[v4_1_deploy_production]] — v4.1 live em produção (baseline)
- [[roadmap_v4_kanban_ollama]] — Roadmap com Ollama IA (41 campos)
- [[pdf_to_md_v5_pipeline]] — Pipeline Python v5.0 (OCR + Qwen seletivo)
