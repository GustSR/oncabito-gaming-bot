# 🤖 OnCabito Gaming Bot

**Bot oficial da comunidade gamer OnCabo** 🎮

Bot inteligente de moderação e gestão para grupos Telegram, integrado com o sistema ERP da OnCabo. Automatiza verificação de usuários, gerencia tópicos e mantém a comunidade organizada.

---

## ✨ **FUNCIONALIDADES**

### 🔐 **Verificação Automática**
- Validação de CPF contra API HubSoft
- Verificação de contratos ativos
- Links de convite temporários (30 min)

### 🎮 **Gestão de Comunidade**
- Sistema de regras obrigatórias
- Tópicos restritos até aceitação
- Mensagens apenas em canais específicos

### ⏰ **Automação Avançada**
- Checkup diário de usuários ativos
- Remoção automática de contratos cancelados
- Notificações para administradores

### 📊 **Monitoramento**
- Logs detalhados de todas as ações
- Dashboard de atividade
- Relatórios de uso

---

## 🚀 **INÍCIO RÁPIDO**

### 📦 **Instalação Automática (Recomendado)**
```bash
# 1. Clone o projeto
git clone https://github.com/GustSR/oncabito-gaming-bot.git
cd oncabito-gaming-bot

# 2. Execute o instalador
./deployment/install.sh

# 3. Configure credenciais
nano .env

# 4. Deploy do bot
./deployment/deploy.sh
```

### 🔧 **Desenvolvimento Local**
```bash
# 1. Ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate   # Windows

# 2. Dependências
pip install -r requirements.txt

# 3. Configuração
cp .env.example .env
nano .env

# 4. Execução
python main.py
```

---

## 📁 **ESTRUTURA DO PROJETO**

```
oncabito-bot/
├── 📁 src/                    # Código fonte
│   └── sentinela/
│       ├── bot/               # Handlers do Telegram
│       ├── clients/           # APIs (HubSoft, Database)
│       ├── services/          # Lógica de negócio
│       └── core/              # Configurações base
├── 📁 scripts/                # Scripts de automação
├── 📁 deployment/             # Deploy e instalação
│   ├── install.sh             # Instalador automático
│   ├── deploy.sh              # Deploy do bot
│   └── run_checkup.sh         # Checkup manual
├── 📁 tools/                  # Utilitários e testes
├── 📁 docs/                   # Documentação completa
├── 📁 data/                   # Banco de dados (criado automaticamente)
├── 📁 logs/                   # Logs do sistema
├── 🔧 .env                    # Configurações (não commitar)
├── 🐳 Dockerfile             # Container Docker
└── 📖 README.md              # Este arquivo
```

---

## ⚙️ **CONFIGURAÇÃO**

### 🔑 **Variáveis Obrigatórias (.env)**
```bash
# Bot Telegram
TELEGRAM_TOKEN=seu_token_do_botfather
TELEGRAM_GROUP_ID="-100123456789"

# API HubSoft
HUBSOFT_HOST="https://api.oncabo.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="77"
HUBSOFT_CLIENT_SECRET="sua_secret"
HUBSOFT_USER="bottelegram@oncabo.com.br"
HUBSOFT_PASSWORD="sua_senha"

# Tópicos do Telegram
RULES_TOPIC_ID="87"          # ID do tópico de regras
WELCOME_TOPIC_ID="89"        # ID do tópico de boas-vindas

# Configurações
INVITE_LINK_EXPIRE_TIME=1800  # 30 minutos
DATABASE_FILE=database/sentinela.db
```

### 🎯 **Como Obter IDs dos Tópicos**
Siga o guia: **[docs/TOPICS_DISCOVERY_GUIDE.md](docs/TOPICS_DISCOVERY_GUIDE.md)**

---

## 🐳 **DOCKER**

### 📦 **Build Manual**
```bash
docker build -t oncabito-bot .
docker run -d --name oncabito-bot --env-file .env oncabito-bot
```

### 📊 **Comandos Úteis**
```bash
# Status
docker ps | grep oncabito-bot

# Logs
docker logs -f oncabito-bot

# Restart
docker restart oncabito-bot

# Bash interno
docker exec -it oncabito-bot /bin/bash
```

---

## 📚 **DOCUMENTAÇÃO**

### 📖 **Guias Principais**
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Instalação em servidor
- **[Topics Setup](docs/TOPICS_SETUP_GUIDE.md)** - Configuração de tópicos
- **[Messages Templates](docs/MENSAGENS_TOPICOS.md)** - Templates para tópicos

### 🔧 **Guias Técnicos**
- **[Topics Discovery](docs/TOPICS_DISCOVERY_GUIDE.md)** - Auto-descoberta de IDs
- **[Restricted Topics](docs/RESTRICTED_TOPICS_GUIDE.md)** - Sistema de permissões
- **[Notifications](docs/NOTIFICATIONS_SETUP.md)** - Configuração de alertas

---

## 🛠️ **COMANDOS UTILITÁRIOS**

### ⏰ **Checkups e Monitoramento**
```bash
# Checkup manual
./deployment/run_checkup.sh

# Teste do cron
./tools/test_cron.sh

# Validação do sistema
python scripts/validate_checkup.py
```

### 🧪 **Testes e Debug**
```bash
# Teste de configuração
./tools/test_config_final.sh

# Logs do checkup
tail -f logs/checkup.log

# Status do banco
docker exec oncabito-bot python3 -c "
from src.sentinela.clients.db_client import get_all_active_users
print(f'Usuários ativos: {len(get_all_active_users())}')
"
```

---

## 🔄 **AUTOMAÇÃO**

### ⏰ **Cron Jobs Configurados**
```bash
# Checkup diário às 6:00
0 6 * * * /caminho/do/projeto/deployment/run_checkup.sh

# Backup semanal (opcional)
0 3 * * 0 cp /caminho/do/projeto/data/database/sentinela.db /backup/
```

### 📊 **Monitoramento Automático**
- ✅ Verificação diária de contratos ativos
- ✅ Remoção automática de usuários inativos
- ✅ Notificações para administradores
- ✅ Logs detalhados de todas as operações

---

## 🆘 **SUPORTE E TROUBLESHOOTING**

### 🐛 **Problemas Comuns**
```bash
# Bot não responde
docker logs oncabito-bot | tail -20

# Erro de permissões
ls -la data/ logs/
sudo chown -R $USER:$USER data/ logs/

# Container não inicia
./deployment/deploy.sh

# Cron não executa
crontab -l
./tools/test_cron.sh
```

### 📞 **Onde Buscar Ajuda**
- **Issues:** GitHub Issues
- **Logs:** `logs/checkup.log` e `docker logs oncabito-bot`
- **Documentação:** Pasta `docs/`
- **Troubleshooting:** [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

---

## 🏗️ **DESENVOLVIMENTO**

### 🔧 **Setup de Dev**
```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Executar testes
pytest tests/

# Linting
flake8 src/
black src/

# Pre-commit hooks
pre-commit install
```

### 📝 **Contribuindo**
1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudanças: `git commit -m 'Adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

---

## 📄 **LICENÇA**

Este projeto é propriedade da **OnCabo Gaming Community**.

---

## 🎮 **OnCabo Gaming Community**

**Conectando gamers, criando experiências épicas!**

- 🌐 **Website:** [oncabo.com.br](https://oncabo.com.br)
- 🎮 **Telegram:** Grupo OnCabo Gaming
- 📧 **Contato:** gaming@oncabo.com.br

---

*Documentação atualizada em 23/09/2025 - OnCabito Gaming Bot v2.0*
