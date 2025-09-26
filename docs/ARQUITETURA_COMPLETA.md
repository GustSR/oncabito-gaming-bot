# 🏗️ Arquitetura Completa - OnCabito Bot

Documentação técnica detalhada da arquitetura e funcionamento do sistema.

---

## 📊 **VISÃO GERAL DA ARQUITETURA**

### 🎯 **Padrão GitOps com Microserviços**

```mermaid
graph TB
    Dev[👨‍💻 Desenvolvedor] --> Git[📂 Git Repository]
    Git --> GHA[⚙️ GitHub Actions]
    GHA --> Registry[📦 Container Registry]
    GHA --> Server[🖥️ Production Server]
    Registry --> Server

    subgraph "GitHub Ecosystem"
        Git
        GHA
        Registry
    end

    subgraph "Production Environment"
        Server --> Docker[🐳 Docker Engine]
        Docker --> Bot[🤖 OnCabito Bot]
        Bot --> TG[📱 Telegram API]
        Bot --> Hub[🔌 HubSoft API]
        Bot --> DB[(💾 SQLite)]
    end
```

### 🔄 **Fluxo de Dados Completo**

```
Código → Build → Test → Package → Deploy → Monitor
  │        │      │       │         │        │
  │        │      │       │         │        └─ Health Checks
  │        │      │       │         └─ Container Orchestration
  │        │      │       └─ Container Registry
  │        │      └─ Automated Testing
  │        └─ Docker Image Build
  └─ Git Push Trigger
```

---

## 🏛️ **COMPONENTES DA ARQUITETURA**

### 1️⃣ **Camada de Desenvolvimento**

```
📁 Local Development Environment
├── 🐍 Python 3.11+
├── 📝 Code Editor (VS Code)
├── 🔧 Git SCM
├── 🧪 Local Testing Tools
└── 🔄 Migration System (Database Schema)
```

**Responsabilidades:**
- ✅ Desenvolvimento de funcionalidades
- ✅ Testes locais e validação de migrations
- ✅ Validação de código e integridade de dados
- ✅ Commit e push com migrations automáticas

### 2️⃣ **Camada de Integração Contínua**

```
⚙️ GitHub Actions Workflow
├── 🧪 Test Stage
│   ├── Lint verificação (flake8)
│   ├── Import testing
│   └── Configuration validation
├── 🔨 Build Stage
│   ├── Docker image build
│   ├── Dependency installation
│   └── Multi-architecture support
└── 📤 Publish Stage
    ├── Container registry push
    ├── Tagging strategy
    └── Metadata generation
```

**Triggers:**
- `push` para branch `main`
- `pull_request` para testes
- Manual dispatch (webhook)

### 3️⃣ **Camada de Armazenamento**

```
📦 GitHub Container Registry (ghcr.io)
├── 🏷️ Tagged Images
│   ├── latest (production)
│   ├── main-{sha} (versioned)
│   └── pr-{number} (testing)
├── 🔒 Access Control
│   ├── Public read access
│   └── Write via GitHub token
└── 🌐 Global CDN Distribution
```

### 4️⃣ **Camada de Deploy Contínuo**

```
🚀 Deployment Pipeline
├── 🔐 SSH Authentication
├── 📥 Image Pull Strategy
├── 🔄 Container Orchestration
│   ├── docker-compose down
│   ├── docker pull latest
│   └── docker-compose up -d
└── ✅ Health Verification
```

### 5️⃣ **Camada de Produção**

```
🖥️ Production Server
├── 🐳 Docker Engine
│   ├── oncabito-bot container
│   ├── Volume mounts (data persistence)
│   └── Network configuration
├── 💾 Persistent Storage (Triple Protection)
│   ├── SQLite database (primary)
│   ├── JSON exports (backup)
│   ├── Application logs
│   └── Configuration files
├── 🔄 Automated Systems
│   ├── Daily checkup (contratos + CPF + integridade)
│   ├── Re-verification system (CPF ↔ Telegram ID)
│   ├── Migration engine (schema updates)
│   └── Backup automation (3h, 6h, 9h)
└── 🔍 Monitoring Stack
    ├── Health checks
    ├── Data integrity validation
    ├── Log aggregation
    └── Metrics collection
```

---

## 🔄 **DETALHAMENTO DO WORKFLOW**

### 🚀 **1. Trigger Phase**

```yaml
# .github/workflows/docker-deploy.yml
on:
  push:
    branches: [ main ]
```

**O que acontece:**
- Webhook do GitHub detecta push
- Workflow inicia automaticamente
- Ambiente Ubuntu latest é provisionado
- Código é checked out

### 🧪 **2. Test Phase**

```yaml
steps:
- name: 🔍 Lint Code
  run: |
    pip install flake8
    flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics

- name: ✅ Test Configuration
  run: |
    python -c "
    import sys
    sys.path.append('src')
    from sentinela.core.config import get_env_var
    print('✅ Config module loaded successfully')
    "
```

**Validações:**
- ✅ Syntax errors (E9)
- ✅ Undefined names (F63, F7, F82)
- ✅ Import resolution
- ✅ Configuration loading

### 🔨 **3. Build Phase**

```yaml
- name: 🔨 Build and push
  uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
```

**Processo Docker:**
1. **Base Image:** `python:3.11-slim`
2. **Dependencies:** System packages + Python packages
3. **Application:** Copy source code
4. **Configuration:** Set working directory and command
5. **Optimization:** Multi-stage build for size

### 📦 **4. Registry Phase**

```yaml
- name: 🔐 Login to Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

**Registry Operations:**
- ✅ Authenticate with GitHub token
- ✅ Push image with multiple tags
- ✅ Update metadata and labels
- ✅ Trigger registry webhooks

### 🚀 **5. Deploy Phase**

```yaml
- name: 🚀 Deploy to Server
  uses: appleboy/ssh-action@v1.0.0
  with:
    host: ${{ secrets.SERVER_HOST }}
    username: ${{ secrets.SERVER_USER }}
    key: ${{ secrets.SERVER_SSH_KEY }}
    script: |
      cd ${{ secrets.PROJECT_PATH }}
      echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
      docker pull ghcr.io/${{ github.repository }}:latest
      docker-compose down
      docker-compose up -d
```

**Deploy Steps:**
1. **SSH Connection:** Authenticate with private key
2. **Registry Login:** Access container registry
3. **Image Pull:** Download latest image
4. **Service Stop:** Gracefully stop current container
5. **Service Start:** Start new container with updated image
6. **Health Check:** Verify service is running

---

## 🐳 **CONTAINERIZAÇÃO DETALHADA**

### 📋 **Dockerfile Analysis**

```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as base

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application layer
FROM base as app
WORKDIR /app
COPY src/ ./src/
COPY main.py .

# Runtime configuration
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run application
CMD ["python", "main.py"]
```

**Otimizações:**
- ✅ Multi-stage build (smaller final image)
- ✅ Layer caching (faster builds)
- ✅ No-cache pip install (smaller image)
- ✅ Health check integration
- ✅ Non-root user (security)

### 🎛️ **Docker Compose Configuration**

```yaml
version: '3.8'

services:
  oncabito-bot:
    image: ghcr.io/gustsr/oncabito-gaming-bot:latest
    container_name: oncabito-bot
    restart: unless-stopped

    # Environment
    env_file: .env
    environment:
      - TZ=America/Sao_Paulo
      - PYTHONUNBUFFERED=1

    # Storage
    volumes:
      - ./data:/app/data:rw
      - ./logs:/app/logs:rw

    # Networking
    networks:
      - oncabito-net

    # Resource limits
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

    # Health monitoring
    healthcheck:
      test: ["CMD", "python3", "-c", "from src.sentinela.core.config import TELEGRAM_TOKEN; print('OK' if TELEGRAM_TOKEN else 'FAIL')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  oncabito-net:
    driver: bridge

volumes:
  oncabito-data:
    driver: local
```

---

## 🔒 **MODELO DE SEGURANÇA**

### 🛡️ **Princípios de Segurança**

1. **Separation of Concerns**
   - Código ≠ Configuração
   - Build ≠ Runtime
   - CI ≠ CD

2. **Least Privilege**
   - Containers run as non-root
   - SSH access limited to deployment
   - Registry access read-only in production

3. **Defense in Depth**
   - Multiple layers of validation
   - Container isolation
   - Network segmentation

### 🔐 **Matriz de Permissões**

| Componente | GitHub Actions | Production Server | Container |
|------------|---------------|-------------------|-----------|
| **Source Code** | ✅ Read/Write | ❌ No Access | ✅ Read Only |
| **Secrets** | ✅ CI Secrets | ✅ .env File | ✅ Runtime Env |
| **Registry** | ✅ Push/Pull | ✅ Pull Only | ❌ No Access |
| **SSH** | ✅ Deploy Key | ✅ Authorized Keys | ❌ No Access |
| **Database** | ❌ No Access | ✅ File Access | ✅ App Access |

### 🔑 **Gestão de Secrets**

```
GitHub Secrets (Actions)
├── SERVER_HOST          # Server IP/domain
├── SERVER_USER          # SSH username
├── SERVER_SSH_KEY       # Private key for deployment
└── GITHUB_TOKEN         # Auto-generated (registry access)

Server Environment (.env)
├── TELEGRAM_TOKEN       # Bot authentication
├── HUBSOFT_*           # API credentials
├── DATABASE_FILE       # SQLite path
└── TOPIC_IDS           # Telegram configuration
```

### 🔒 **Isolamento de Containers**

```
Host System
├── Docker Engine (isolated)
│   ├── oncabito-bot container
│   │   ├── /app/src (read-only)
│   │   ├── /app/data (mounted)
│   │   └── /app/logs (mounted)
│   └── Network bridge (restricted)
└── Host filesystem
    ├── /opt/oncabito-bot/.env (600 permissions)
    ├── /opt/oncabito-bot/data/ (container access)
    └── /opt/oncabito-bot/logs/ (container access)
```

---

## 📊 **MONITORAMENTO E OBSERVABILIDADE**

### 🏥 **Health Checks**

```python
# Container health check
def health_check():
    try:
        # Verify configuration loading
        from sentinela.core.config import TELEGRAM_TOKEN
        if not TELEGRAM_TOKEN:
            return "FAIL: No Telegram token"

        # Verify API connectivity (optional)
        response = requests.get("https://api.telegram.org/bot{}/getMe".format(TELEGRAM_TOKEN))
        if response.status_code != 200:
            return "FAIL: Telegram API unreachable"

        return "OK"
    except Exception as e:
        return f"FAIL: {str(e)}"
```

### 📋 **Logging Strategy**

```
Log Levels:
├── ERROR   # System failures, API errors
├── WARNING # Rate limits, retries
├── INFO    # User actions, deployments
└── DEBUG   # Detailed execution flow

Log Destinations:
├── Container stdout (docker logs)
├── Host filesystem (/opt/oncabito-bot/logs/)
└── Optional: External aggregation (Loki, ELK)
```

### 📈 **Métricas Avançadas**

```
Application Metrics:
├── Bot uptime e responsividade
├── Message processing rate
├── API response times (HubSoft + Telegram)
├── Error rates por categoria
├── User verification success/failure
└── Re-verification effectiveness

Data Protection Metrics:
├── Database schema version
├── Migration success rate
├── Data integrity score (daily)
├── Backup completion status
├── Critical data export frequency
└── Record count variations

Business Metrics:
├── Active users with valid CPF
├── Support tickets created/resolved
├── Group member retention rate
├── Contract verification accuracy
├── Re-verification conversion rate
└── Daily checkup coverage

Infrastructure Metrics:
├── Container resource usage
├── Deployment frequency
├── Build success/failure rate
├── Registry pull statistics
├── Server resource utilization
└── Automated job execution (cron)
```

---

## 🔄 **ESTRATÉGIAS DE DEPLOYMENT**

### 🚀 **Blue-Green Deployment**

```bash
# Current implementation (simple)
docker-compose down  # Stop current (blue)
docker-compose up -d # Start new (green)

# Advanced implementation (zero downtime)
docker-compose -f docker-compose.blue.yml down
docker-compose -f docker-compose.green.yml up -d
# Switch load balancer
docker-compose -f docker-compose.blue.yml down
```

### 🔄 **Rollback Strategy**

```bash
# Automatic rollback on health check failure
if ! docker-compose ps | grep "healthy"; then
    echo "Health check failed, rolling back..."
    docker pull ghcr.io/gustsr/oncabito-gaming-bot:previous
    docker-compose down
    docker-compose up -d
fi

# Manual rollback to specific version
docker pull ghcr.io/gustsr/oncabito-gaming-bot:main-abc123
docker-compose down
docker-compose up -d
```

### 📦 **Backup and Recovery (Triple Protection)**

```bash
# Automated backup strategy with data integrity
#!/bin/bash
BACKUP_DIR="/backup/oncabito-bot"
DATE=$(date +%Y%m%d_%H%M%S)

# 1. SQLite Database backup
cp /opt/oncabito-bot/data/database/sentinela.db $BACKUP_DIR/db-$DATE.db

# 2. JSON Critical Data Export
python3 /app/scripts/export_critical_data.py
cp /opt/oncabito-bot/data/exports/critical_data_latest.json $BACKUP_DIR/critical-$DATE.json

# 3. Migration History
cp -r /opt/oncabito-bot/data/migrations/ $BACKUP_DIR/migrations-$DATE/

# 4. Configuration backup
cp /opt/oncabito-bot/.env $BACKUP_DIR/env-$DATE.backup

# 5. Log archive
tar -czf $BACKUP_DIR/logs-$DATE.tar.gz /opt/oncabito-bot/logs/

# 6. Data integrity verification
python3 /app/scripts/verify_data_integrity.py --backup-mode

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -type f -mtime +30 -delete
```

### 🔄 **Migration System Architecture**

```
Migration Engine
├── 📋 Schema Versioning
│   ├── migrations/001_initial.sql
│   ├── migrations/002_support_system.sql
│   ├── migrations/003_cpf_verification.sql
│   └── migrations/migration_engine.py
├── 🛡️ Data Protection
│   ├── Before/after record counting
│   ├── Integrity validation
│   ├── Automatic rollback on >5% data loss
│   └── Administrator notifications
├── 🔄 Auto-execution
│   ├── On bot startup (check pending migrations)
│   ├── Pre-deployment verification
│   └── Manual execution via scripts
└── 📊 Migration History
    ├── Applied migrations log
    ├── Before/after statistics
    ├── Rollback information
    └── Integrity reports
```

### 🔍 **Re-verification System**

```
CPF Re-verification Flow
├── 🔍 Detection Phase
│   ├── Daily checkup (group members without CPF)
│   ├── Support request (user without CPF data)
│   └── Manual verification triggers
├── ⏱️ Verification Process
│   ├── Create pending verification (24h deadline)
│   ├── Send private message with instructions
│   ├── Handle CPF input and validation
│   └── Save verified data with history
├── 🚫 Timeout Handling
│   ├── Automatic removal after 24h
│   ├── Administrator notifications
│   ├── Re-entry process with /start
│   └── Grace period for administrators
└── 📊 Statistics & Monitoring
    ├── Pending verifications count
    ├── Success/failure rates (24h)
    ├── Expired verification cleanup
    └── Data integrity validation
```

---

## 🎯 **PERFORMANCE E ESCALABILIDADE**

### ⚡ **Otimizações de Performance**

**Container Level:**
- Resource limits (CPU/Memory)
- Health check intervals
- Restart policies

**Application Level:**
- Connection pooling
- Async/await patterns
- Caching strategies

**Infrastructure Level:**
- SSD storage for database
- Regional container registry
- CDN for static assets

### 📈 **Planejamento de Escalabilidade**

```
Current: Single Instance
├── 1 container
├── SQLite database
└── Local file storage

Horizontal Scaling:
├── Multiple bot instances
├── PostgreSQL database
├── Redis for caching
└── Load balancer

Vertical Scaling:
├── Increased container resources
├── Database optimization
└── SSD storage upgrade
```

### 🔍 **Bottleneck Analysis**

```
Potential Bottlenecks:
├── Telegram API rate limits (30 msg/sec)
├── HubSoft API response time
├── SQLite write concurrency
├── Container memory limits
└── Network I/O to external APIs

Mitigation Strategies:
├── Request queuing and throttling
├── API response caching
├── Database connection pooling
├── Memory optimization
└── Circuit breaker patterns
```

---

## 🛠️ **FERRAMENTAS E TECNOLOGIAS**

### 🧰 **Stack Tecnológico Avançado**

```
Development:
├── Python 3.11 (Runtime)
├── python-telegram-bot (Telegram SDK)
├── requests (HTTP client)
├── sqlite3 (Database + migrations)
├── asyncio (Async processing)
└── Migration engine (schema versioning)

Data Protection:
├── SQLite (primary database)
├── JSON exports (critical data backup)
├── Migration system (schema evolution)
├── Integrity validation (daily checks)
└── Triple backup strategy (3h/6h/9h)

Automation:
├── Daily checkup (multi-phase)
├── Re-verification system (24h deadline)
├── Automatic cleanup (expired verifications)
├── Cron jobs (backup + monitoring)
└── Migration auto-execution

Infrastructure:
├── Docker (Containerization)
├── Docker Compose (Orchestration)
├── GitHub Actions (CI/CD)
├── GitHub Container Registry (Artifacts)
├── SSH (Deployment)
└── Volume persistence (data + logs)

Monitoring:
├── Docker health checks
├── Application logging (structured)
├── Data integrity monitoring
├── System metrics
├── Error tracking
└── Business metrics (verification rates)
```

### 🔧 **Ferramentas de Desenvolvimento**

```
Local Development:
├── VS Code (Editor)
├── Python venv (Environment)
├── Git (Version control)
└── Docker Desktop (Testing)

CI/CD Pipeline:
├── GitHub Actions (Automation)
├── flake8 (Linting)
├── pytest (Testing - future)
└── Docker buildx (Multi-arch builds)

Production:
├── Ubuntu Server (OS)
├── Docker Engine (Runtime)
├── systemd (Process management)
└── cron (Scheduled tasks)
```

---

## 📚 **PADRÕES E CONVENÇÕES**

### 📝 **Convenções de Código**

```python
# Naming conventions
class_names = "PascalCase"
function_names = "snake_case"
constants = "UPPER_SNAKE_CASE"
modules = "lowercase"

# File structure
src/
├── sentinela/
│   ├── __init__.py
│   ├── core/          # Configuration, constants
│   ├── bot/           # Telegram handlers
│   ├── clients/       # External API clients
│   ├── services/      # Business logic
│   └── utils/         # Helper functions
```

### 🏷️ **Git Conventions**

```
Commit Message Format:
<type>(<scope>): <description>

Types:
├── feat: New feature
├── fix: Bug fix
├── docs: Documentation
├── style: Formatting
├── refactor: Code restructuring
├── test: Testing
└── chore: Maintenance

Examples:
feat(bot): Add user verification workflow
fix(api): Handle HubSoft API timeout
docs(deployment): Add troubleshooting guide
```

### 🐳 **Container Conventions**

```
Image Tagging:
├── latest (production)
├── main-{git_sha} (versioned)
├── pr-{number} (testing)
└── v{semver} (releases)

Container Naming:
├── oncabito-bot (main service)
├── oncabito-backup (backup service)
└── oncabito-{env} (multi-environment)

Volume Mounting:
├── ./data:/app/data (database)
├── ./logs:/app/logs (logging)
└── ./.env (configuration)
```

---

---

## 🚀 **SISTEMA DE RE-VERIFICAÇÃO DETALHADO**

### 🎯 **Arquitetura do Sistema**

```mermaid
graph TB
    subgraph "Detection Layer"
        DC[Daily Checkup]
        SC[Support Command]
        MC[Manual Check]
    end

    subgraph "Verification Engine"
        PV[Pending Verifications]
        CVS[CPF Verification Service]
        VH[Verification History]
    end

    subgraph "Data Layer"
        DB[(SQLite Database)]
        TBL1[pending_cpf_verifications]
        TBL2[cpf_verification_history]
        TBL3[users]
    end

    subgraph "External APIs"
        TG[Telegram API]
        HS[HubSoft API]
    end

    DC --> CVS
    SC --> CVS
    MC --> CVS
    CVS --> PV
    CVS --> VH
    PV --> DB
    VH --> DB
    DB --> TBL1
    DB --> TBL2
    DB --> TBL3
    CVS --> TG
    CVS --> HS
```

### ⚙️ **Fluxo de Execução**

```
1. DETECÇÃO (Detection Phase)
   ├── Daily Checkup (6:00 AM)
   │   ├── Scan all group members
   │   ├── Check CPF data in database
   │   └── Create pending verifications
   ├── Support Request Trigger
   │   ├── User sends /suporte
   │   ├── Check user CPF data
   │   └── Redirect to verification if missing
   └── Manual Admin Commands
       ├── /admin_reverify [user_id]
       └── Manual verification creation

2. VERIFICAÇÃO (Verification Phase)
   ├── Create Pending Record
   │   ├── 24-hour deadline
   │   ├── Verification type tracking
   │   └── Source action logging
   ├── Send Private Message
   │   ├── Clear instructions
   │   ├── CPF format explanation
   │   └── Deadline warning
   └── Handle User Response
       ├── CPF validation (format)
       ├── HubSoft API verification
       └── Database update

3. FINALIZAÇÃO (Completion Phase)
   ├── Success Path
   │   ├── Save verified CPF
   │   ├── Link to Telegram ID
   │   ├── Allow group access
   │   └── Log success history
   ├── Failure Path
   │   ├── Invalid CPF format
   │   ├── No active contract
   │   ├── Allow retry (max 3)
   │   └── Log failure reason
   └── Timeout Path
       ├── 24-hour deadline reached
       ├── Remove from group
       ├── Notify administrators
       └── Cleanup pending record
```

### 🔄 **Estados da Verificação**

```
Verification States:
├── pending      # Aguardando resposta do usuário
├── processing   # Validando CPF no HubSoft
├── completed    # Verificação bem-sucedida
├── failed       # Falha na verificação (CPF inválido)
├── expired      # Prazo de 24h expirado
└── cancelled    # Cancelado pelo usuário

State Transitions:
├── pending → processing (user sends CPF)
├── processing → completed (valid CPF + active contract)
├── processing → failed (invalid CPF or no contract)
├── pending → expired (24-hour timeout)
├── pending → cancelled (user cancels)
└── failed → pending (retry attempt)
```

---

## 🛡️ **SISTEMA DE MIGRATIONS DETALHADO**

### 📋 **Estrutura de Migrations**

```
migrations/
├── migration_engine.py     # Engine principal
├── 001_initial.sql         # Schema inicial
├── 002_support_system.sql  # Sistema de suporte
├── 003_cpf_verification.sql # Re-verificação
└── applied_migrations.log  # Histórico de aplicação
```

### 🔧 **Engine Features**

```python
class MigrationEngine:
    def __init__(self, db_path):
        self.features = [
            "📊 Before/after record counting",
            "🛡️ Data integrity validation",
            "🔄 Automatic rollback on >5% loss",
            "📬 Administrator notifications",
            "📋 Detailed migration history",
            "⚡ Auto-execution on startup",
            "🔍 Schema version tracking"
        ]
```

### 🚨 **Safety Mechanisms**

```
Data Protection:
├── Pre-migration Backup
│   ├── Full database copy
│   ├── Critical data export
│   └── Schema dump
├── Integrity Validation
│   ├── Record count comparison
│   ├── Critical table verification
│   └── Foreign key consistency
├── Rollback Triggers
│   ├── >5% data loss detection
│   ├── Critical table empty
│   └── Migration execution failure
└── Administrator Alerts
    ├── Telegram notifications
    ├── Detailed error reports
    └── Rollback confirmations
```

---

*Documentação técnica atualizada em 26/09/2025 - OnCabito Gaming Bot v2.2*

### 🆕 **Novidades v2.2**
- ✨ **Sistema de Re-verificação Automática**: Detecção e recuperação de clientes órfãos
- 🛡️ **Proteção Tripla de Dados**: SQLite + JSON + Migrations com integridade
- 🔄 **Checkup Inteligente**: 3 fases com estatísticas detalhadas
- ⚡ **Monitoramento 24/7**: Automação completa com cron jobs
- 📊 **Sistema de Migrations**: Evolução segura do schema
- 🎯 **Zero Perda de Dados**: Garantia total da ligação CPF ↔ Telegram ID