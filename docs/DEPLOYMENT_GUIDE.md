# 🚀 GUIA DE DEPLOY - ONCABITO BOT

Este guia explica como instalar o OnCabito Bot em qualquer servidor Linux.

---

## 📋 **PRÉ-REQUISITOS**

### 🐳 **Docker & Docker Compose**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

### 🐍 **Python 3.10+** (opcional para debug)
```bash
sudo apt install python3 python3-pip
```

---

## 📦 **INSTALAÇÃO AUTOMÁTICA**

### 1️⃣ **Clone o Projeto**
```bash
# Em qualquer diretório do servidor
git clone https://github.com/seu-usuario/oncabito-bot.git
cd oncabito-bot

# OU se transferir por FTP/SCP
scp -r projeto-local/ usuario@servidor:/home/usuario/oncabito-bot/
```

### 2️⃣ **Execute o Instalador**
```bash
chmod +x install.sh
./install.sh
```

**O instalador faz automaticamente:**
- ✅ Detecta o diretório atual
- ✅ Configura variáveis de ambiente
- ✅ Cria diretório de logs
- ✅ Atualiza paths nos scripts
- ✅ Configura cron job
- ✅ Cria script de deploy

### 3️⃣ **Configure Credenciais**
```bash
# Edite o arquivo .env com suas credenciais
nano .env
```

**Variáveis obrigatórias:**
```bash
TELEGRAM_TOKEN=seu_token_do_bot
TELEGRAM_GROUP_ID="-100123456789"
HUBSOFT_HOST="https://api.oncabo.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="77"
HUBSOFT_CLIENT_SECRET="sua_secret"
HUBSOFT_USER="bottelegram@oncabo.com.br"
HUBSOFT_PASSWORD="sua_senha"
RULES_TOPIC_ID="87"
WELCOME_TOPIC_ID="89"
INVITE_LINK_EXPIRE_TIME=1800
```

### 4️⃣ **Deploy do Bot**
```bash
./deploy.sh
```

---

## 🔧 **COMANDOS ÚTEIS**

### 📊 **Status e Monitoramento**
```bash
# Status do container
docker ps | grep oncabito-bot

# Logs em tempo real
docker logs -f oncabito-bot

# Logs do checkup diário
tail -f logs/checkup.log

# Status do cron job
crontab -l | grep oncabito
```

### 🔄 **Operações Comuns**
```bash
# Restart do bot
docker restart oncabito-bot

# Redeploy completo
./deploy.sh

# Teste manual do checkup
./run_checkup.sh

# Backup do banco de dados
cp data/database/sentinela.db backup/sentinela_$(date +%Y%m%d).db
```

### 🐛 **Debug e Troubleshooting**
```bash
# Execução interativa
docker exec -it oncabito-bot /bin/bash

# Teste da API HubSoft
docker exec oncabito-bot python3 -c "
from src.sentinela.clients.erp_client import check_contract_status
print(check_contract_status('12345678901'))
"

# Verificar banco de dados
docker exec oncabito-bot python3 -c "
import sqlite3
conn = sqlite3.connect('/app/database/sentinela.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print(f'Usuários no banco: {cursor.fetchone()[0]}')
"
```

---

## 📁 **ESTRUTURA DE DIRETÓRIOS**

```
/caminho/do/projeto/
├── 📁 src/                 # Código fonte
├── 📁 scripts/             # Scripts de automação
├── 📁 data/               # Banco de dados (persistido)
├── 📁 logs/               # Logs do sistema
├── 📄 .env                # Configurações (NÃO commitar)
├── 📄 Dockerfile          # Configuração do container
├── 📄 requirements.txt    # Dependências Python
├── 🔧 install.sh          # Instalador automático
├── 🚀 deploy.sh           # Script de deploy
├── ⏰ run_checkup.sh      # Checkup manual
└── 📖 DEPLOYMENT_GUIDE.md # Este guia
```

---

## ⏰ **AUTOMAÇÃO E CRON JOBS**

### 📅 **Cron Job Configurado:**
```bash
# Checkup diário às 6:00 da manhã
0 6 * * * /caminho/do/projeto/run_checkup.sh >> /caminho/do/projeto/logs/checkup.log 2>&1
```

### 🔄 **Outros Cron Jobs Úteis:**
```bash
# Backup diário às 3:00
0 3 * * * cp /caminho/do/projeto/data/database/sentinela.db /backup/sentinela_$(date +\%Y\%m\%d).db

# Limpeza de logs antigos (mensalmente)
0 0 1 * * find /caminho/do/projeto/logs -name "*.log" -mtime +30 -delete

# Restart semanal do bot (domingos às 4:00)
0 4 * * 0 docker restart oncabito-bot
```

---

## 🛡️ **SEGURANÇA E BACKUP**

### 🔐 **Configurações de Segurança**
```bash
# Permissões corretas
chmod 600 .env                    # Apenas owner pode ler
chmod 755 *.sh                    # Scripts executáveis
chmod -R 755 logs/                # Logs legíveis
```

### 💾 **Strategy de Backup**
```bash
# Backup completo
tar -czf backup/oncabito_$(date +%Y%m%d).tar.gz \
  --exclude='logs' \
  --exclude='.git' \
  ./

# Restore
tar -xzf backup/oncabito_YYYYMMDD.tar.gz
```

---

## 🌐 **FIREWALL E REDE**

### 🔥 **Configuração de Firewall**
```bash
# Apenas se necessário para debug
sudo ufw allow 22         # SSH
sudo ufw enable

# O bot usa apenas HTTPS saindo (443)
# Não precisa liberar portas de entrada
```

---

## 📞 **SUPORTE E MONITORAMENTO**

### 🚨 **Alertas Críticos**
- ❌ Container parado: `docker ps | grep oncabito-bot`
- 💾 Espaço em disco: `df -h`
- 📊 Uso de memória: `docker stats oncabito-bot --no-stream`

### 📊 **Health Check**
```bash
# Script de health check
./scripts/health_check.sh

# Ou manual:
curl -f http://localhost/health 2>/dev/null || echo "Bot offline"
```

---

## 🆘 **TROUBLESHOOTING COMUM**

### ❌ **Container não inicia**
```bash
# Verifica logs de erro
docker logs oncabito-bot

# Verifica .env
cat .env | grep -v "PASSWORD\|SECRET"

# Recria container
./deploy.sh
```

### ❌ **Cron job não executa**
```bash
# Verifica se está configurado
crontab -l

# Verifica logs do sistema
sudo tail /var/log/syslog | grep CRON

# Testa execução manual
./run_checkup.sh
```

### ❌ **API HubSoft falhando**
```bash
# Testa conectividade
docker exec oncabito-bot ping -c 3 api.oncabo.hubsoft.com.br

# Testa credenciais
docker exec oncabito-bot python3 -c "
from src.sentinela.clients.erp_client import get_auth_token
print('Token:', get_auth_token())
"
```

---

*Guia criado em 23/09/2025 - OnCabito Gaming Bot v2.0*