# ⚡ Quick Reference - OnCabito Bot

Comandos e informações essenciais para uso diário do OnCabito Bot.

---

## 🚀 **DEPLOY RÁPIDO**

```bash
# No servidor:
cd /opt/oncabito-bot
git pull && ./deploy.sh
```

---

## 📊 **MONITORAMENTO**

### 🔍 **Status do Bot**
```bash
# Ver se está rodando
docker ps | grep oncabito

# Logs em tempo real
docker logs oncabito-bot -f

# Health check
docker inspect oncabito-bot --format='{{.State.Health.Status}}'
```

### 📈 **Métricas Rápidas**
```bash
# Usuários no banco
sqlite3 data/database/sentinela.db "SELECT COUNT(*) FROM users;"

# Últimas mensagens
tail -20 logs/bot.log

# Espaço em disco
df -h
```

---

## 🔧 **COMANDOS DE EMERGÊNCIA**

### ⚠️ **Restart de Emergência**
```bash
cd /opt/oncabito-bot
docker-compose restart
```

### 🛑 **Parada de Emergência**
```bash
cd /opt/oncabito-bot
docker-compose down
```

### 🔄 **Rebuild Completo**
```bash
cd /opt/oncabito-bot
docker-compose down
git pull
./deploy.sh
```

---

## 📋 **TROUBLESHOOTING BÁSICO**

| Problema | Solução Rápida |
|----------|----------------|
| Bot não responde | `docker logs oncabito-bot --tail 50` |
| Container não inicia | Verificar `.env` e `docker-compose ps` |
| Sem espaço em disco | `docker system prune -f` |
| Erro de permissão | `sudo chown -R $USER:$USER data/ logs/` |
| Database locked | Verificar se bot não está rodando duplo |

---

## ⚙️ **CONFIGURAÇÕES ESSENCIAIS**

### 📁 **Arquivos Importantes**
```
/opt/oncabito-bot/
├── .env                    # Credenciais (nunca commitar)
├── docker-compose.yml      # Configuração Docker
├── deploy.sh              # Script de deploy
├── data/database/         # Banco de dados (backup!)
└── logs/                  # Logs do sistema
```

### 🔑 **Variáveis Críticas (.env)**
```bash
TELEGRAM_TOKEN=          # Token do BotFather
TELEGRAM_GROUP_ID=       # ID do grupo
HUBSOFT_CLIENT_SECRET=   # Secret da API
HUBSOFT_PASSWORD=        # Senha do usuário
```

---

## 🎯 **CHECKLISTS DIÁRIOS**

### ✅ **Manhã (5 min)**
- [ ] Verificar se bot está online: `docker ps`
- [ ] Logs sem erros: `docker logs oncabito-bot --tail 20`
- [ ] Espaço em disco OK: `df -h`

### ✅ **Tarde (2 min)**
- [ ] Verificar checkup diário: `tail logs/checkup.log`
- [ ] Health check OK: `docker inspect oncabito-bot`

### ✅ **Noite (3 min)**
- [ ] Backup automático: `ls -la backups/`
- [ ] Métricas do dia: Usuários ativos/removidos

---

## 🆘 **CONTATOS DE EMERGÊNCIA**

### 📞 **Suporte Técnico**
- **Logs**: `/opt/oncabito-bot/logs/`
- **Documentação**: `/opt/oncabito-bot/docs/`
- **Troubleshooting**: `docs/TROUBLESHOOTING_COMPLETO.md`

### 🔧 **Comandos de Diagnóstico**
```bash
# Informações completas do sistema
./tools/system_info.sh

# Teste de configuração
python3 -c "from src.sentinela.core.config import *; print('Config OK')"

# Conectividade
ping api.oncabo.hubsoft.com.br
```

---

*Quick Reference atualizado em 24/09/2025*