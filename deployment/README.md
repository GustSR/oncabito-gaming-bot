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

### ⚙️ `setup-cron.sh` - Configuração de Todos os Cron Jobs
**Quando usar**: UMA VEZ após instalar o bot no servidor

**O que faz**:
- Configura **4 cron jobs** automatizados:
  1. **Auto-Update**: Deploy automático via GHCR (cada 10 min, 00:00-05:00)
  2. **Daily Checkup**: Verificações de saúde (cada 30 min, 6:00-23:59)
  3. **Integrity Check**: Verificação de integridade do banco (diário às 6:00)
  4. **Data Export**: Backup incremental em JSON (diário às 6:30)
- Cria diretórios necessários com permissões corretas (chmod 777)
- Valida se crontab está instalado
- Mostra configuração completa e próximas execuções

**Como usar**:
```bash
cd /opt/oncabito-gaming-bot
./deployment/setup-cron.sh
```

**Verificar crons**:
```bash
crontab -l                    # Ver todos os cron jobs instalados
tail -f logs/auto-update.log  # Monitorar auto-update
tail -f logs/checkup.log      # Monitorar checkup diário
tail -f logs/integrity.log    # Monitorar verificação de integridade
tail -f logs/export.log       # Monitorar export de dados
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

### 🏥 `run_checkup.sh` - Checkup Diário Completo
**Quando usar**: Automático via cron (cada 30 min, 6:00-23:59) ou manual

**O que faz** (6 fases):
1. **Sincroniza administradores** do Telegram → banco de dados
2. **Processa conflitos de CPF** duplicados expirados (timeout 24h)
3. **Detecta CPFs duplicados** entre usuários ativos
4. **Remove verificações expiradas** de CPF não completadas
5. **Verifica contratos cancelados** na HubSoft API
6. **Remove usuários não-verificados** após 24h (protege admins)

**Executar manualmente**:
```bash
./deployment/run_checkup.sh
# ou dentro do container:
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/daily_cpf_checkup.py
```

**Logs**: `logs/checkup.log`

---

### 🔍 `run_integrity_check.sh` - Verificação de Integridade
**Quando usar**: Automático via cron (diário às 6:00) ou manual

**O que faz**:
- Verifica saúde do banco de dados SQLite
- Detecta anomalias e perda de dados (alerta se > 5%)
- Valida consistência entre tabelas relacionadas
- Gera relatório detalhado de integridade

**Executar manualmente**:
```bash
./deployment/run_integrity_check.sh
# ou dentro do container:
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/verify_data_integrity.py
```

**Logs**: `logs/integrity.log`

---

### 💾 `run_data_export.sh` - Export de Dados Críticos
**Quando usar**: Automático via cron (diário às 6:30) ou manual

**O que faz**:
- Exporta dados críticos para backup em JSON
- Inclui: usuários, verificações de CPF, tickets
- Backup incremental com timestamp
- Útil para auditoria e recuperação de desastres

**Executar manualmente**:
```bash
./deployment/run_data_export.sh
# ou dentro do container:
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/export_critical_data.py
```

**Logs**: `logs/export.log`

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
