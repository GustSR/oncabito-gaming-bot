# 🚀 CI/CD Setup Guide - OnCabito Bot

Guia completo para configurar deploy automático com GitHub Actions.

---

## 📋 **VISÃO GERAL**

### ✨ **O que será configurado:**
- ✅ **CI:** Testes automáticos em cada commit
- ✅ **CD:** Deploy automático no servidor
- ✅ **Pipeline:** main branch → testes → deploy
- ✅ **Rollback:** Backup automático antes do deploy

---

## 🖥️ **PARTE 1: CONFIGURAÇÃO DO SERVIDOR**

### 🔧 **1. Preparar o Servidor**

Execute no seu servidor:

```bash
# 1. Baixe o script de setup
wget https://raw.githubusercontent.com/GustSR/oncabito-gaming-bot/main/scripts/server_setup.sh

# 2. Torne executável
chmod +x server_setup.sh

# 3. Execute (NÃO como root)
./server_setup.sh
```

### 🔑 **2. Configurar SSH**

**No seu computador local:**
```bash
# Gerar chave SSH (se não tiver)
ssh-keygen -t ed25519 -C "oncabito-deploy@github"

# Copiar chave pública para o servidor
ssh-copy-id oncabito@SEU_SERVIDOR_IP
```

**No servidor:**
```bash
# Verificar se a chave foi copiada
cat /home/oncabito/.ssh/authorized_keys
```

### 📝 **3. Configurar .env no Servidor**

```bash
# No servidor, edite o .env
sudo -u oncabito nano /home/oncabito/oncabito-gaming-bot/.env
```

**Cole suas configurações:**
```bash
TELEGRAM_TOKEN=8334929310:AAFvWiJrVwm8kBssjV2yTbfIsIpCblyk60o
TELEGRAM_GROUP_ID="-1002966479273"
HUBSOFT_HOST="https://api.oncabo.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="77"
HUBSOFT_CLIENT_SECRET="DIejQ8z6PlNoIfa74gwvd672Fry8tlqHaoAQfohR"
HUBSOFT_USER="bottelegram@oncabo.com.br"
HUBSOFT_PASSWORD="TelBot@2025"
RULES_TOPIC_ID="87"
WELCOME_TOPIC_ID="89"
INVITE_LINK_EXPIRE_TIME=1800
DATABASE_FILE=data/database/sentinela.db
```

### 🧪 **4. Testar Deploy Manual**

```bash
# No servidor
sudo -u oncabito /home/oncabito/oncabito-gaming-bot/deployment/deploy.sh
```

---

## 🐙 **PARTE 2: CONFIGURAÇÃO DO GITHUB**

### 🔐 **1. Configurar Secrets**

No GitHub: **Settings → Secrets and variables → Actions**

Adicione estes **Repository secrets:**

| Nome | Valor | Descrição |
|------|-------|-----------|
| `SSH_PRIVATE_KEY` | Sua chave privada SSH | Conteúdo do arquivo `~/.ssh/id_ed25519` |
| `SSH_USER` | `oncabito` | Usuário de deploy no servidor |
| `SSH_HOST` | `SEU_SERVIDOR_IP` | IP ou domínio do servidor |
| `DEPLOY_PATH` | `/home/oncabito/oncabito-gaming-bot` | Caminho do projeto |

### 📋 **Como obter SSH_PRIVATE_KEY:**

**No seu computador:**
```bash
# Mostrar chave privada
cat ~/.ssh/id_ed25519
```

**Copie TUDO**, incluindo:
```
-----BEGIN OPENSSH PRIVATE KEY-----
...conteúdo da chave...
-----END OPENSSH PRIVATE KEY-----
```

### ✅ **2. Ativar Actions**

1. Vá em **Actions** no seu repositório
2. Click **"I understand my workflows, go ahead and enable them"**

---

## 🔄 **COMO FUNCIONA O PIPELINE**

### 📊 **Fluxo Automático:**

```mermaid
graph LR
    A[git push] → B[GitHub Actions]
    B → C[Tests]
    C → D{Tests Pass?}
    D →|Yes| E[Deploy]
    D →|No| F[❌ Stop]
    E → G[✅ Bot Online]
```

### 🧪 **Testes Executados:**
- ✅ **Lint:** Verificação de código
- ✅ **Config:** Validação de configurações
- ✅ **Import:** Teste de imports Python

### 🚀 **Deploy Automático:**
1. **Backup** do .env atual
2. **Pull** do código novo
3. **Stop** container antigo
4. **Build** nova imagem
5. **Start** novo container
6. **Verificação** de saúde

---

## 🧪 **TESTANDO O PIPELINE**

### 🎯 **1. Teste Simples**

Faça uma alteração pequena:

```bash
# No seu computador
cd "/home/gust/Repositorios Github/Sentinela"

# Altere algo simples
echo "# Teste CI/CD" >> README.md

# Commit e push
git add .
git commit -m "test: Teste do pipeline CI/CD"
git push origin main
```

### 👀 **2. Acompanhar Execução**

1. Vá em **Actions** no GitHub
2. Clique no workflow em execução
3. Acompanhe os logs em tempo real

### ✅ **3. Verificar Deploy**

**No servidor:**
```bash
# Verificar se container está rodando
docker ps | grep oncabito-bot

# Ver logs do bot
docker logs oncabito-bot --tail 20

# Status do sistema
sudo -u oncabito /home/oncabito/oncabito-gaming-bot/tools/test_config_final.sh
```

---

## 🛡️ **SEGURANÇA E BOAS PRÁTICAS**

### 🔒 **Secrets Management**
- ✅ **Nunca** commite chaves no código
- ✅ **Use** GitHub Secrets para dados sensíveis
- ✅ **Rotacione** chaves SSH regularmente

### 🚨 **Monitoramento**
- ✅ **Notificações** de falha no deploy
- ✅ **Logs** detalhados em cada etapa
- ✅ **Rollback** automático em case de erro

### 🔧 **Manutenção**
```bash
# Backup manual antes de mudanças grandes
sudo -u oncabito cp /home/oncabito/oncabito-gaming-bot/.env /backup/

# Limpar imagens Docker antigas
docker system prune -f

# Verificar espaço em disco
df -h
```

---

## 🆘 **TROUBLESHOOTING**

### ❌ **Pipeline Falha nos Testes**
```bash
# Executar testes localmente
cd "/home/gust/Repositorios Github/Sentinela"
python -m pip install -r requirements.txt
python -c "import sys; sys.path.append('src'); from sentinela.core.config import get_env_var"
```

### ❌ **Falha na Conexão SSH**
```bash
# Testar conexão SSH
ssh oncabito@SEU_SERVIDOR_IP "echo 'Conexão OK'"

# Verificar permissões
ls -la ~/.ssh/
ls -la /home/oncabito/.ssh/
```

### ❌ **Deploy Falha no Servidor**
```bash
# Logs do GitHub Actions
# Ver em: Actions → Workflow → Deploy → Logs

# Logs do servidor
sudo -u oncabito docker logs oncabito-bot
```

### ❌ **Container Não Inicia**
```bash
# Debug no servidor
sudo -u oncabito docker run -it --rm --env-file /home/oncabito/oncabito-gaming-bot/.env oncabito-bot /bin/bash
```

---

## 🎯 **PRÓXIMOS PASSOS**

### 📈 **Melhorias Futuras**
- 🔄 **Staging Environment:** Deploy em ambiente de teste
- 📊 **Monitoring:** Alertas via Telegram
- 🧪 **Tests:** Testes de integração
- 📦 **Releases:** Tags automáticas

### 🔧 **Comandos Úteis**

```bash
# Forçar novo deploy (mesmo commit)
git commit --allow-empty -m "force: Re-deploy"
git push origin main

# Ver status de todos workflows
gh run list

# Cancelar workflow em execução
gh run cancel WORKFLOW_ID
```

---

## 📞 **SUPORTE**

### 🐛 **Em caso de problemas:**
1. **Check** logs do GitHub Actions
2. **Verify** conexão SSH manual
3. **Test** deploy manual no servidor
4. **Review** configuração dos secrets

### 📚 **Documentação:**
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Deploy Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

*Guia criado em 23/09/2025 - OnCabito Gaming Bot v2.0*