# 🚀 DESLOCAMENTO V2 — DEPLOY AGORA

## Status: PRONTO PARA DEPLOY

✅ Todos os 4 arquivos estão em scratchpad:
- `deslocamento_v2.py` (7.4KB)
- `deslocamento_routes_v2.py` (8.2KB)
- `deslocamento_ui.html` (16KB)
- `requirements_deslocamento_v2.txt` (79B)

---

## ⚡ FAZER DEPLOY AGORA (3 opções)

### Opção A: PowerShell no Windows (Recomendado)

**No Windows PowerShell (como Admin)**:

```powershell
# Copiar e rodar:
cd C:\Users\bruno\  # (ou pasta onde tiver os scripts)
.\DEPLOY_DESLOCAMENTO_WINDOWS.ps1
```

**O script faz automaticamente**:
1. SCP 4 arquivos pro VPS
2. SSH: instala deps + docker restart
3. Testa endpoints

---

### Opção B: Manual (copiar/colar)

**Terminal Windows (com SSH/SCP disponível)**:

```bash
# 1. SCP files
scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento_v2.py root@129.121.34.186:/var/www/perito-v6/backend/app/services/

scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento_routes_v2.py root@129.121.34.186:/var/www/perito-v6/backend/app/routes/

scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento_ui.html root@129.121.34.186:/var/www/perito-v6/backend/frontend/public/

scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/requirements_deslocamento_v2.txt root@129.121.34.186:/var/www/perito-v6/backend/

# 2. SSH
ssh -p 22022 root@129.121.34.186
cd /var/www/perito-v6/backend
pip install -r requirements_deslocamento_v2.txt -q
docker restart perito-v6-backend

# 3. Teste
sleep 5
curl -X POST http://localhost:8000/api/v1/deslocamento/calcular \
  -H "Content-Type: application/json" \
  -d '{"origem":"Campo Grande","destino":"Dourados","tipo_deslocamento":"rodovia"}'
```

---

### Opção C: agent_windows.py (Custom Job)

Se agent_windows.py estiver rodando, pode fazer um job custom. Mas a Opção A é mais rápida.

---

## ✅ Após Deploy

**Testar UI**:
```
http://129.121.34.186:8000/frontend/public/deslocamento_ui.html
```

**Testar API**:
```bash
# Rodovia com pedágio automático
curl -X POST http://129.121.34.186:8000/api/v1/deslocamento/calcular \
  -H "Content-Type: application/json" \
  -d '{"origem":"Campo Grande","destino":"Dourados","tipo_deslocamento":"rodovia","ida_volta":true}'

# Terra sem pedágio
curl -X POST http://129.121.34.186:8000/api/v1/deslocamento/calcular \
  -H "Content-Type: application/json" \
  -d '{"origem":"-20.47,-55.40","destino":"-22.22,-54.80","tipo_deslocamento":"terra"}'

# Upload KML
curl -X POST http://129.121.34.186:8000/api/v1/deslocamento/upload-kml \
  -F "file=@seu_arquivo.kml"
```

---

## 🎯 Features Ativadas

✅ **Pedágio Automático** — cálculo por km, sem digitação manual  
✅ **Deslocamento Terra** — lat/lon para fazendas, sem pedágio  
✅ **KML/GeoJSON Upload** — Google Earth + QGIS  
✅ **UI com Abas** — Rodovia | Terra | Upload | Mapa  
✅ **Preview Mapa** — Folium interativo  
✅ **PDF Export** — resultado em PDF  

---

## 📋 Checklist Pós-Deploy

- [ ] SCP dos 4 arquivos bem-sucedido
- [ ] pip install requirements_deslocamento_v2.txt bem-sucedido
- [ ] docker restart perito-v6-backend bem-sucedido
- [ ] Teste API GET /cidades retorna 200
- [ ] Teste API POST /calcular retorna resultado correto
- [ ] UI abre em browser (http://...)
- [ ] Teste upload KML/GeoJSON

---

**Próximo passo**: Execute Opção A (PowerShell) e confirme quando terminar! 🚀

