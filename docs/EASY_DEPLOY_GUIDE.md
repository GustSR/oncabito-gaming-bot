# 🚀 Deploy Super Fácil - OnCabito Bot

Deploy automático com **GitHub Container Registry** + **Docker Compose**

---

## ⚡ **MÉTODO SUPER FÁCIL**

### 🖥️ **No Servidor (1 comando só!)**

```bash
curl -fsSL https://raw.githubusercontent.com/GustSR/oncabito-gaming-bot/main/scripts/easy_setup.sh | bash
```

**Pronto!** Isso instala tudo automaticamente.

---

## 🐙 **No GitHub (3 secrets apenas)**

### 🔐 **Configurar Secrets**

No GitHub: **Settings → Secrets → Actions**

| Nome | Valor | Exemplo |
|------|-------|---------|
| `SERVER_HOST` | IP do servidor | `123.456.789.10` |
| `SERVER_USER` | Usuário SSH | `root` ou `ubuntu` |
| `SERVER_SSH_KEY` | Chave privada SSH | Conteúdo de `~/.ssh/id_rsa` |

### 🔑 **Como pegar SSH_KEY:**

```bash
# Gerar chave (se não tiver)
ssh-keygen -t rsa -b 4096

# Mostrar chave privada
cat ~/.ssh/id_rsa

# Copiar chave pública para servidor
ssh-copy-id user@servidor
```

---

## 🚀 **Como Funciona**

### 📊 **Fluxo Automático:**

1. **Push** para main
2. **GitHub** builda imagem Docker
3. **Publica** no GitHub Container Registry
4. **SSH** para seu servidor
5. **Pull** da nova imagem
6. **Restart** do container
7. **✅ Bot online!**

### 🐳 **Vantagens do Docker:**

- ✅ **Sem dependências** no servidor
- ✅ **Deploy em segundos**
- ✅ **Rollback fácil**
- ✅ **Não precisa compilar no servidor**
- ✅ **Funciona em qualquer Linux**

---

## 🛠️ **Comandos no Servidor**

### 📁 **Navegar para o projeto:**
```bash
cd /opt/oncabito-bot
```

### 🚀 **Deploy manual:**
```bash
./deploy.sh
```

### 📋 **Ver logs:**
```bash
./logs.sh
```

### 💾 **Fazer backup:**
```bash
./backup.sh
```

### 📊 **Status:**
```bash
docker-compose ps
```

### 🛑 **Parar bot:**
```bash
docker-compose down
```

---

## ⚙️ **Configuração (.env)**

### 📝 **Editar configurações:**
```bash
cd /opt/oncabito-bot
nano .env
```

### 🔧 **Exemplo completo:**
```bash
# Bot Telegram
TELEGRAM_TOKEN="SEU_TOKEN_DO_BOTFATHER"
TELEGRAM_GROUP_ID="SEU_GROUP_ID"

# API HubSoft
HUBSOFT_HOST="https://api.oncabo.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="77"
HUBSOFT_CLIENT_SECRET="SEU_CLIENT_SECRET"
HUBSOFT_USER="seu_usuario@email.com"
HUBSOFT_PASSWORD="SUA_SENHA"

# Tópicos
RULES_TOPIC_ID="87"
WELCOME_TOPIC_ID="89"

# Configurações
INVITE_LINK_EXPIRE_TIME=1800
DATABASE_FILE=data/database/sentinela.db
```

### 🔄 **Aplicar mudanças:**
```bash
./deploy.sh
```

---

## 🆘 **Troubleshooting**

### ❌ **Bot não responde:**
```bash
cd /opt/oncabito-bot
docker-compose logs oncabito-bot
```

### ❌ **Deploy falha:**
```bash
# Ver se imagem foi baixada
docker images | grep oncabito

# Forçar download
docker pull ghcr.io/gustsr/oncabito-gaming-bot:latest

# Deploy novamente
./deploy.sh
```

### ❌ **Sem espaço em disco:**
```bash
# Limpar Docker
docker system prune -f

# Ver espaço
df -h
```

### ❌ **Erro de permissão:**
```bash
# Corrigir permissões
sudo chown -R $USER:$USER /opt/oncabito-bot
```

---

## 🎯 **DIFERENÇAS DOS MÉTODOS**

### 🟢 **Método Fácil (Recomendado):**
- ✅ 1 comando no servidor
- ✅ 3 secrets no GitHub
- ✅ Deploy em ~30 segundos
- ✅ Sem configuração SSH complexa
- ✅ Imagem pré-construída

### 🟡 **Método Tradicional:**
- ❌ Script complexo no servidor
- ❌ 4+ secrets no GitHub
- ❌ Deploy em ~2-3 minutos
- ❌ Configuração SSH manual
- ❌ Build na hora

---

## 📈 **Monitoramento**

### 📊 **Health Check automático:**
```bash
# Ver status de saúde
docker-compose ps

# Container deve estar "healthy"
```

### ⏰ **Backup automático (opcional):**
```bash
# Adicionar ao cron (backup diário às 3h)
echo "0 3 * * * cd /opt/oncabito-bot && ./backup.sh" | crontab -

# Ver backups
ls -la /opt/oncabito-bot/backups/
```

### 📱 **Notificações (futuro):**
- Integração com Telegram para alertas
- Webhook para Discord/Slack
- Email em caso de falhas

---

## 🔒 **Segurança**

### 🛡️ **Imagem Pública vs Privada:**
- ✅ **Pública:** Código aberto, sem secrets na imagem
- ✅ **Seguro:** Credenciais apenas no .env do servidor

### 🔐 **Boas Práticas:**
- ✅ SSH key sem senha para automação
- ✅ .env com permissões 600
- ✅ Backup criptografado (opcional)
- ✅ Firewall configurado

---

## 🎮 **Resultado Final**

### ⚡ **Deploy em segundos:**
```bash
git push origin main
# 30 segundos depois...
# ✅ Bot online com nova versão!
```

### 🔄 **Rollback rápido:**
```bash
# Se algo der errado, voltar versão anterior
docker pull ghcr.io/gustsr/oncabito-gaming-bot:commit-abc123
docker-compose down
docker-compose up -d
```

---

*Método super fácil criado em 23/09/2025 - OnCabito Gaming Bot v2.0* 🚀