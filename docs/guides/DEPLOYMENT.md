# 🚀 Guia de Deploy - Sentinela Bot

## Visão Geral

O projeto tem **2 formas de deploy**:

1. **Deploy Local** - Usa `./deploy.sh` (código local)
2. **CI/CD** - GitHub Actions faz build e push pro registry (automático)

## 🏠 Deploy Local

### Quando Usar
- ✅ Desenvolvimento e testes
- ✅ Deploy manual em servidor próprio
- ✅ Mudanças rápidas sem commit

### Como Funciona

```bash
./deploy.sh
```

### O que o Script Faz

```
1. Verifica mudanças Git (apenas aviso)
2. Para container atual
3. Limpa recursos Docker não utilizados
4. Cria diretórios (data, logs, backups)
5. Verifica .env (TELEGRAM_TOKEN, GROUP_ID)
6. Build da imagem LOCAL (docker-compose build)
7. Sobe container (docker-compose up -d)
8. Aguarda 10 segundos
9. Verifica health check
10. Mostra status e logs
```

### Características
- 🔨 Build **sempre local** (usa código da sua máquina)
- ❌ **NÃO** puxa do git
- ❌ **NÃO** usa imagem do registry
- ✅ Usa `docker-compose build` (Dockerfile local)

### Pré-requisitos

```bash
# 1. Docker e Docker Compose instalados
docker --version
docker-compose --version

# 2. Arquivo .env configurado
cp .env.example .env
nano .env  # Configure TELEGRAM_TOKEN e GROUP_ID

# 3. Permissão de execução
chmod +x deploy.sh
```

### Variáveis Obrigatórias (.env)

```env
# Telegram (OBRIGATÓRIO)
TELEGRAM_TOKEN="seu_token_aqui"
TELEGRAM_GROUP_ID="id_do_grupo"

# HubSoft (OPCIONAL - pode usar modo mock)
HUBSOFT_ENABLED=false  # ou true se tiver API
HUBSOFT_HOST="https://api.hubsoft.com.br"
HUBSOFT_CLIENT_ID="seu_client_id"
HUBSOFT_CLIENT_SECRET="seu_secret"
```

### Exemplo de Uso

```bash
# Deploy completo
./deploy.sh

# Ver logs ao vivo
docker-compose logs -f

# Parar bot
docker-compose down

# Reiniciar apenas o bot
docker-compose restart

# Ver status
docker-compose ps
```

## 🤖 CI/CD (GitHub Actions)

### Quando Usar
- ✅ Deploy em produção
- ✅ Múltiplos servidores
- ✅ Build automatizado após merge

### Como Funciona

**Trigger:** Push para `main` branch

```yaml
# .github/workflows/deploy.yml (futuro)
on:
  push:
    branches: [main]

jobs:
  build-and-push:
    - Build da imagem Docker
    - Push para ghcr.io/gustsr/oncabo-gaming-bot:latest
    - Tag com versão (v1.0.0)
```

### Características
- 🔨 Build **automático** no GitHub
- 📦 Publica no **GitHub Container Registry**
- 🏷️ Tags versionadas (v1.0.0, v1.0.1, etc)
- 🚀 Servidores apenas baixam imagem pronta

### Registry

```bash
# Imagem disponível em:
ghcr.io/gustsr/oncabo-gaming-bot:latest
ghcr.io/gustsr/oncabo-gaming-bot:v1.0.0
```

### Deploy em Produção (Usando Registry)

```bash
# Servidor de produção puxa imagem pronta
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📊 Comparação

| Característica | Deploy Local (`./deploy.sh`) | CI/CD (GitHub Actions) |
|---|---|---|
| **Build** | Local (sua máquina) | GitHub (cloud) |
| **Código** | Código local (não commitado OK) | Código commitado no Git |
| **Imagem** | Build toda vez | Baixa do registry |
| **Velocidade** | Mais lento (build completo) | Mais rápido (só download) |
| **Uso** | Dev, testes, servidor único | Produção, múltiplos servidores |
| **Automação** | Manual (`./deploy.sh`) | Automático (push to main) |

## 🐳 Docker Compose - Arquivos

### docker-compose.yml (Base)
Configuração principal usada **sempre**

```yaml
services:
  oncabo-gaming-bot:
    build: .              # Build local
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

### docker-compose.override.yml (Dev)
Automaticamente usado em **desenvolvimento**

```yaml
services:
  oncabo-gaming-bot:
    restart: "no"         # Não reinicia automaticamente
    environment:
      - PYTHONUNBUFFERED=1
```

### docker-compose.prod.yml (Prod)
Usado **explicitamente** em produção

```yaml
services:
  oncabo-gaming-bot:
    image: ghcr.io/gustsr/oncabo-gaming-bot:latest  # Usa registry
    pull_policy: always   # Sempre baixa última versão
    build: null          # Remove build local
```

## 🔧 Comandos Úteis

### Deploy e Gerenciamento

```bash
# Deploy local (desenvolvimento)
./deploy.sh

# Deploy prod (usando registry)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Parar tudo
docker-compose down

# Restart rápido (sem rebuild)
docker-compose restart

# Ver logs ao vivo
docker-compose logs -f

# Ver logs específico
docker-compose logs -f oncabo-gaming-bot

# Entrar no container
docker-compose exec oncabo-gaming-bot bash

# Ver uso de recursos
docker stats
```

### Manutenção

```bash
# Limpar containers parados
docker container prune -f

# Limpar imagens não usadas
docker image prune -a -f

# Limpar tudo (CUIDADO!)
docker system prune -a -f --volumes

# Ver espaço usado
docker system df
```

### Backup

```bash
# Backup manual do banco
docker-compose exec oncabo-gaming-bot cp /app/data/database/sentinela.db /app/data/backup-$(date +%Y%m%d).db

# Ou copiar para host
docker cp oncabo-gaming-bot:/app/data/database/sentinela.db ./backups/

# Backup automático (via docker-compose)
docker-compose --profile backup run backup
```

## 🚨 Troubleshooting

### Container não inicia

```bash
# Ver logs completos
docker-compose logs

# Verificar se .env está correto
cat .env | grep TELEGRAM_TOKEN

# Testar build manualmente
docker-compose build --no-cache
```

### Erro de permissão

```bash
# Ajustar permissões dos diretórios
chmod 755 data logs backups
chmod 644 data/database/*.db
```

### Container fica reiniciando

```bash
# Ver logs de erro
docker-compose logs --tail 50

# Parar restart loop
docker-compose down

# Tentar iniciar em foreground (ver erro)
docker-compose up
```

### Banco de dados corrompido

```bash
# Restaurar backup
cp backups/backup-YYYYMMDD.db data/database/sentinela.db

# Ou recriar do zero (PERDE DADOS!)
rm data/database/sentinela.db
docker-compose restart
```

## 📝 Checklist de Deploy

### Pré-Deploy
- [ ] `.env` configurado corretamente
- [ ] Código testado localmente
- [ ] Backup do banco de dados atual
- [ ] Verificar espaço em disco

### Deploy
- [ ] `./deploy.sh` executado com sucesso
- [ ] Container rodando (`docker-compose ps`)
- [ ] Health check OK
- [ ] Logs sem erros críticos

### Pós-Deploy
- [ ] Bot responde no Telegram
- [ ] Comandos funcionando (`/start`, `/help`)
- [ ] Integração HubSoft OK (se habilitada)
- [ ] Monitorar logs por 5-10 minutos

## 🔗 Próximos Passos

- [Guia Rápido](./QUICK_START.md)
- [Comandos do Bot](./COMMANDS.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
