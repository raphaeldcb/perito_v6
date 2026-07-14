#!/bin/bash
# Deploy manual — Você copia para VPS

echo "✅ Arquivos prontos em scratchpad:"
echo ""
ls -lh /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento* /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/requirements_deslocamento*
echo ""
echo "📋 COPIAR PARA VPS (SCP):"
echo ""
echo "scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento_v2.py root@129.121.34.186:/var/www/perito-v6/backend/app/services/"
echo "scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento_routes_v2.py root@129.121.34.186:/var/www/perito-v6/backend/app/routes/"
echo "scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/deslocamento_ui.html root@129.121.34.186:/var/www/perito-v6/backend/frontend/public/"
echo "scp -P 22022 /private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad/requirements_deslocamento_v2.txt root@129.121.34.186:/var/www/perito-v6/backend/"
echo ""
echo "🔌 DEPOIS, SSH:"
echo ""
echo "ssh -p 22022 root@129.121.34.186"
echo "cd /var/www/perito-v6/backend"
echo "pip install -r requirements_deslocamento_v2.txt"
echo "docker restart perito-v6-backend"
echo ""
echo "✅ Pronto!"
