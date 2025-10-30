# 🤖 OnCabito Gaming Bot

**Bot oficial da comunidade gamer OnCabo** 🎮

Bot inteligente de moderação e gestão para grupos Telegram, integrado com o sistema ERP da OnCabo. Automatiza verificação de usuários, gerencia tópicos e mantém a comunidade organizada.

---

## ✨ **FUNCIONALIDADES**

### 🔐 **Verificação Automática Inteligente**
- Validação de CPF contra API HubSoft
- Verificação de contratos ativos
- **Re-verificação automática** quando dados são perdidos
- Detecção proativa de membros sem CPF
- Links de convite temporários (30 min)
- Sistema de migrations para preservação de dados

### 🆘 **Sistema de Suporte Completo**
- Formulário conversacional inteligente em 6 etapas
- Upload de imagens (screenshots, fotos) até 3 por ticket
- Integração automática com HubSoft ERP
- Protocolos oficiais e acompanhamento via /status
- **Sistema duplo de notificações:**
  - Notificação completa (HTML) para canal admin com dados técnicos
  - Notificação simples (Markdown) para tópico de suporte
- Anti-spam: 1 ticket a cada 30 minutos
- **Validação de tópico:** `/suporte` só funciona no tópico configurado

### 🎮 **Gestão de Comunidade**
- Sistema de regras obrigatórias
- Tópicos restritos até aceitação
- **Validação global de tópicos:** Bot só responde no tópico de suporte
- Respostas contextualizadas (privado vs grupo)
- Comandos funcionam no grupo e privado
- Mensagens apenas em canais específicos

### ⏰ **Automação Avançada**
- **Checkup diário triplo**: contratos + CPF + integridade
- Re-verificação automática de membros órfãos
- Remoção automática de contratos cancelados (24h aviso)
- **Sistema de migrations** com backup automático
- **Proteção de dados críticos** (CPF ↔ Telegram ID)
- Notificações para administradores
- Fallback automático quando HubSoft offline

### 📊 **Monitoramento e Proteção de Dados**
- **Sistema triplo de backup**: SQLite + JSON + Logs
- Verificação de integridade diária automática
- Export de dados críticos com histórico
- Detecção de anomalias (perda > 5% de dados)
- Logs estruturados de todas as ações
- Configuração flexível de integrações
- Relatórios de uso e tickets
- **Migrations com contagem before/after**

---

## 🚀 **INÍCIO RÁPIDO**

### 📦 **Instalação Automática (Recomendado)**
```bash
# Setup super fácil em 1 comando (repositório público)
curl -fsSL https://raw.githubusercontent.com/GustSR/oncabito-gaming-bot/main/scripts/easy_setup.sh | bash

# OU clonagem manual
git clone https://github.com/GustSR/oncabito-gaming-bot.git
cd oncabito-gaming-bot
./scripts/easy_setup.sh
```

### 🔄 **Deploy (após mudanças no código)**
```bash
# No servidor:
cd /opt/oncabito-bot
git pull && ./deploy.sh
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
sentinela/
├── 📁 src/sentinela/                    # Código fonte (Clean Architecture)
│   ├── application/                     # Camada de Aplicação
│   │   ├── command_handlers/            # Handlers de comandos (CQRS)
│   │   ├── commands/                    # Comandos do sistema
│   │   └── use_cases/                   # Casos de uso
│   ├── domain/                          # Camada de Domínio (DDD)
│   │   ├── entities/                    # Entidades de negócio
│   │   ├── value_objects/               # Value Objects
│   │   ├── repositories/                # Interfaces de repositórios
│   │   └── events/                      # Eventos de domínio
│   ├── infrastructure/                  # Camada de Infraestrutura
│   │   ├── repositories/                # Implementações de repositórios
│   │   ├── external_services/           # APIs externas (HubSoft)
│   │   ├── locking/                     # Sistema de locks distribuídos
│   │   └── database/                    # Conexões e migrações
│   ├── presentation/                    # Camada de Apresentação
│   │   └── handlers/                    # Handlers do Telegram Bot
│   ├── core/                            # Configurações e dependências
│   └── integrations/                    # Integrações (HubSoft, etc)
│
├── 📁 deployment/                       # Scripts de deploy e produção
│   ├── auto-update.sh                   # ⭐ Deploy automático via GHCR (PRODUÇÃO)
│   ├── setup-cron.sh                    # ⚙️ Configura auto-update (setup inicial)
│   ├── deploy-compose.sh                # 📦 Deploy local com docker-compose
│   ├── deploy-local.sh                  # 🏗️ Deploy local sem compose
│   ├── install.sh                       # 📥 Instalação inicial no servidor
│   ├── run_checkup.sh                   # 🏥 Checkup diário de saúde
│   └── README.md                        # 📖 Documentação completa dos scripts
│
├── 📁 migrations/                       # Migrations do banco
│   ├── migration_engine.py              # Engine de migrations
│   └── 00X_*.sql                        # Scripts SQL versionados
│
├── 📁 scripts/                          # Scripts utilitários
│   ├── dev/                             # 🔧 Helper de desenvolvimento (dev.sh)
│   ├── db/                              # 💾 Backup e restore de banco
│   └── run_tests.sh                     # ✅ Executa testes automatizados
│
├── 📁 docs/                             # Documentação (REORGANIZADA)
│   ├── architecture/                    # Docs de arquitetura
│   ├── guides/                          # Guias práticos
│   ├── api/                             # Docs da API HubSoft
│   ├── processes/                       # Inconsistências e processos
│   ├── analysis/                        # Análises e diagramas
│   ├── migration/                       # Histórico de migração
│   └── archive/                         # Documentos históricos
│
├── 📁 tests/                            # Testes automatizados
│   ├── unit/                            # Testes unitários
│   └── integration/                     # Testes de integração
│
├── 📁 data/                             # Dados persistentes (volumes)
│   └── database/                        # Banco SQLite
│
├── 📁 logs/                             # Logs do sistema
│
├── 🔧 .env                              # Configurações (não commitar)
├── 🔧 .env.example                      # Template de configuração
├── 🐳 Dockerfile                        # Imagem produção (multi-stage)
├── 🐳 Dockerfile.dev                    # Imagem desenvolvimento
└── 📖 README.md                         # Este arquivo
```

---

## ⚙️ **CONFIGURAÇÃO**

### 🔑 **Variáveis Obrigatórias (.env)**
```bash
# === Bot Telegram ===
TELEGRAM_TOKEN="SEU_TOKEN_DO_BOTFATHER"
TELEGRAM_GROUP_ID="-100123456789"

# === Configurações de Tópicos ===
RULES_TOPIC_ID="87"          # ID do tópico de regras
WELCOME_TOPIC_ID="89"        # ID do tópico de boas-vindas
SUPPORT_TOPIC_ID="148"       # ID do tópico de suporte gamer

# === Notificações ===
TECH_NOTIFICATION_CHANNEL_ID="-1003102389025"  # Canal técnico privado

# === Administração ===
ADMIN_USER_IDS="123456789,987654321"  # IDs dos admins

# === API HubSoft (Opcional) ===
HUBSOFT_ENABLED="true"       # true/false para habilitar integração
HUBSOFT_HOST="https://api.sua-instancia.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="SEU_CLIENT_ID"
HUBSOFT_CLIENT_SECRET="SEU_CLIENT_SECRET"
HUBSOFT_USER="seu_usuario@email.com"
HUBSOFT_PASSWORD="SUA_SENHA"

# === Configurações ===
INVITE_LINK_EXPIRE_TIME=3600  # 1 hora
DATABASE_FILE="data/database/sentinela.db"
```

### 🎯 **Como Obter IDs dos Tópicos**
Siga o guia: **[docs/TOPICS_DISCOVERY_GUIDE.md](docs/TOPICS_DISCOVERY_GUIDE.md)**

### 🤖 **Comandos do Bot**
```bash
# === Comandos para Usuários ===
/start              # Validação de CPF e acesso ao grupo
/suporte           # Abrir ticket de suporte (só funciona no tópico de suporte)
/status            # Consultar status dos seus tickets

# === Comandos Administrativos (EM DESENVOLVIMENTO) ===
# ⚠️ Atualmente exibem "Funcionalidade em manutenção"
# Veja Issue #8 para acompanhar implementação
/admin              # Menu administrativo com botões interativos
/stats              # Estatísticas do bot (planejado)

# Botões Admin (aparece no /start para admins):
# 📋 Listar Tickets - Listar tickets com filtros (planejado)
# 📊 Estatísticas - Estatísticas detalhadas do bot (planejado)
# 🔄 Sync HubSoft - Sincronizar dados com HubSoft (planejado)
# ⚙️ Configurações - Gerenciar configurações (planejado)

# === Comandos Legados (Descontinuados) ===
/topics            # Listar tópicos descobertos
/auto_config       # Gerar configuração automática de tópicos
/test_topics       # Testar configuração atual de tópicos
/scan_topics       # Escanear grupo em busca de tópicos
```

### 🎭 **Comportamento do Bot por Contexto**

O bot tem comportamentos diferentes dependendo de onde você interage com ele:

#### 📱 **No Privado (DM)**
- ✅ Responde a **todos** os comandos
- ✅ Responde a mensagens aleatórias com menu de ajuda
- ✅ Aceita fotos durante fluxo de suporte
- ✅ Processa fluxos completos de CPF e suporte
- ✅ Envia confirmações e notificações

#### 👥 **No Grupo - Tópico de Suporte** (🆘 Suporte Gamer)
- ✅ Responde ao comando `/suporte` (redireciona para privado)
- ✅ Envia notificações de novos tickets (para equipe)
- ❌ **Ignora** mensagens e fotos aleatórias
- ❌ **Ignora** outros comandos

#### 🔇 **No Grupo - Outros Tópicos**
- ❌ **Ignora TUDO** (mensagens, fotos, comandos)
- 🗑️ Deleta comando `/suporte` se enviado fora do tópico correto

**💡 Por que isso?**
Para manter o grupo organizado e evitar spam do bot em conversas não relacionadas ao suporte.

**📖 Detalhes completos:** Veja [MAPEAMENTO_RESPOSTAS_BOT.md](MAPEAMENTO_RESPOSTAS_BOT.md) para entender todas as interações

---

## 🚀 **QUICK START**

### 🏭 **Produção (Servidor)**
```bash
# 1. Clone e instale
git clone https://github.com/GustSR/oncabito-gaming-bot.git /opt/oncabito-gaming-bot
cd /opt/oncabito-gaming-bot
./deployment/install.sh

# 2. Configure credenciais
cp .env.example .env
nano .env  # Editar com suas credenciais

# 3. Login no GitHub Container Registry
echo 'SEU_TOKEN' | docker login ghcr.io -u SEU_USUARIO --password-stdin

# 4. Setup auto-update (roda a cada 10 min)
./deployment/setup-cron.sh

# 5. Primeiro deploy
./deployment/auto-update.sh

# ✅ Pronto! O bot vai atualizar automaticamente quando houver nova versão
```

### 💻 **Desenvolvimento Local**
```bash
# Opção 1: Helper de desenvolvimento (RECOMENDADO)
./dev.sh start     # Inicia bot
./dev.sh logs      # Ver logs em tempo real
./dev.sh restart   # Reinicia após mudanças no código
./dev.sh rebuild   # Rebuild completo (se mudar requirements.txt)
./dev.sh help      # Ver todos os comandos

# Opção 2: Deploy manual com docker-compose
./deployment/deploy-compose.sh

# Opção 3: Build manual Docker
docker build -t oncabito-bot:local .
docker run -d --name oncabito-bot --env-file .env -v $(pwd)/data:/app/data oncabito-bot:local
```

### 📊 **Monitoramento**
```bash
# Ver logs do bot
docker logs -f oncabo-gaming-bot
tail -f logs/auto-update.log      # Logs do auto-update

# Status do container
docker ps | grep oncabo-gaming-bot

# Executar checkup manual
./deployment/run_checkup.sh

# Acessar shell do container
docker exec -it oncabo-gaming-bot /bin/bash
```

---

## 📚 **DOCUMENTAÇÃO**

### 📖 **Guias Principais**
- **[🚀 Deploy Manual Guide](docs/DEPLOY_MANUAL_GUIDE.md)** - Deploy simplificado (NOVO)
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Instalação em servidor
- **[Topics Setup](docs/TOPICS_SETUP_GUIDE.md)** - Configuração de tópicos
- **[Messages Templates](docs/MENSAGENS_TOPICOS.md)** - Templates para tópicos
- **[🤖 Mapeamento de Respostas](MAPEAMENTO_RESPOSTAS_BOT.md)** - Todas as interações do bot (NOVO)

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
./scripts/test_cron.sh
```

### 🧪 **Testes e Debug**
```bash
# Teste completo do sistema de re-verificação
python3 scripts/test_cpf_verification.py

# Teste de configuração
./scripts/test_config_final.sh

# Verificação manual de integridade
python3 scripts/verify_data_integrity.py

# Logs do sistema
tail -f logs/checkup.log
tail -f logs/integrity_check.log
tail -f logs/backup_cron.log

# Status completo do banco
docker exec oncabito-bot python3 -c "
from src.sentinela.clients.db_client import get_all_active_users
from src.sentinela.services.cpf_verification_service import CPFVerificationService
print(f'Usuários ativos: {len(get_all_active_users())}')
stats = CPFVerificationService.get_verification_stats()
print(f'Verificações pendentes: {stats[\"pending\"]}')
print(f'Sucessos últimas 24h: {stats[\"last_24h\"][\"successful\"]}')
"
```

---

## 🔄 **AUTOMAÇÃO**

### ⏰ **Cron Jobs Configurados (Automático)**
```bash
# Setup automático via scripts/setup/setup_monitoring.sh

# Backup diário às 3:00 AM
0 3 * * * ./scripts/db/backup_database.sh auto

# Checkup completo às 6:00 AM (contratos + CPF + integridade)
0 6 * * * python3 ./scripts/daily_checkup.py

# Export de dados críticos às 9:00 AM
0 9 * * * python3 ./scripts/export_critical_data.py

# Verificação de integridade (manual)
python3 ./scripts/verify_data_integrity.py
```

### 📊 **Monitoramento Automático Completo**
- ✅ **Checkup diário triplo** (contratos + CPF + integridade)
- ✅ **Re-verificação automática** de membros sem CPF
- ✅ **Backup automático** diário às 3h
- ✅ **Verificação de integridade** às 6h
- ✅ **Export de dados críticos** às 9h
- ✅ Remoção automática de usuários inativos (com aviso 24h)
- ✅ **Proteção tripla** contra perda de dados
- ✅ Notificações para administradores
- ✅ Logs estruturados de todas as operações

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
./scripts/test_cron.sh
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

*Documentação atualizada em 30/10/2025 - OnCabito Gaming Bot v2.4*

### 🆕 **Novidades v2.4**
- 🎯 **Validação Global de Tópicos**: Bot agora só responde no tópico de suporte configurado
- 📢 **Sistema Duplo de Notificações**: Notificação completa (HTML) para admin + simples (Markdown) para suporte
- 🤖 **Respostas Contextualizadas**: Comportamento diferenciado entre privado e grupo
- 📚 **Mapeamento Completo de Respostas**: Documentação detalhada de todas as interações do bot
- 🔧 **Infraestrutura Admin Preparada**: Base para comandos administrativos (Issue #8)
- 🧹 **Limpeza de Código**: Remoção de comandos inexistentes e código morto

### 📦 **v2.3 (Anterior)**
- 🏗️ **Arquitetura Clean + DDD**: Migração completa para Clean Architecture + Domain-Driven Design
- 🔒 **Sistema de Locks Distribuídos**: Prevenção de race conditions em verificação de CPF
- 🐛 **7 Inconsistências Resolvidas**: Correção de bugs críticos identificados em auditoria
- 📦 **Deploy Local Otimizado**: Script de deploy com build local (304MB vs 757MB dev)
- 📚 **Documentação Reorganizada**: Estrutura por categorias (architecture/, processes/, analysis/)
- ⚡ **Persistência Aprimorada**: Contexto de resolução sobrevive a reinicializações
- 🎯 **Notificações Técnicas**: Canal dedicado para alertas de permissões e erros críticos
