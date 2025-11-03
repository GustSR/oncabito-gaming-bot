#!/bin/bash
#
# Script para executar verificação de integridade dentro do container Docker
#

echo "🔍 Executando verificação de integridade..."
echo "Data/Hora: $(date)"
echo "----------------------------------------"

# Executa o script dentro do container
docker exec oncabo-gaming-bot python3 scripts/tasks/verify_data_integrity.py

echo "----------------------------------------"
echo "✅ Verificação de integridade concluída em $(date)"
