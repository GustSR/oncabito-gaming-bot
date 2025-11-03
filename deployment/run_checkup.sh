#!/bin/bash
#
# Script para executar o checkup diário dentro do container Docker
#

echo "🚀 Executando checkup diário..."
echo "Data/Hora: $(date)"
echo "----------------------------------------"

# Executa o script dentro do container com path absoluto
# IMPORTANTE: Usa path absoluto para __file__ ser resolvido corretamente
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/daily_cpf_checkup.py

echo "----------------------------------------"
echo "✅ Checkup concluído em $(date)"