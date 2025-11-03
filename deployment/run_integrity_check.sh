#!/bin/bash
#
# Script para executar verificação de integridade dentro do container Docker
#

echo "🔍 Executando verificação de integridade..."
echo "Data/Hora: $(date)"
echo "----------------------------------------"

# Executa o script dentro do container com path absoluto
# IMPORTANTE: Usa path absoluto para __file__ ser resolvido corretamente
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/verify_data_integrity.py

echo "----------------------------------------"
echo "✅ Verificação de integridade concluída em $(date)"
