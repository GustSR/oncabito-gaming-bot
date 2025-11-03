#!/bin/bash
#
# Script para executar o checkup diário dentro do container Docker
#

echo "🚀 Executando checkup diário..."
echo "Data/Hora: $(date)"
echo "----------------------------------------"

# Executa o script dentro do container
docker exec oncabo-gaming-bot python3 scripts/tasks/daily_cpf_checkup.py

echo "----------------------------------------"
echo "✅ Checkup concluído em $(date)"