# 🚀 Deploy em Produção (Git Clone Local)

**Guia completo para fazer deploy do bot usando código local (git clone) com build de produção.**

---

## 📋 **PRÉ-REQUISITOS**

### **No Servidor:**
```bash
# 1. Docker instalado e rodando
sudo systemctl status docker

# 2. Git instalado
git --version

# 3. Porta 80/443 liberada (se usar webhook no futuro)
# 4. Mínimo 512MB RAM, 1GB recomendado
# 5. 2GB de espaço em disco
```

---

## 🎯 **PROCESSO DE DEPLOY - PASSO A PASSO**

### **OPÇÃO 1: Deploy Automático (Recomendado)** ✅

```bash
# 1. Clone o repositório
cd /opt
git clone https://github.com/SeuUsuario/Sentinela.git oncabo-bot
cd oncabo-bot

# 2. Configure o .env
cp .env.example .env
nano .env

# Configure as variáveis obrigatórias:
# - TELEGRAM_TOKEN=seu_token_do_botfather
# - TELEGRAM_GROUP_ID=-100xxxxxxxxx
# - HUBSOFT_HOST=https://api.hubsoft...
# - HUBSOFT_CLIENT_ID=...
# - HUBSOFT_CLIENT_SECRET=...
# - HUBSOFT_USER=...
# - HUBSOFT_PASSWORD=...
# - TECH_NOTIFICATION_CHANNEL_ID=-100xxxxxxxxx

# 3. Execute o deploy
./deployment/deploy-local.sh

# 4. Monitore os logs
docker logs -f oncabo-gaming-bot
```

**Pronto!** O bot está rodando em produção! 🎉

---

### **OPÇÃO 2: Deploy Manual (Controle Total)** 🔧

```bash
# 1. Clone e configure
cd /opt
git clone https://github.com/SeuUsuario/Sentinela.git oncabo-bot
cd oncabo-bot
cp .env.example .env
nano .env

# 2. Pare containers antigos (se existirem)
docker stop oncabo-gaming-bot 2>/dev/null || true
docker rm oncabo-gaming-bot 2>/dev/null || true

# 3. Build da imagem de PRODUÇÃO
docker build \
    --file Dockerfile \
    --tag oncabo-gaming-bot:latest \
    --tag oncabo-gaming-bot:$(date +%Y%m%d-%H%M%S) \
    --no-cache \
    .

# 4. Crie os diretórios necessários
mkdir -p data/database logs backups

# 5. Inicie o container
docker run -d \
    --name oncabo-gaming-bot \
    --restart unless-stopped \
    --env-file .env \
    -e TZ=America/Sao_Paulo \
    -e PYTHONUNBUFFERED=1 \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    oncabo-gaming-bot:latest

# 6. Verifique o status
docker ps | grep oncabo-gaming-bot
docker logs -f oncabo-gaming-bot
```

---

## 🔍 **VERIFICAÇÕES PÓS-DEPLOY**

### **1. Container Rodando:**
```bash
docker ps | grep oncabo-gaming-bot

# Output esperado:
# CONTAINER ID   IMAGE                        STATUS
# abc123def456   oncabo-gaming-bot:latest     Up 2 minutes (healthy)
```

### **2. Logs Saudáveis:**
```bash
docker logs oncabo-gaming-bot --tail 50

# Logs esperados:
# ✅ Sistema de logging configurado
# ✅ Migrations aplicadas com sucesso
# ✅ Injeção de dependência configurada
# ✅ Gerenciador de locks inicializado
# ✅ Bot iniciado com sucesso
```

### **3. Migrations Aplicadas:**
```bash
docker exec oncabo-gaming-bot ls -la data/database/

# Deve mostrar: sentinela.db
```

### **4. Teste o Bot:**
```
1. Abra o Telegram
2. Envie /start para o bot
3. Deve responder com formulário de CPF
```

---

## 🔄 **ATUALIZAÇÕES (GIT PULL + REDEPLOY)**

### **Atualização Rápida:**
```bash
cd /opt/oncabo-bot

# 1. Puxa código novo
git pull origin main  # ou nome da branch

# 2. Redeploy
./deployment/deploy-local.sh
```

### **Atualização Manual:**
```bash
cd /opt/oncabo-bot

# 1. Backup do .env
cp .env .env.backup

# 2. Pull do código
git pull origin main

# 3. Restaura .env se sobrescrito
cp .env.backup .env

# 4. Rebuild e restart
docker stop oncabo-gaming-bot
docker rm oncabo-gaming-bot
docker build --file Dockerfile --tag oncabo-gaming-bot:latest --no-cache .
docker run -d \
    --name oncabo-gaming-bot \
    --restart unless-stopped \
    --env-file .env \
    -e TZ=America/Sao_Paulo \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    oncabo-gaming-bot:latest
```

---

## 📊 **COMANDOS ÚTEIS**

### **Logs:**
```bash
# Logs em tempo real
docker logs -f oncabo-gaming-bot

# Últimas 100 linhas
docker logs oncabo-gaming-bot --tail 100

# Logs com timestamp
docker logs oncabo-gaming-bot --timestamps

# Salvar logs em arquivo
docker logs oncabo-gaming-bot > bot-logs.txt
```

### **Status:**
```bash
# Status do container
docker ps | grep oncabo-gaming-bot

# Informações detalhadas
docker inspect oncabo-gaming-bot

# Uso de recursos
docker stats oncabo-gaming-bot
```

### **Manutenção:**
```bash
# Restart
docker restart oncabo-gaming-bot

# Stop
docker stop oncabo-gaming-bot

# Start
docker start oncabo-gaming-bot

# Rebuild sem cache
docker build --file Dockerfile --tag oncabo-gaming-bot:latest --no-cache .

# Limpar imagens antigas
docker image prune -a
```

### **Banco de Dados:**
```bash
# Acessa banco SQLite
docker exec -it oncabo-gaming-bot sqlite3 data/database/sentinela.db

# Dentro do SQLite:
sqlite> .tables
sqlite> SELECT COUNT(*) FROM users;
sqlite> .exit

# Backup manual do banco
docker exec oncabo-gaming-bot cat data/database/sentinela.db > backup-$(date +%Y%m%d).db
```

### **Shell no Container:**
```bash
# Acessa bash dentro do container
docker exec -it oncabo-gaming-bot /bin/bash

# Dentro do container:
$ ls -la /app
$ cat /app/data/database/sentinela.db | wc -c
$ exit
```

---

## 🐛 **TROUBLESHOOTING**

### **Problema 1: Container não inicia**
```bash
# Verifica logs de erro
docker logs oncabo-gaming-bot

# Possíveis causas:
# - TELEGRAM_TOKEN inválido
# - .env mal configurado
# - Porta em uso
# - Falta de permissões
```

**Solução:**
```bash
# Valida .env
cat .env | grep TELEGRAM_TOKEN
cat .env | grep TELEGRAM_GROUP_ID

# Testa manualmente
docker run --rm --env-file .env oncabo-gaming-bot:latest python3 -c "from src.sentinela.core.config import TELEGRAM_TOKEN; print(f'Token: {TELEGRAM_TOKEN[:10]}...')"
```

### **Problema 2: Bot não responde**
```bash
# Verifica se container está rodando
docker ps | grep oncabo-gaming-bot

# Verifica logs
docker logs -f oncabo-gaming-bot

# Possíveis causas:
# - API HubSoft offline
# - Telegram API offline
# - Credenciais erradas
```

**Solução:**
```bash
# Testa conexão API
curl -I https://api.telegram.org

# Restart do container
docker restart oncabo-gaming-bot
```

### **Problema 3: Migrations falharam**
```bash
# Verifica migrations
docker exec oncabo-gaming-bot ls -la migrations/

# Verifica banco
docker exec oncabo-gaming-bot ls -la data/database/

# Logs de migrations
docker logs oncabo-gaming-bot | grep -i migration
```

**Solução:**
```bash
# Remove banco e recria
docker exec oncabo-gaming-bot rm -f data/database/sentinela.db
docker restart oncabo-gaming-bot
```

### **Problema 4: Permissões negadas**
```bash
# Verifica proprietário dos arquivos
ls -la data/ logs/

# Corrige permissões
sudo chown -R $(id -u):$(id -g) data/ logs/
chmod -R 755 data/ logs/
```

---

## 🔒 **SEGURANÇA**

### **Checklist de Segurança:**
- [ ] ✅ `.env` NÃO está commitado no git
- [ ] ✅ Container roda com usuário não-root (oncabito)
- [ ] ✅ Volumes mapeados apenas para dados (não código)
- [ ] ✅ TELEGRAM_TOKEN está protegido
- [ ] ✅ HubSoft credentials estão protegidas
- [ ] ✅ Firewall configurado corretamente
- [ ] ✅ Backups automáticos configurados

### **Proteção do .env:**
```bash
# Permissões restritas
chmod 600 .env

# Nunca commitar
echo ".env" >> .gitignore
```

---

## 📦 **DIFERENÇAS: DEV vs PRODUÇÃO**

| Aspecto | Desenvolvimento | Produção |
|---------|----------------|----------|
| **Dockerfile** | `Dockerfile.dev` | `Dockerfile` (multi-stage) |
| **Volumes** | Código mapeado (hot-reload) | Apenas dados |
| **Restart** | `no` (manual) | `unless-stopped` |
| **Build** | Single-stage | Multi-stage otimizado |
| **Cache** | Habilitado | `--no-cache` |
| **User** | oncabito | oncabito |
| **Health Check** | Não | Sim |

---

## 🎯 **RESUMO DO FLUXO DE DEPLOY**

```
1. Git Clone → /opt/oncabo-bot
2. Configure .env
3. ./deployment/deploy-local.sh
4. ✅ Bot rodando!
```

**Simples, rápido e seguro!** 🚀

---

## 📞 **SUPORTE**

**Problemas?**
1. Verifique os logs: `docker logs oncabo-gaming-bot`
2. Consulte: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
3. Abra uma issue no GitHub

**Documentos Relacionados:**
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Guia completo
- [README.md](../README.md) - Visão geral do projeto
- [INCONSISTENCIAS_RESOLUCOES.md](./INCONSISTENCIAS_RESOLUCOES.md) - Bugs corrigidos

---

*Documentação atualizada: 2025-10-20*
*Versão do Bot: 2.2*
*Status: ✅ Pronto para produção*
