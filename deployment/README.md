# 📦 Scripts de Deploy e Produção

Este diretório contém todos os scripts relacionados a deploy, produção e manutenção do bot OnCabito Gaming.

---

## 🚀 Scripts de Deploy

### ⭐ `auto-update.sh` - Deploy Automático (PRODUÇÃO)
**Quando usar**: No servidor de produção (roda automaticamente via cron)

**O que faz**:
- Verifica se há nova imagem no GitHub Container Registry (GHCR)
- Baixa e atualiza automaticamente quando detecta nova versão
- Sistema de rollback automático se o deploy falhar
- Verifica saúde do container após deploy
- Mantém apenas as 3 versões de backup mais recentes

**Como funciona**:
1. Compara SHA da imagem local vs remota
2. Se diferente, faz backup da imagem atual
3. Para container antigo e inicia novo com imagem atualizada
4. Verifica se está saudável, senão faz rollback

**Configuração**:
```bash
# Roda automaticamente a cada 10 minutos via cron (configurado pelo setup-cron.sh)
./auto-update.sh
```

**Logs**: `/opt/oncabito-gaming-bot/logs/auto-update.log`

---

### ⚙️ `setup-cron.sh` - Configuração Inicial do Auto-Update
**Quando usar**: UMA VEZ após instalar o bot no servidor

**O que faz**:
- Configura cron job para rodar `auto-update.sh` a cada 10 minutos
- Cria diretórios necessários com permissões corretas (chmod 777)
- Valida se crontab está instalado
- Mostra próximas execuções agendadas

**Como usar**:
```bash
cd /opt/oncabito-gaming-bot
./deployment/setup-cron.sh
```

**Verificar cron**:
```bash
crontab -l                    # Ver cron jobs instalados
tail -f logs/auto-update.log  # Monitorar execuções
```

---

### 📦 `deploy-compose.sh` - Deploy Local com Docker Compose
**Quando usar**: Desenvolvimento local, quando você quer testar mudanças rapidamente

**O que faz**:
- Usa `docker-compose.yml` para build e deploy
- Builda imagem localmente a partir do código
- Para e remove containers/imagens antigas
- Cria diretórios com permissões corretas (chmod 777)
- Valida ambiente (.env, Docker, credenciais)
- Mostra logs iniciais após deploy

**Como usar**:
```bash
cd /path/to/projeto
./deployment/deploy-compose.sh
```

**Ideal para**:
- Testar mudanças localmente antes de commitar
- Desenvolvimento onde você precisa rebuild frequente
- Ambientes onde não tem acesso ao GHCR

---

### 🏗️ `deploy-local.sh` - Deploy Local com Build Direto
**Quando usar**: Deploy local SEM docker-compose (alternativa mais manual)

**O que faz**:
- Build de imagem Docker direto (sem docker-compose)
- Configuração manual de volumes e variáveis
- Útil quando docker-compose não está disponível
- Cria imagem com tag `oncabito-bot:local`

**Diferença do deploy-compose.sh**:
- `deploy-compose.sh`: Usa docker-compose.yml (mais automático)
- `deploy-local.sh`: Build manual com `docker build` (mais controle)

**Como usar**:
```bash
cd /path/to/projeto
./deployment/deploy-local.sh
```

---

## 🔧 Scripts de Manutenção

### 🏥 `run_checkup.sh` - Checkup Diário de Saúde
**Quando usar**: Via cron para manutenção diária automática

**O que faz**:
- Executa `scripts/daily_checkup.py` dentro do container
- Verifica integridade do banco de dados
- Limpa registros expirados
- Gera relatório de saúde do sistema

**Configurar cron diário**:
```bash
# Adicionar ao crontab para rodar todo dia às 3h da manhã
0 3 * * * /opt/oncabito-gaming-bot/deployment/run_checkup.sh >> /opt/oncabito-gaming-bot/logs/checkup.log 2>&1
```

**Executar manualmente**:
```bash
./deployment/run_checkup.sh
```

---

### 📥 `install.sh` - Instalação Inicial
**Quando usar**: PRIMEIRA VEZ ao instalar o bot em um servidor novo

**O que faz**:
- Configura variável de ambiente `ONCABITO_PROJECT_DIR` no `~/.bashrc`
- Cria diretório de logs
- Torna scripts executáveis
- Prepara ambiente para primeira execução

**Como usar**:
```bash
cd /opt/oncabito-gaming-bot
./deployment/install.sh
source ~/.bashrc  # Recarrega variáveis de ambiente
```

**Após install.sh, executar**:
1. Copiar e configurar `.env`: `cp .env.example .env && nano .env`
2. Configurar auto-update: `./deployment/setup-cron.sh`
3. Fazer primeiro deploy: `./deployment/auto-update.sh`

---

## 📋 Fluxo Recomendado

### Primeira Instalação no Servidor
```bash
# 1. Clone do repositório
git clone https://github.com/GustSR/oncabito-gaming-bot.git /opt/oncabito-gaming-bot
cd /opt/oncabito-gaming-bot

# 2. Instalação inicial
./deployment/install.sh
source ~/.bashrc

# 3. Configurar credenciais
cp .env.example .env
nano .env  # Editar com suas credenciais

# 4. Login no GitHub Container Registry
echo 'SEU_TOKEN_GITHUB' | docker login ghcr.io -u SEU_USUARIO --password-stdin

# 5. Configurar auto-update
./deployment/setup-cron.sh

# 6. Primeiro deploy
./deployment/auto-update.sh

# 7. Verificar logs
tail -f logs/auto-update.log
docker logs -f oncabo-gaming-bot
```

### Desenvolvimento Local
```bash
# Opção 1: Usar helper de desenvolvimento (RECOMENDADO)
./dev.sh start    # Inicia bot
./dev.sh logs     # Ver logs
./dev.sh restart  # Reinicia após mudanças
./dev.sh rebuild  # Rebuild completo

# Opção 2: Deploy manual com docker-compose
./deployment/deploy-compose.sh

# Opção 3: Deploy manual sem compose
./deployment/deploy-local.sh
```

### Atualizar Produção
```bash
# Automático (via cron - a cada 10 minutos)
# Não precisa fazer nada, o auto-update.sh cuida disso

# Manual (forçar atualização agora)
./deployment/auto-update.sh

# Verificar status
docker ps | grep oncabo-gaming-bot
docker logs oncabo-gaming-bot --tail 50
```

---

## 🆘 Troubleshooting

### Container não inicia após deploy
```bash
# Ver logs de erro
docker logs oncabo-gaming-bot

# Verificar permissões
ls -la data/database/
# Deve estar 777 (drwxrwxrwx)

# Recriar com permissões corretas
chmod -R 777 data logs
./deployment/auto-update.sh
```

### Auto-update não está funcionando
```bash
# Verificar se cron está instalado
crontab -l | grep auto-update

# Ver logs do auto-update
tail -f logs/auto-update.log

# Testar manualmente
./deployment/auto-update.sh
```

### Banco de dados com problemas
```bash
# Executar checkup manual
./deployment/run_checkup.sh

# Backup do banco
cp data/database/sentinela.db data/database/sentinela.db.backup

# Verificar integridade
docker exec oncabo-gaming-bot sqlite3 /app/data/database/sentinela.db "PRAGMA integrity_check;"
```

---

## 📚 Referências Adicionais

- **CI/CD GitHub Actions**: `.github/workflows/deploy.yml`
- **Documentação Completa**: `docs/guides/GITHUB_REGISTRY_DEPLOY.md`
- **Helper de Desenvolvimento**: `scripts/dev/dev.sh` (symlink na raiz: `./dev.sh`)
- **Scripts de Database**: `scripts/db/`
- **Scripts de Testes**: `scripts/run_tests.sh`
