#!/bin/bash
# Script de Backup Automático
# Cria um backup com timestamp antes de qualquer operação crítica
# Uso: ./backup_automatico.sh [pasta_origem] [pasta_destino]

set -e

# Configurações
# Origem padrão: OneDrive conforme instrução
SOURCE_DIR="${1:-/Users/ipc_server/Library/CloudStorage/OneDrive-BibliotecasCompartilhadas-IPCMSPERICIASLTDA}"
BACKUP_DIR="${2:-/Users/ipc_server/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_${TIMESTAMP}"

# Cria o diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

echo "🔄 Iniciando backup..."
echo "📂 Origem: $SOURCE_DIR"
echo "📁 Destino: $BACKUP_DIR/$BACKUP_NAME"

# Verifica se a origem existe
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Erro: A pasta de origem '$SOURCE_DIR' não existe."
    exit 1
fi

# Copia os arquivos para o backup
cp -r "$SOURCE_DIR" "$BACKUP_DIR/$BACKUP_NAME"

# Compacta o backup
tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"

# Remove a pasta descompactada para economizar espaço
rm -rf "$BACKUP_DIR/$BACKUP_NAME"

echo "✅ Backup concluído: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"

# Mantém apenas os últimos 10 backups
cd "$BACKUP_DIR"
ls -t *.tar.gz | tail -n +11 | xargs -r rm

echo "🧹 Backups antigos removidos (mantidos: últimos 10)"
