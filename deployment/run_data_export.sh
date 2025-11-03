#!/bin/bash
#
# Script para executar export de dados críticos dentro do container Docker
#

echo "📦 Executando export de dados críticos..."
echo "Data/Hora: $(date)"
echo "----------------------------------------"

# Executa o script dentro do container
docker exec oncabo-gaming-bot python3 scripts/tasks/export_critical_data.py

echo "----------------------------------------"
echo "✅ Export de dados concluído em $(date)"
