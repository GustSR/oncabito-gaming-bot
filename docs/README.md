# 📚 DOCUMENTAÇÃO - ONCABITO BOT

Documentação completa do sistema OnCabito Gaming Bot.

---

## 📖 **GUIAS DISPONÍVEIS**

### 🚀 **Setup e Configuração**
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Guia completo de instalação em servidor
- **[TOPICS_SETUP_GUIDE.md](TOPICS_SETUP_GUIDE.md)** - Configuração de tópicos do Telegram
- **[TOPICS_DISCOVERY_GUIDE.md](TOPICS_DISCOVERY_GUIDE.md)** - Auto-descoberta de IDs de tópicos

### 🔒 **Sistema de Regras e Permissões**
- **[RESTRICTED_TOPICS_GUIDE.md](RESTRICTED_TOPICS_GUIDE.md)** - Sistema de tópicos restritos
- **[NOTIFICATIONS_SETUP.md](NOTIFICATIONS_SETUP.md)** - Configuração de notificações

### 💬 **Conteúdo e Mensagens**
- **[MENSAGENS_TOPICOS.md](MENSAGENS_TOPICOS.md)** - Templates de mensagens para tópicos

---

## 🎯 **INÍCIO RÁPIDO**

### 1️⃣ **Para Desenvolvedores**
```bash
# Clone e setup local
git clone https://github.com/oncabo/oncabito-bot.git
cd oncabito-bot
pip install -r requirements.txt
cp .env.example .env
# Configure o .env com suas credenciais
python main.py
```

### 2️⃣ **Para Deploy em Servidor**
```bash
# Upload para servidor e execute
./deployment/install.sh
# Configure credenciais no .env
./deployment/deploy.sh
```

### 3️⃣ **Para Configurar Tópicos**
Siga o guia: **[TOPICS_SETUP_GUIDE.md](TOPICS_SETUP_GUIDE.md)**

---

## 🔧 **ARQUITETURA DO SISTEMA**

```
OnCabito Bot
├── 🤖 Bot Core (Telegram API)
├── 🔐 Authentication (HubSoft API)
├── 💾 Database (SQLite)
├── ⏰ Scheduler (Daily Checkups)
├── 🎮 Topics Management
└── 📊 Admin Notifications
```

---

## 📞 **SUPORTE**

- **Issues:** [GitHub Issues](https://github.com/oncabo/oncabito-bot/issues)
- **Documentação:** Esta pasta `docs/`
- **Deploy:** Siga o [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

*Documentação atualizada em 23/09/2025 - OnCabito Gaming Bot v2.0*