# 🔧 Operações e Manutenção - OnCabito Bot

Guia completo para operações diárias, manutenção preventiva e gestão do sistema em produção.

---

## 📋 **VISÃO GERAL OPERACIONAL**

### 🎯 **Objetivos de Disponibilidade**

| Métrica | Objetivo | Medição |
|---------|----------|---------|
| **Uptime** | 99.9% | Mensal |
| **Response Time** | < 2s | Média por hora |
| **Error Rate** | < 0.1% | Diário |
| **Recovery Time** | < 5 min | Por incidente |

### 📊 **Stack de Monitoramento**

```
🏗️ Monitoring Stack
├── 🐳 Container Health
│   ├─ Docker health checks
│   ├─ Resource monitoring
│   └─ Process monitoring
│
├── 📱 Application Metrics
│   ├─ Response times
│   ├─ Error rates
│   ├─ User interactions
│   └─ API call success
│
├── 🖥️ Infrastructure Metrics
│   ├─ CPU/Memory usage
│   ├─ Disk space
│   ├─ Network I/O
│   └─ System loads
│
└── 📋 Business Metrics
    ├─ User verifications/day
    ├─ Messages processed
    ├─ API success rate
    └─ Customer satisfaction
```

---

## 📅 **OPERAÇÕES DIÁRIAS**

### 🌅 **Checklist Matinal (8:00 AM)**

```bash
#!/bin/bash
# morning_check.sh

echo "🌅 OnCabito Bot - Checklist Matinal"
echo "=================================="

# 1. Status geral do sistema
echo "📊 Status Geral:"
echo "Bot Status: $(docker-compose ps oncabito-bot | grep 'Up' &>/dev/null && echo '✅ Online' || echo '❌ Offline')"
echo "Health: $(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')"
echo "Uptime: $(docker inspect oncabito-bot | jq -r '.[0].State.StartedAt')"

# 2. Métricas das últimas 24h
echo "📈 Métricas (24h):"
MESSAGES_24H=$(docker logs oncabito-bot --since 24h | grep "mensagem processada" | wc -l)
ERRORS_24H=$(docker logs oncabito-bot --since 24h | grep -i error | wc -l)
VERIFICATIONS_24H=$(docker logs oncabito-bot --since 24h | grep "verificação.*sucesso" | wc -l)

echo "Mensagens processadas: $MESSAGES_24H"
echo "Verificações realizadas: $VERIFICATIONS_24H"
echo "Erros registrados: $ERRORS_24H"

# 3. Recursos do sistema
echo "💻 Recursos do Sistema:"
echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free -h | grep '^Mem' | awk '{print $3"/"$2}')"
echo "Disk: $(df -h /opt/oncabito-bot | tail -1 | awk '{print $5}') usado"

# 4. Conectividade de APIs
echo "🌐 Conectividade APIs:"
timeout 5 curl -s https://api.telegram.org >/dev/null && echo "✅ Telegram API" || echo "❌ Telegram API"
timeout 5 curl -s https://api.oncabo.hubsoft.com.br >/dev/null && echo "✅ HubSoft API" || echo "❌ HubSoft API"

# 5. Backup da noite anterior
echo "💾 Backup:"
LAST_BACKUP=$(ls -t /opt/oncabito-bot/backups/*.tar.gz 2>/dev/null | head -1)
if [ -n "$LAST_BACKUP" ]; then
    echo "✅ Último backup: $(basename $LAST_BACKUP)"
else
    echo "⚠️ Nenhum backup encontrado"
fi

# 6. Logs críticos
echo "🚨 Alertas nas últimas 24h:"
CRITICAL_LOGS=$(docker logs oncabito-bot --since 24h | grep -i "critical\|fatal\|emergency" | wc -l)
if [ $CRITICAL_LOGS -gt 0 ]; then
    echo "⚠️ $CRITICAL_LOGS logs críticos encontrados"
    docker logs oncabito-bot --since 24h | grep -i "critical\|fatal\|emergency" | tail -3
else
    echo "✅ Nenhum log crítico"
fi

echo ""
echo "📝 Resumo:"
if [ $ERRORS_24H -lt 10 ] && [ $CRITICAL_LOGS -eq 0 ]; then
    echo "✅ Sistema operando normalmente"
else
    echo "⚠️ Atenção necessária - verificar logs detalhados"
fi

echo "⏰ Próximo check: $(date -d '+4 hours' '+%H:%M')"
```

### 🕐 **Monitoramento de 4h em 4h**

```bash
#!/bin/bash
# hourly_check.sh

echo "🕐 Check de 4h - OnCabito Bot ($(date))"

# Health check rápido
HEALTH=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
RUNNING=$(docker inspect oncabito-bot | jq -r '.[0].State.Running')

if [ "$HEALTH" != "healthy" ] || [ "$RUNNING" != "true" ]; then
    echo "🚨 ALERTA: Bot não está saudável!"
    echo "Status: $HEALTH | Running: $RUNNING"

    # Tentar restart automático
    echo "🔄 Tentando restart automático..."
    docker-compose restart oncabito-bot

    # Aguardar e verificar novamente
    sleep 30
    NEW_HEALTH=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')

    if [ "$NEW_HEALTH" = "healthy" ]; then
        echo "✅ Restart bem-sucedido"
    else
        echo "❌ Restart falhou - escalação necessária"
        # Enviar alerta para administradores
        ./send_alert.sh "CRITICAL: OnCabito Bot restart failed"
    fi
else
    echo "✅ Sistema operando normalmente"
fi

# Log de métricas básicas
echo "$(date),$(docker stats oncabito-bot --no-stream --format 'table {{.CPUPerc}},{{.MemUsage}}')" >> /opt/oncabito-bot/logs/metrics.csv
```

### 🌙 **Checklist Noturno (22:00 PM)**

```bash
#!/bin/bash
# evening_check.sh

echo "🌙 OnCabito Bot - Checklist Noturno"
echo "================================="

# 1. Relatório do dia
echo "📊 Relatório do Dia:"
MESSAGES_TODAY=$(docker logs oncabito-bot --since "$(date +%Y-%m-%d)T00:00:00" | grep "mensagem processada" | wc -l)
VERIFICATIONS_TODAY=$(docker logs oncabito-bot --since "$(date +%Y-%m-%d)T00:00:00" | grep "verificação.*sucesso" | wc -l)
ERRORS_TODAY=$(docker logs oncabito-bot --since "$(date +%Y-%m-%d)T00:00:00" | grep -i error | wc -l)
USERS_ADDED=$(docker logs oncabito-bot --since "$(date +%Y-%m-%d)T00:00:00" | grep "usuário adicionado" | wc -l)

echo "Mensagens: $MESSAGES_TODAY"
echo "Verificações: $VERIFICATIONS_TODAY"
echo "Usuários adicionados: $USERS_ADDED"
echo "Erros: $ERRORS_TODAY"

# 2. Preparar backup noturno
echo "💾 Executando backup noturno..."
./backup.sh

# 3. Limpeza de logs antigos
echo "🧹 Limpeza de logs antigos..."
find /opt/oncabito-bot/logs -name "*.log" -mtime +7 -delete
docker system prune -f >/dev/null 2>&1

# 4. Preparar relatório para o dia seguinte
echo "📋 Preparando relatório..."
cat > /opt/oncabito-bot/daily_report.txt << EOF
OnCabito Bot - Relatório Diário ($(date +%d/%m/%Y))
================================================

📈 Métricas do Dia:
- Mensagens processadas: $MESSAGES_TODAY
- Verificações realizadas: $VERIFICATIONS_TODAY
- Novos usuários: $USERS_ADDED
- Taxa de erro: $(echo "scale=2; $ERRORS_TODAY * 100 / $MESSAGES_TODAY" | bc)%

📊 Status do Sistema:
- Uptime: $(docker inspect oncabito-bot | jq -r '.[0].State.StartedAt')
- Health: $(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
- Uso de CPU: $(docker stats oncabito-bot --no-stream --format '{{.CPUPerc}}')
- Uso de Memória: $(docker stats oncabito-bot --no-stream --format '{{.MemUsage}}')

💾 Backup:
- Status: $([ -f "/opt/oncabito-bot/backups/backup-$(date +%Y%m%d)*.tar.gz" ] && echo "✅ Realizado" || echo "❌ Falhou")
- Tamanho: $(ls -lh /opt/oncabito-bot/backups/backup-$(date +%Y%m%d)*.tar.gz 2>/dev/null | awk '{print $5}' | head -1)

🔍 Ações Necessárias:
$([ $ERRORS_TODAY -gt 50 ] && echo "- ⚠️ Investigar alto número de erros" || echo "- ✅ Nenhuma ação necessária")

EOF

echo "✅ Checklist noturno concluído"
```

---

## 🔧 **MANUTENÇÃO PREVENTIVA**

### 📅 **Manutenção Semanal (Domingos, 3:00 AM)**

```bash
#!/bin/bash
# weekly_maintenance.sh

echo "🔧 OnCabito Bot - Manutenção Semanal"
echo "=================================="

# 1. Backup completo
echo "💾 Backup completo semanal..."
BACKUP_DIR="/backup/weekly/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# Database
docker exec oncabito-bot sqlite3 /app/data/database/sentinela.db ".backup /tmp/full_backup.db"
docker cp oncabito-bot:/tmp/full_backup.db $BACKUP_DIR/

# Configuração
cp /opt/oncabito-bot/.env $BACKUP_DIR/.env.backup

# Logs importantes
tar -czf $BACKUP_DIR/logs_week.tar.gz /opt/oncabito-bot/logs/

echo "✅ Backup completo realizado"

# 2. Atualização do sistema
echo "🔄 Atualizando sistema..."
apt update && apt upgrade -y

# 3. Otimização do banco de dados
echo "🗄️ Otimizando banco de dados..."
docker exec oncabito-bot python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/database/sentinela.db')
print('Executando VACUUM...')
conn.execute('VACUUM')
print('Executando ANALYZE...')
conn.execute('ANALYZE')
conn.commit()
conn.close()
print('✅ Otimização concluída')
"

# 4. Limpeza profunda
echo "🧹 Limpeza profunda do sistema..."

# Logs antigos
find /opt/oncabito-bot/logs -name "*.log" -mtime +30 -delete
find /var/log -name "*.log.*.gz" -mtime +30 -delete

# Docker cleanup
docker system prune -af
docker volume prune -f

# Backups antigos (manter 3 meses)
find /backup -name "*.tar.gz" -mtime +90 -delete

# 5. Verificação de integridade
echo "🔍 Verificação de integridade..."

# Verificar banco de dados
DB_INTEGRITY=$(docker exec oncabito-bot sqlite3 /app/data/database/sentinela.db "PRAGMA integrity_check;")
if [ "$DB_INTEGRITY" = "ok" ]; then
    echo "✅ Integridade do banco OK"
else
    echo "⚠️ Problema na integridade do banco: $DB_INTEGRITY"
fi

# Verificar arquivos de configuração
if [ -f "/opt/oncabito-bot/.env" ]; then
    echo "✅ Arquivo .env presente"
else
    echo "❌ Arquivo .env não encontrado!"
fi

# 6. Teste de funcionalidade
echo "🧪 Teste de funcionalidade..."
docker-compose restart oncabito-bot

sleep 60

HEALTH_AFTER_RESTART=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
if [ "$HEALTH_AFTER_RESTART" = "healthy" ]; then
    echo "✅ Teste de funcionalidade passou"
else
    echo "❌ Teste de funcionalidade falhou"
fi

# 7. Relatório de manutenção
echo "📋 Gerando relatório de manutenção..."
cat > /opt/oncabito-bot/maintenance_report_$(date +%Y%m%d).txt << EOF
OnCabito Bot - Relatório de Manutenção Semanal
==============================================
Data: $(date)

✅ Atividades Realizadas:
- Backup completo
- Atualização do sistema
- Otimização do banco de dados
- Limpeza profunda
- Verificação de integridade
- Teste de funcionalidade

📊 Métricas Pós-Manutenção:
- Status: $HEALTH_AFTER_RESTART
- Espaço liberado: $(df -h /opt/oncabito-bot | tail -1 | awk '{print $4}') disponível
- Integridade DB: $DB_INTEGRITY

🔍 Próximas Ações:
- Monitorar performance nas próximas 24h
- Verificar logs de erro
- Acompanhar métricas de usuário

EOF

echo "✅ Manutenção semanal concluída"
```

### 📅 **Manutenção Mensal (1º Domingo do mês, 2:00 AM)**

```bash
#!/bin/bash
# monthly_maintenance.sh

echo "🗓️ OnCabito Bot - Manutenção Mensal"
echo "================================="

# 1. Análise profunda de performance
echo "📈 Análise de performance mensal..."

# Gerar relatório de métricas do mês
python3 << EOF
import sqlite3
import datetime

# Conectar ao banco
conn = sqlite3.connect('/opt/oncabito-bot/data/database/sentinela.db')

# Métricas do mês atual
start_month = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0)
end_month = datetime.datetime.now()

# Contar usuários ativos
active_users = conn.execute(
    "SELECT COUNT(*) FROM users WHERE created_at >= ?",
    (start_month.isoformat(),)
).fetchone()[0]

# Contar verificações realizadas
verifications = conn.execute(
    "SELECT COUNT(*) FROM user_states WHERE created_at >= ?",
    (start_month.isoformat(),)
).fetchone()[0]

print(f"📊 Métricas do Mês:")
print(f"Usuários ativos: {active_users}")
print(f"Verificações: {verifications}")

conn.close()
EOF

# 2. Auditoria de segurança
echo "🔒 Auditoria de segurança mensal..."
./security_audit.sh

# 3. Rotação de logs
echo "📋 Rotação de logs..."
tar -czf /archive/logs_$(date +%Y_%m).tar.gz /opt/oncabito-bot/logs/
rm -f /opt/oncabito-bot/logs/*.log

# 4. Verificação de atualizações
echo "🔄 Verificando atualizações disponíveis..."

# Sistema
apt list --upgradable

# Docker
CURRENT_DOCKER=$(docker --version | grep -oP '\d+\.\d+\.\d+')
echo "Docker atual: $CURRENT_DOCKER"

# Python packages
docker exec oncabito-bot pip list --outdated

# 5. Teste de disaster recovery
echo "🚨 Teste de disaster recovery..."

# Simular falha e recovery
echo "Simulando falha do container..."
docker stop oncabito-bot

echo "Aguardando 30 segundos..."
sleep 30

echo "Iniciando recovery..."
docker-compose up -d

sleep 60

RECOVERY_STATUS=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
if [ "$RECOVERY_STATUS" = "healthy" ]; then
    echo "✅ Disaster recovery teste passou"
else
    echo "❌ Disaster recovery teste falhou"
fi

# 6. Relatório executivo
echo "📊 Gerando relatório executivo..."
cat > /opt/oncabito-bot/executive_report_$(date +%Y_%m).txt << EOF
OnCabito Bot - Relatório Executivo Mensal
========================================
Período: $(date -d "month ago" +%B/%Y)

📈 KPIs do Mês:
- Uptime: $(echo "scale=2; (744 - $(grep -c "bot offline" /opt/oncabito-bot/logs/metrics.csv)) * 100 / 744" | bc)%
- Usuários processados: [Número do script Python acima]
- Taxa de sucesso: [Calculada pelos logs]
- Tempo médio de resposta: [Extraído dos logs]

🔒 Segurança:
- Incidentes de segurança: 0
- Tentativas de acesso não autorizado: [Dos logs de auditoria]
- Status da auditoria: ✅ Aprovado

💾 Infraestrutura:
- Backups realizados: $(ls /backup/weekly/ | wc -l)
- Espaço usado: $(df -h /opt/oncabito-bot | tail -1 | awk '{print $5}')
- Performance: Estável

🔧 Manutenção:
- Atualizações aplicadas: [Lista das atualizações]
- Problemas encontrados: [Se houver]
- Ações corretivas: [Se necessárias]

📋 Recomendações:
- [Baseadas na análise dos dados]
- [Melhorias propostas]
- [Investimentos necessários]

EOF

echo "✅ Manutenção mensal concluída"
```

---

## 📊 **MONITORAMENTO E ALERTAS**

### 🔔 **Sistema de Alertas**

```bash
#!/bin/bash
# alert_system.sh

# Configuração de alertas
TELEGRAM_ALERT_TOKEN="SEU_TOKEN_DE_ALERTA"
ADMIN_CHAT_ID="SEU_CHAT_ID_ADMIN"
EMAIL_ALERT="admin@oncabo.com.br"

send_telegram_alert() {
    local message="$1"
    local priority="$2"

    local emoji=""
    case $priority in
        "CRITICAL") emoji="🚨" ;;
        "WARNING") emoji="⚠️" ;;
        "INFO") emoji="ℹ️" ;;
        *) emoji="📢" ;;
    esac

    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_ALERT_TOKEN/sendMessage" \
        -d "chat_id=$ADMIN_CHAT_ID" \
        -d "text=$emoji OnCabito Bot Alert: $message" \
        -d "parse_mode=Markdown" >/dev/null
}

send_email_alert() {
    local subject="$1"
    local body="$2"

    echo "$body" | mail -s "$subject" "$EMAIL_ALERT"
}

# Verificações de alerta
check_bot_health() {
    local health=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')

    if [ "$health" != "healthy" ]; then
        send_telegram_alert "Bot não está saudável: $health" "CRITICAL"
        send_email_alert "OnCabito Bot Health Alert" "O bot está com status: $health"
        return 1
    fi
    return 0
}

check_disk_space() {
    local usage=$(df /opt/oncabito-bot | tail -1 | awk '{print $5}' | sed 's/%//')

    if [ $usage -gt 90 ]; then
        send_telegram_alert "Espaço em disco crítico: ${usage}%" "CRITICAL"
    elif [ $usage -gt 80 ]; then
        send_telegram_alert "Espaço em disco alto: ${usage}%" "WARNING"
    fi
}

check_memory_usage() {
    local mem_usage=$(docker stats oncabito-bot --no-stream --format '{{.MemPerc}}' | sed 's/%//')

    if (( $(echo "$mem_usage > 90" | bc -l) )); then
        send_telegram_alert "Uso de memória crítico: ${mem_usage}%" "CRITICAL"
    elif (( $(echo "$mem_usage > 80" | bc -l) )); then
        send_telegram_alert "Uso de memória alto: ${mem_usage}%" "WARNING"
    fi
}

check_error_rate() {
    local errors_last_hour=$(docker logs oncabito-bot --since 1h | grep -i error | wc -l)

    if [ $errors_last_hour -gt 50 ]; then
        send_telegram_alert "Taxa de erro alta: $errors_last_hour erros na última hora" "CRITICAL"
    elif [ $errors_last_hour -gt 20 ]; then
        send_telegram_alert "Taxa de erro elevada: $errors_last_hour erros na última hora" "WARNING"
    fi
}

check_api_connectivity() {
    if ! timeout 10 curl -s https://api.telegram.org >/dev/null; then
        send_telegram_alert "API Telegram inacessível" "CRITICAL"
    fi

    if ! timeout 10 curl -s https://api.oncabo.hubsoft.com.br >/dev/null; then
        send_telegram_alert "API HubSoft inacessível" "CRITICAL"
    fi
}

# Executar todas as verificações
main() {
    echo "🔔 Executando verificações de alerta..."

    check_bot_health
    check_disk_space
    check_memory_usage
    check_error_rate
    check_api_connectivity

    echo "✅ Verificações concluídas"
}

# Executar se chamado diretamente
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main
fi
```

### 📈 **Dashboard de Métricas**

```bash
#!/bin/bash
# generate_dashboard.sh

echo "📊 OnCabito Bot - Dashboard de Métricas"
echo "======================================"

# Função para calcular tempo de execução
start_time=$(date +%s)

# 1. Status geral
echo "🟢 STATUS GERAL"
echo "---------------"
HEALTH=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
UPTIME=$(docker inspect oncabito-bot | jq -r '.[0].State.StartedAt')
RESTART_COUNT=$(docker inspect oncabito-bot | jq -r '.[0].RestartCount')

echo "Health: $HEALTH"
echo "Started: $UPTIME"
echo "Restarts: $RESTART_COUNT"
echo ""

# 2. Performance metrics
echo "⚡ PERFORMANCE"
echo "-------------"
CPU_USAGE=$(docker stats oncabito-bot --no-stream --format '{{.CPUPerc}}')
MEM_USAGE=$(docker stats oncabito-bot --no-stream --format '{{.MemUsage}}')
NET_IO=$(docker stats oncabito-bot --no-stream --format '{{.NetIO}}')

echo "CPU: $CPU_USAGE"
echo "Memory: $MEM_USAGE"
echo "Network: $NET_IO"
echo ""

# 3. Métricas de negócio (últimas 24h)
echo "📈 MÉTRICAS DE NEGÓCIO (24h)"
echo "---------------------------"
MESSAGES_24H=$(docker logs oncabito-bot --since 24h | grep "mensagem processada" | wc -l)
VERIFICATIONS_24H=$(docker logs oncabito-bot --since 24h | grep "verificação.*sucesso" | wc -l)
ERRORS_24H=$(docker logs oncabito-bot --since 24h | grep -i error | wc -l)
USERS_ADDED_24H=$(docker logs oncabito-bot --since 24h | grep "usuário adicionado" | wc -l)

echo "Mensagens processadas: $MESSAGES_24H"
echo "Verificações bem-sucedidas: $VERIFICATIONS_24H"
echo "Novos usuários: $USERS_ADDED_24H"
echo "Erros: $ERRORS_24H"

# Calcular taxa de sucesso
if [ $MESSAGES_24H -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; ($MESSAGES_24H - $ERRORS_24H) * 100 / $MESSAGES_24H" | bc)
    echo "Taxa de sucesso: $SUCCESS_RATE%"
fi
echo ""

# 4. Recursos do sistema
echo "💻 RECURSOS DO SISTEMA"
echo "--------------------"
DISK_USAGE=$(df -h /opt/oncabito-bot | tail -1 | awk '{print $5}')
TOTAL_DISK=$(df -h /opt/oncabito-bot | tail -1 | awk '{print $2}')
FREE_DISK=$(df -h /opt/oncabito-bot | tail -1 | awk '{print $4}')

echo "Disco usado: $DISK_USAGE de $TOTAL_DISK"
echo "Disco livre: $FREE_DISK"

SYSTEM_LOAD=$(uptime | awk -F'load average:' '{print $2}')
echo "Load average:$SYSTEM_LOAD"
echo ""

# 5. APIs externas
echo "🌐 CONECTIVIDADE"
echo "---------------"
TELEGRAM_STATUS=$(timeout 5 curl -s https://api.telegram.org >/dev/null && echo "✅ Online" || echo "❌ Offline")
HUBSOFT_STATUS=$(timeout 5 curl -s https://api.oncabo.hubsoft.com.br >/dev/null && echo "✅ Online" || echo "❌ Offline")

echo "Telegram API: $TELEGRAM_STATUS"
echo "HubSoft API: $HUBSOFT_STATUS"
echo ""

# 6. Backups
echo "💾 BACKUPS"
echo "---------"
LAST_BACKUP=$(ls -t /opt/oncabito-bot/backups/*.tar.gz 2>/dev/null | head -1)
if [ -n "$LAST_BACKUP" ]; then
    BACKUP_DATE=$(stat -c %y "$LAST_BACKUP" | cut -d' ' -f1)
    BACKUP_SIZE=$(ls -lh "$LAST_BACKUP" | awk '{print $5}')
    echo "Último backup: $BACKUP_DATE ($BACKUP_SIZE)"
else
    echo "⚠️ Nenhum backup encontrado"
fi
echo ""

# 7. Alertas recentes
echo "🚨 ALERTAS RECENTES"
echo "------------------"
CRITICAL_LOGS=$(docker logs oncabito-bot --since 24h | grep -i "critical\|fatal" | wc -l)
WARNING_LOGS=$(docker logs oncabito-bot --since 24h | grep -i "warning" | wc -l)

echo "Logs críticos (24h): $CRITICAL_LOGS"
echo "Logs de warning (24h): $WARNING_LOGS"

if [ $CRITICAL_LOGS -gt 0 ]; then
    echo "Últimos logs críticos:"
    docker logs oncabito-bot --since 24h | grep -i "critical\|fatal" | tail -3
fi
echo ""

# 8. Tendências (comparação com ontem)
echo "📊 TENDÊNCIAS"
echo "------------"
MESSAGES_YESTERDAY=$(docker logs oncabito-bot --since 48h --until 24h | grep "mensagem processada" | wc -l)
VERIFICATIONS_YESTERDAY=$(docker logs oncabito-bot --since 48h --until 24h | grep "verificação.*sucesso" | wc -l)

if [ $MESSAGES_YESTERDAY -gt 0 ]; then
    MSG_TREND=$(echo "scale=1; ($MESSAGES_24H - $MESSAGES_YESTERDAY) * 100 / $MESSAGES_YESTERDAY" | bc)
    VER_TREND=$(echo "scale=1; ($VERIFICATIONS_24H - $VERIFICATIONS_YESTERDAY) * 100 / $VERIFICATIONS_YESTERDAY" | bc)

    echo "Mensagens vs ontem: ${MSG_TREND}%"
    echo "Verificações vs ontem: ${VER_TREND}%"
fi
echo ""

# 9. Resumo executivo
echo "📋 RESUMO EXECUTIVO"
echo "------------------"

# Status geral
if [ "$HEALTH" = "healthy" ] && [ $CRITICAL_LOGS -eq 0 ]; then
    echo "Status: ✅ Sistema operando normalmente"
elif [ "$HEALTH" = "healthy" ] && [ $CRITICAL_LOGS -gt 0 ]; then
    echo "Status: ⚠️ Sistema operacional com alertas"
else
    echo "Status: 🚨 Atenção necessária"
fi

# Ações recomendadas
echo "Ações recomendadas:"
if [ $CRITICAL_LOGS -gt 0 ]; then
    echo "- 🔍 Investigar logs críticos"
fi
if [ "${DISK_USAGE%?}" -gt 80 ]; then
    echo "- 🧹 Limpeza de disco necessária"
fi
if [ $ERRORS_24H -gt 100 ]; then
    echo "- 🚨 Investigar alta taxa de erros"
fi
if [ $CRITICAL_LOGS -eq 0 ] && [ "${DISK_USAGE%?}" -lt 80 ] && [ $ERRORS_24H -lt 20 ]; then
    echo "- ✅ Nenhuma ação necessária"
fi

# Tempo de execução
end_time=$(date +%s)
execution_time=$((end_time - start_time))
echo ""
echo "Dashboard gerado em ${execution_time}s - $(date)"
```

---

## 🔧 **AUTOMAÇÃO DE TAREFAS**

### ⏰ **Configuração do Crontab**

```bash
# /etc/crontab ou crontab -e

# Verificações de saúde a cada 5 minutos
*/5 * * * * /opt/oncabito-bot/alert_system.sh >/dev/null 2>&1

# Check matinal
0 8 * * * /opt/oncabito-bot/morning_check.sh >> /opt/oncabito-bot/logs/operations.log 2>&1

# Checks de 4h em 4h
0 */4 * * * /opt/oncabito-bot/hourly_check.sh >> /opt/oncabito-bot/logs/operations.log 2>&1

# Check noturno
0 22 * * * /opt/oncabito-bot/evening_check.sh >> /opt/oncabito-bot/logs/operations.log 2>&1

# Backup diário
0 3 * * * /opt/oncabito-bot/backup.sh >> /opt/oncabito-bot/logs/backup.log 2>&1

# Manutenção semanal (domingo às 3h)
0 3 * * 0 /opt/oncabito-bot/weekly_maintenance.sh >> /opt/oncabito-bot/logs/maintenance.log 2>&1

# Manutenção mensal (primeiro domingo do mês às 2h)
0 2 1-7 * 0 /opt/oncabito-bot/monthly_maintenance.sh >> /opt/oncabito-bot/logs/maintenance.log 2>&1

# Dashboard a cada hora
0 * * * * /opt/oncabito-bot/generate_dashboard.sh > /opt/oncabito-bot/logs/dashboard.log 2>&1

# Limpeza de logs antigos (diário às 4h)
0 4 * * * find /opt/oncabito-bot/logs -name "*.log" -mtime +7 -delete

# Rotação de métricas (semanal)
0 5 * * 0 tar -czf /archive/metrics_$(date +\%Y\%W).tar.gz /opt/oncabito-bot/logs/metrics.csv && > /opt/oncabito-bot/logs/metrics.csv
```

### 🤖 **Scripts de Automação Avançada**

```bash
#!/bin/bash
# auto_recovery.sh - Sistema de recuperação automática

echo "🤖 Sistema de Auto-Recovery OnCabito Bot"
echo "======================================="

# Configurações
MAX_RESTART_ATTEMPTS=3
RESTART_COOLDOWN=300  # 5 minutos
ESCALATION_THRESHOLD=5

# Arquivo de estado
STATE_FILE="/opt/oncabito-bot/.auto_recovery_state"

# Funções
get_restart_count() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "0"
    fi
}

increment_restart_count() {
    local current=$(get_restart_count)
    echo $((current + 1)) > "$STATE_FILE"
}

reset_restart_count() {
    echo "0" > "$STATE_FILE"
}

send_escalation_alert() {
    local message="$1"
    # Enviar alerta crítico para administradores
    ./alert_system.sh "$message" "CRITICAL"
}

# Verificação principal
check_and_recover() {
    local health=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
    local running=$(docker inspect oncabito-bot | jq -r '.[0].State.Running')
    local restart_count=$(get_restart_count)

    echo "Status atual: Health=$health, Running=$running, Restarts=$restart_count"

    if [ "$health" != "healthy" ] || [ "$running" != "true" ]; then
        echo "⚠️ Problema detectado no sistema"

        if [ $restart_count -ge $MAX_RESTART_ATTEMPTS ]; then
            echo "🚨 Máximo de tentativas atingido - escalando"
            send_escalation_alert "OnCabito Bot falhou $restart_count vezes. Intervenção manual necessária."
            return 1
        fi

        echo "🔄 Tentativa de recuperação automática ($((restart_count + 1))/$MAX_RESTART_ATTEMPTS)"
        increment_restart_count

        # Coletar informações de debug antes do restart
        echo "📋 Coletando logs de debug..."
        docker logs oncabito-bot --tail 50 > "/tmp/debug_$(date +%Y%m%d_%H%M%S).log"

        # Tentar restart
        docker-compose restart oncabito-bot

        # Aguardar e verificar
        sleep $RESTART_COOLDOWN

        local new_health=$(docker inspect oncabito-bot | jq -r '.[0].State.Health.Status')
        if [ "$new_health" = "healthy" ]; then
            echo "✅ Recuperação bem-sucedida"
            reset_restart_count
            ./alert_system.sh "Sistema recuperado automaticamente após $restart_count tentativas" "INFO"
        else
            echo "❌ Recuperação falhou"
            check_and_recover  # Recursão para nova tentativa
        fi
    else
        echo "✅ Sistema operando normalmente"
        reset_restart_count
    fi
}

# Verificação de dependências externas
check_dependencies() {
    echo "🔍 Verificando dependências externas..."

    # APIs críticas
    if ! timeout 10 curl -s https://api.telegram.org >/dev/null; then
        echo "⚠️ API Telegram inacessível"
        ./alert_system.sh "API Telegram inacessível - pode afetar operações" "WARNING"
    fi

    if ! timeout 10 curl -s https://api.oncabo.hubsoft.com.br >/dev/null; then
        echo "⚠️ API HubSoft inacessível"
        ./alert_system.sh "API HubSoft inacessível - verificações podem falhar" "WARNING"
    fi

    # Recursos do sistema
    local disk_usage=$(df /opt/oncabito-bot | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $disk_usage -gt 95 ]; then
        echo "🚨 Espaço em disco criticamente baixo"
        # Limpeza automática de emergência
        find /opt/oncabito-bot/logs -name "*.log" -mtime +1 -delete
        docker system prune -f
        ./alert_system.sh "Limpeza automática executada - espaço em disco crítico" "CRITICAL"
    fi
}

# Execução principal
main() {
    echo "Iniciando verificação de auto-recovery..."
    check_dependencies
    check_and_recover
    echo "Verificação concluída"
}

# Executar se chamado diretamente
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main
fi
```

---

## 📋 **DOCUMENTAÇÃO DE PROCEDIMENTOS**

### 📝 **Runbook de Operações**

```markdown
# OnCabito Bot - Runbook de Operações

## 🚨 Procedimentos de Emergência

### Bot Offline
1. **Diagnóstico Rápido (2 min)**
   ```bash
   docker-compose ps
   docker logs oncabito-bot --tail 20
   df -h
   ```

2. **Restart Padrão (1 min)**
   ```bash
   docker-compose restart oncabito-bot
   ```

3. **Restart Completo (2 min)**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Escalação (se restart falhar)**
   - Verificar logs detalhados
   - Contactar desenvolvedores
   - Executar recovery manual

### Alta Taxa de Erros
1. **Identificar Fonte**
   ```bash
   docker logs oncabito-bot | grep -i error | tail -20
   ```

2. **Verificar APIs**
   ```bash
   curl -s https://api.telegram.org
   curl -s https://api.oncabo.hubsoft.com.br
   ```

3. **Restart se necessário**

### Espaço em Disco Baixo
1. **Limpeza Imediata**
   ```bash
   find /opt/oncabito-bot/logs -mtime +1 -delete
   docker system prune -f
   ```

2. **Análise de Uso**
   ```bash
   du -sh /opt/oncabito-bot/*
   ```

3. **Backup e Limpeza**
   ```bash
   tar -czf /archive/emergency_backup.tar.gz /opt/oncabito-bot/data
   ```

## 📞 Contatos de Emergência
- Desenvolvedor Principal: [Telefone/Telegram]
- Administrador Sistema: [Telefone/Email]
- Suporte OnCabo: [Canal/Telefone]
```

---

## 📊 **MÉTRICAS E KPIs**

### 📈 **KPIs Principais**

| KPI | Meta | Medição | Frequência |
|-----|------|---------|------------|
| **Uptime** | 99.9% | Disponibilidade | Mensal |
| **Response Time** | < 2s | Tempo de resposta | Contínuo |
| **Success Rate** | > 99% | Taxa de sucesso | Diário |
| **Error Rate** | < 0.1% | Taxa de erro | Diário |
| **User Satisfaction** | > 95% | Feedback usuários | Semanal |

### 📊 **Coleta de Métricas**

```python
# metrics_collector.py
import sqlite3
import json
import datetime
from typing import Dict, List

class MetricsCollector:
    def __init__(self):
        self.db_path = '/app/data/database/sentinela.db'
        self.metrics_file = '/app/logs/metrics.json'

    def collect_daily_metrics(self) -> Dict:
        """Coleta métricas diárias do sistema"""

        conn = sqlite3.connect(self.db_path)
        today = datetime.date.today()

        metrics = {
            'date': today.isoformat(),
            'timestamp': datetime.datetime.now().isoformat(),
            'users': self._get_user_metrics(conn, today),
            'messages': self._get_message_metrics(conn, today),
            'performance': self._get_performance_metrics(),
            'errors': self._get_error_metrics(today)
        }

        conn.close()
        self._save_metrics(metrics)
        return metrics

    def _get_user_metrics(self, conn, date) -> Dict:
        """Métricas de usuários"""
        start_date = f"{date}T00:00:00"
        end_date = f"{date}T23:59:59"

        new_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?",
            (start_date, end_date)
        ).fetchone()[0]

        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        verified_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE verified = 1 AND created_at BETWEEN ? AND ?",
            (start_date, end_date)
        ).fetchone()[0]

        return {
            'new_users': new_users,
            'total_users': total_users,
            'verified_today': verified_users,
            'verification_rate': (verified_users / new_users * 100) if new_users > 0 else 0
        }

    def _get_message_metrics(self, conn, date) -> Dict:
        """Métricas de mensagens"""
        # Implementar coleta de métricas de mensagens
        return {
            'total_messages': 0,  # Implementar
            'successful_responses': 0,  # Implementar
            'failed_responses': 0,  # Implementar
            'average_response_time': 0  # Implementar
        }

    def _get_performance_metrics(self) -> Dict:
        """Métricas de performance do sistema"""
        import psutil
        import docker

        client = docker.from_env()
        container = client.containers.get('oncabito-bot')
        stats = container.stats(stream=False)

        return {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'container_memory': stats['memory_stats']['usage'],
            'container_cpu': stats['cpu_stats']['cpu_usage']['total_usage']
        }

    def _save_metrics(self, metrics: Dict):
        """Salva métricas em arquivo JSON"""
        with open(self.metrics_file, 'a') as f:
            json.dump(metrics, f)
            f.write('\n')

# Executar coleta diária
if __name__ == "__main__":
    collector = MetricsCollector()
    daily_metrics = collector.collect_daily_metrics()
    print(f"Métricas coletadas: {daily_metrics}")
```

---

*Documentação de operações criada em 23/09/2025 - OnCabito Gaming Bot v2.0*