# 🚀 Guia de Deploy com GitHub Container Registry

> **Última atualização:** 23 de Outubro de 2025

Este guia mostra como configurar deploy automático usando GitHub Container Registry (GHCR) com polling.

---

## 📋 Visão Geral

### **Como Funciona:**

```
Você: git push main
    ↓
GitHub Actions: Testes + Build + Push
    ↓
Imagem publicada: ghcr.io/gustsr/oncabito-gaming-bot:latest
    ↓
[10 minutos depois]
    ↓
Servidor: Cron verifica nova imagem
    ↓
Se houver atualização: Pull + Restart (30 seg)
    ↓
Bot online com nova versão! 🚀
```

### **Vantagens:**

- ✅ **Deploy automático** - Push e esqueça
- ✅ **Super rápido** - 30s vs 5 min
- ✅ **Rollback automático** - Se falhar, volta versão anterior
- ✅ **Sem downtime** - Restart rápido
- ✅ **Imagem privada** - Só você acessa
- ✅ **Build no GitHub** - Servidor não sofre

---

## 🔧 Setup Inicial (Uma Vez)

### **Parte 1: Criar Personal Access Token (PAT)**

**1. Acesse GitHub:**
```
https://github.com/settings/tokens
→ Personal access tokens
→ Tokens (classic)
→ Generate new token (classic)
```

**2. Configurar token:**
- **Name:** `oncabito-bot-registry`
- **Expiration:** `No expiration` (token permanente)
- **Scopes:**
  - ✅ `read:packages` - Baixar imagens
  - ✅ `write:packages` - Publicar imagens

**3. Copiar token:**
```
ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **IMPORTANTE:**
- Copie o token AGORA (só aparece uma vez!)
- Salve em gerenciador de senhas seguro
- NUNCA commite o token

---

### **Parte 2: Configurar Servidor**

**1. SSH no servidor:**
```bash
ssh usuario@seu-servidor.com
cd /home/usuario/oncabito-gaming-bot
```

**2. Login no GitHub Container Registry:**
```bash
echo "SEU_TOKEN_AQUI" | docker login ghcr.io -u SEU_USUARIO_GITHUB --password-stdin
```

**Exemplo:**
```bash
echo "ghp_abc123xyz..." | docker login ghcr.io -u GustSR --password-stdin
```

**Resultado esperado:**
```
Login Succeeded
```

**3. Testar pull da imagem:**
```bash
docker pull ghcr.io/gustsr/oncabito-gaming-bot:latest
```

Se funcionar: ✅ Setup OK!

---

### **Parte 3: Configurar Auto-Update (Cron)**

**1. Executar setup:**
```bash
cd /home/usuario/oncabito-gaming-bot
./deployment/setup-cron.sh
```

**2. Verificar cron instalado:**
```bash
crontab -l
```

**Deve mostrar:**
```
*/10 * * * * /home/usuario/oncabito-gaming-bot/deployment/auto-update.sh >> /home/usuario/oncabito-gaming-bot/logs/auto-update.log 2>&1
```

**3. Testar manualmente:**
```bash
./deployment/auto-update.sh
```

**4. Monitorar logs:**
```bash
tail -f logs/auto-update.log
```

---

## 🔄 Fluxo de Deploy

### **1. Desenvolvedor (Você):**

```bash
# Faz alterações no código
git add .
git commit -m "feat: nova funcionalidade"
git push origin main
```

### **2. GitHub Actions (Automático):**

```
✅ Roda testes (Python 3.10, 3.11, 3.12)
✅ Se passar: Builda imagem Docker
✅ Publica em ghcr.io/gustsr/oncabito-gaming-bot:latest
```

**Ver progresso:**
```
https://github.com/GustSR/oncabito-gaming-bot/actions
```

### **3. Servidor (Automático em até 10 min):**

```
Cron executa auto-update.sh
↓
Verifica nova imagem no registry
↓
Se nova versão: Pull + Restart
↓
Bot atualizado!
```

---

## 📊 Monitoramento

### **Ver logs de auto-update:**
```bash
tail -f logs/auto-update.log
```

### **Ver logs do bot:**
```bash
docker logs -f oncabo-gaming-bot
```

### **Ver status do container:**
```bash
docker ps | grep oncabo-gaming-bot
```

### **Ver última atualização:**
```bash
docker inspect oncabo-gaming-bot --format='{{.Created}}'
```

### **Ver versão atual (SHA):**
```bash
docker inspect oncabo-gaming-bot --format='{{.Image}}'
```

---

## 🛡️ Rollback Automático

**O que acontece se algo der errado:**

```
1. Nova versão é baixada
2. Container antigo para
3. Container novo inicia
4. Script verifica saúde (30 segundos)
5. ❌ Container não está saudável
6. 🔄 ROLLBACK AUTOMÁTICO
7. Container com versão anterior volta
8. ✅ Bot continua funcionando
9. 📝 Log registra o problema
```

**Ver backup disponível:**
```bash
docker images | grep backup
```

**Fazer rollback manual:**
```bash
# Listar backups
docker images ghcr.io/gustsr/oncabito-gaming-bot

# Rodar versão específica
docker stop oncabo-gaming-bot
docker rm oncabo-gaming-bot

docker run -d \
    --name oncabo-gaming-bot \
    --restart unless-stopped \
    --env-file .env \
    -e TZ=America/Sao_Paulo \
    -e PYTHONUNBUFFERED=1 \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    ghcr.io/gustsr/oncabito-gaming-bot:main-backup-20251023-140000
```

---

## 🔧 Troubleshooting

### **❌ Erro: "unauthorized: unauthenticated"**

**Problema:** Não está logado no registry

**Solução:**
```bash
echo "SEU_TOKEN" | docker login ghcr.io -u SEU_USUARIO --password-stdin
```

---

### **❌ Erro: "no such image"**

**Problema:** Imagem ainda não foi publicada

**Solução:**
1. Verificar se CI passou: https://github.com/GustSR/oncabito-gaming-bot/actions
2. Verificar se push foi para `main`
3. Aguardar CI terminar (~5-10 min)

---

### **❌ Cron não está executando**

**Verificar se cron está rodando:**
```bash
sudo systemctl status cron
# ou
sudo systemctl status crond
```

**Iniciar cron:**
```bash
sudo systemctl start cron
sudo systemctl enable cron
```

**Ver logs do cron:**
```bash
grep CRON /var/log/syslog | tail -20
```

---

### **❌ Auto-update não baixa nova versão**

**Verificar logs:**
```bash
tail -50 logs/auto-update.log
```

**Testar manualmente:**
```bash
./deployment/auto-update.sh
```

**Forçar pull:**
```bash
docker pull ghcr.io/gustsr/oncabito-gaming-bot:latest --no-cache
```

---

### **❌ Container não inicia após update**

**Ver logs de erro:**
```bash
docker logs oncabo-gaming-bot --tail 50
```

**Verificar .env:**
```bash
cat .env | grep TELEGRAM_TOKEN
```

**Verificar volumes:**
```bash
ls -la data/database/
ls -la logs/
```

---

## 📚 Comandos Úteis

### **Deploy Manual:**
```bash
# Forçar atualização agora (sem esperar cron)
./deployment/auto-update.sh
```

### **Pausar Auto-Update:**
```bash
# Remover cron temporariamente
crontab -e
# Comenta a linha: # */10 * * * * ...
```

### **Reativar Auto-Update:**
```bash
# Executar setup novamente
./deployment/setup-cron.sh
```

### **Limpar Imagens Antigas:**
```bash
# Remove imagens não usadas
docker image prune -a

# Remove apenas backups antigos (auto-update faz isso automaticamente)
docker images | grep backup | awk '{print $3}' | xargs docker rmi
```

### **Ver Histórico de Deploys:**
```bash
grep "ATUALIZAÇÃO CONCLUÍDA" logs/auto-update.log
```

### **Ver Versão Atual vs Registry:**
```bash
# Local
docker image inspect ghcr.io/gustsr/oncabito-gaming-bot:latest --format='{{.Id}}'

# Registry (faz pull primeiro)
docker pull ghcr.io/gustsr/oncabito-gaming-bot:latest --quiet
docker image inspect ghcr.io/gustsr/oncabito-gaming-bot:latest --format='{{.Id}}'
```

---

## 🔒 Segurança

### **Token Permanente:**

**Vantagens:**
- ✅ Setup uma vez só
- ✅ Sem manutenção
- ✅ Sem interrupções

**Precauções:**
- 🔐 Salve token em gerenciador de senhas
- 🔐 Token fica apenas no servidor (criptografado)
- 🔐 Se comprometer: revogue e crie novo

**Revogar token:**
```
GitHub → Settings → Developer Settings →
Personal Access Tokens → Revogar token antigo
```

**Criar novo token:**
- Mesmo processo do setup inicial
- Fazer login novamente no servidor

---

### **Imagem Privada:**

**Quem pode acessar:**
- ✅ Você (owner do repositório)
- ✅ Colaboradores autorizados
- ❌ Ninguém mais

**Tornar pública (se quiser):**
```
GitHub → Packages → oncabo-gaming-bot →
Package settings → Change visibility → Public
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes (Build Local) | Depois (Registry) |
|---------|---------------------|-------------------|
| **Deploy** | SSH + comandos manuais | Automático |
| **Tempo** | 5-10 min | 30-60 seg |
| **Build** | Servidor | GitHub Actions |
| **Downtime** | 2-5 min | 10-20 seg |
| **Rollback** | Manual | Automático |
| **Você precisa** | Fazer SSH | Só dar push |
| **Frequência** | Quando você quiser | A cada 10 min |

---

## 🎯 Checklist de Verificação

**Setup Inicial:**
- [ ] PAT criado no GitHub
- [ ] Docker login no servidor
- [ ] Cron instalado e configurado
- [ ] Teste manual funcionando
- [ ] Logs aparecendo corretamente

**Funcionamento Diário:**
- [ ] GitHub Actions rodando em cada push
- [ ] Imagem sendo publicada no registry
- [ ] Cron executando a cada 10 min
- [ ] Servidor baixando atualizações
- [ ] Bot atualizando automaticamente

---

## 📞 Suporte

**Problemas comuns:**
- Ver seção Troubleshooting acima
- Checar logs: `logs/auto-update.log`
- Verificar GitHub Actions
- Testar manualmente: `./deployment/auto-update.sh`

**Documentação adicional:**
- [Dockerfile](../../Dockerfile)
- [Deploy Local](../DEPLOY_PRODUCAO_LOCAL.md)
- [Testing Setup](./TESTING_SETUP.md)

---

**Última atualização:** 23/10/2025
