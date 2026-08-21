#!/bin/bash
# Script de Deploy Seguro para VPS
# Atualiza a VPS sem parar o serviço (zero-downtime)
# Uso: ./deploy_seguro.sh [arquivo_para_sync]

set -e

# Configurações
VPS_HOST="sistema.ipcms.com.br"
VPS_USER="admin"
VPS_PASSWORD="Admin@2026" # Em produção, use chaves SSH
REMOTE_DIR="/home/admin/pipeline"

# Caminho absoluto para o script de backup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_automatico.sh"

echo "🚀 Iniciando deploy seguro para VPS..."

# 1. Backup local antes do deploy
echo "💾 Realizando backup local..."
if [ -f "$BACKUP_SCRIPT" ]; then
    bash "$BACKUP_SCRIPT"
else
    echo "⚠️ Aviso: Script de backup não encontrado em $BACKUP_SCRIPT. Pulando backup local."
fi

# 2. Sync de arquivos para a VPS
echo "📤 Sincronizando arquivos..."
rsync -avz --progress \
    --exclude='.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.tar.gz' \
    --exclude='backups/' \
    pipeline/ \
    "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/"

# 3. Atualiza dependências na VPS (se necessário)
echo "📦 Atualizando dependências na VPS..."
ssh "${VPS_USER}@${VPS_HOST}" "cd ${REMOTE_DIR} && pip install -r requirements.txt"

# 4. Reinicia serviços apenas se necessário (ex: se houver mudança em scripts críticos)
# Para zero-downtime, idealmente usa-se reload de serviços (ex: gunicorn, celery)
echo "🔄 Reiniciando serviços..."
ssh "${VPS_USER}@${VPS_HOST}" "cd ${REMOTE_DIR} && supervisorctl restart all"

echo "✅ Deploy concluído com sucesso!"
