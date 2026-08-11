---
name: deploy-media-analyzer-v53
description: Deploy da Ferramenta de Análise de Mídia no Perito System v5.3 (VPS 129.121.34.186)
metadata: 
  node_type: memory
  type: project
  originSessionId: 4c8277ee-7fb1-42ca-8056-ddfd2a975130
---

# Deploy Ferramenta Análise de Mídia — Perito System v5.3

**Data:** 2 de julho de 2026  
**Status:** ✅ Completo  
**Ambiente:** VPS (root@129.121.34.186:22022)  
**Diretório:** `/var/www/perito-v5.2/`

## O Que Foi Deployado

✅ **Código Python Backend**
- `main.py` — Integração com rotas /api/v1/media
- `ferramentas/media_analyzer.py` — Classe MediaAnalyzer (Qwen 3.6 + LLaVA + Whisper)
- `pipeline/media_analyzer_router.py` — Router FastAPI
- `INTEGRACAO_MEDIA_ANALYZER.md` — Documentação

✅ **Dependências Verificadas**
- FastAPI 0.136.3 ✓
- Uvicorn 0.49.0 ✓
- Whisper (via pip)
- Librosa (via pip)

## O Que NÃO foi Tocado

✅ **Frontend Intacto**
- Node.js rodando (PID 2716814)
- Dashboard operacional
- Todos endpoints do Perito funcionando
- index.html, public/, src/ mantidos como estavam

## Backup

Backup automático criado em:
```
/var/www/perito-v5.2/backup_YYYYMMDD_HHMMSS.tar.gz
```

## Como Usar

### Iniciar o serviço FastAPI

```bash
ssh -i /Users/ipc_server/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186

cd /var/www/perito-v5.2

# Opção 1: Manual
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Opção 2: Background (recomendado)
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/www/perito-v5.2/logs/fastapi.log 2>&1 &
```

### Testar endpoints

```bash
# Health check
curl https://sistema.ipcms.com.br/api/v1/media/health

# Listar formatos suportados
curl https://sistema.ipcms.com.br/api/v1/media/supported-formats

# Analisar arquivo
curl -X POST "https://sistema.ipcms.com.br/api/v1/media/analyze" \
  -F "file=@/path/to/video.mp4" \
  -F "prompt=Analise detalhadamente"
```

## Endpoints Disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/media/analyze` | Upload + análise |
| POST | `/api/v1/media/analyze-url` | Arquivo local |
| GET | `/api/v1/media/health` | Health check |
| GET | `/api/v1/media/supported-formats` | Formatos suportados |

## Formatos Suportados

**Vídeos:** MP4, MOV, WEBM, AVI, MKV, FLV (até 2 horas)  
**Áudio:** MP3, WAV, M4A, FLAC, AAC, OGG (até 4 horas)  
**Imagens:** JPG, PNG, GIF, WEBP, BMP (até 50MB)

## Troubleshooting

### FastAPI não inicia
```bash
# Verificar porta 8000 disponível
lsof -i :8000
killall python3  # se necessário
```

### Whisper não disponível
```bash
pip3 install openai-whisper
```

### Dependency issue
```bash
cd /var/www/perito-v5.2
pip3 install -r requirements.txt
# ou instalar manualmente
pip3 install fastapi uvicorn librosa numpy requests
```

## Notas Importantes

- **Frontend**: Totalmente intacto, continua rodando via Node.js
- **Backend Python**: Rotas /api/v1/media adicionadas ao main.py
- **Modelos IA**: Qwen 3.6 (DashScope), LLaVA 13B (Ollama), Whisper (OpenAI)
- **CORS**: Habilitado para integração com frontend
- **Logs**: Salvos em `/var/www/perito-v5.2/logs/fastapi.log`

## Próximas Ações Sugeridas

1. Iniciar FastAPI em produção
2. Integrar UI no dashboard do Perito (se desejar)
3. Treinar usuários sobre nova ferramenta
4. Monitorar performance e logs
5. Configurar auto-restart via systemd/supervisor

---

**Comandos rápidos:**
```bash
# Conectar VPS
ssh -i /Users/ipc_server/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186

# Ir para diretório
cd /var/www/perito-v5.2

# Iniciar FastAPI
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Ver logs (se rodando em background)
tail -f logs/fastapi.log
```
