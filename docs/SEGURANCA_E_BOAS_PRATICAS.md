# 🛡️ Segurança e Boas Práticas - OnCabito Bot

Guia completo de segurança, compliance e boas práticas para produção.

---

## 🎯 **PRINCÍPIOS DE SEGURANÇA**

### 🔐 **Security by Design**

```
┌─────────────────────────────────────────────────┐
│ Camadas de Segurança (Defense in Depth)        │
├─────────────────────────────────────────────────┤
│ 1. 🔒 Application Security                      │
│    ├─ Input validation                          │
│    ├─ Output encoding                           │
│    ├─ Authentication                            │
│    └─ Authorization                             │
│                                                 │
│ 2. 🐳 Container Security                        │
│    ├─ Non-root user                             │
│    ├─ Read-only filesystem                      │
│    ├─ Resource limits                           │
│    └─ Network isolation                         │
│                                                 │
│ 3. 🖥️ Infrastructure Security                   │
│    ├─ SSH key authentication                    │
│    ├─ Firewall configuration                    │
│    ├─ System updates                            │
│    └─ Access logging                            │
│                                                 │
│ 4. 🔧 Operational Security                      │
│    ├─ Secrets management                        │
│    ├─ Backup encryption                         │
│    ├─ Audit logging                             │
│    └─ Incident response                         │
└─────────────────────────────────────────────────┘
```

### 🏛️ **Compliance Framework**

**LGPD (Lei Geral de Proteção de Dados):**
- ✅ Minimização de dados
- ✅ Consentimento explícito
- ✅ Direito ao esquecimento
- ✅ Anonimização/pseudonimização
- ✅ Logs de auditoria

**OWASP Top 10:**
- ✅ A01: Broken Access Control
- ✅ A02: Cryptographic Failures
- ✅ A03: Injection
- ✅ A04: Insecure Design
- ✅ A05: Security Misconfiguration

---

## 🔒 **GESTÃO DE CREDENCIAIS**

### 🗝️ **Hierarquia de Secrets**

```
🔐 Secrets Management Hierarchy
├── 🏢 Organization Level (GitHub)
│   ├── GITHUB_TOKEN (auto-generated)
│   └── Registry access tokens
│
├── 📦 Repository Level (GitHub)
│   ├── SERVER_HOST
│   ├── SERVER_USER
│   └── SERVER_SSH_KEY
│
├── 🖥️ Server Level (.env)
│   ├── TELEGRAM_TOKEN
│   ├── HUBSOFT_* credentials
│   └── Database paths
│
└── 🐳 Container Level (runtime)
    ├── Environment variables
    └── Mounted secrets
```

### 🔐 **Implementação Segura**

**1. GitHub Secrets:**
```yaml
# .github/workflows/docker-deploy.yml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  deploy:
    steps:
    - name: SSH Deploy
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.SERVER_HOST }}        # IP do servidor
        username: ${{ secrets.SERVER_USER }}    # usuário SSH
        key: ${{ secrets.SERVER_SSH_KEY }}      # chave privada SSH
```

**2. Server Environment:**
```bash
# /opt/oncabito-bot/.env
# Permissões: 600 (read/write apenas para owner)

# Bot Telegram
TELEGRAM_TOKEN="8334929310:AAF..."  # Token do BotFather

# API HubSoft
HUBSOFT_HOST="https://api.oncabo.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="77"
HUBSOFT_CLIENT_SECRET="DIejQ8z6PlNoIfa74gwvd672Fry8tlqHaoAQfohR"
HUBSOFT_USER="bottelegram@oncabo.com.br"
HUBSOFT_PASSWORD="TelBot@2025"
```

**3. Container Runtime:**
```yaml
# docker-compose.yml
services:
  oncabito-bot:
    env_file: .env              # Carrega .env
    environment:
      - PYTHONUNBUFFERED=1      # Apenas configs não-sensíveis
    volumes:
      - ./data:/app/data:rw     # Dados isolados
      - ./logs:/app/logs:rw     # Logs isolados
```

### 🔄 **Rotação de Credenciais**

```bash
#!/bin/bash
# rotate_secrets.sh

echo "🔄 Rotação de credenciais OnCabito Bot"

# 1. Backup configuração atual
cp /opt/oncabito-bot/.env /opt/oncabito-bot/.env.backup.$(date +%Y%m%d)

# 2. Gerar novas credenciais (exemplo para SSH)
ssh-keygen -t ed25519 -f /tmp/new_deploy_key -N ""

echo "📋 Próximos passos:"
echo "1. Atualizar secrets no GitHub:"
echo "   - SERVER_SSH_KEY: $(cat /tmp/new_deploy_key)"
echo "2. Autorizar nova chave no servidor:"
echo "   - cat /tmp/new_deploy_key.pub >> ~/.ssh/authorized_keys"
echo "3. Remover chave antiga após teste"

# 3. Limpeza
rm -f /tmp/new_deploy_key /tmp/new_deploy_key.pub
```

---

## 🐳 **SEGURANÇA DE CONTAINERS**

### 🔒 **Dockerfile Seguro**

```dockerfile
# Usar imagem oficial e específica
FROM python:3.11.6-slim

# Criar usuário não-root
RUN groupadd -r oncabito && useradd -r -g oncabito oncabito

# Instalar apenas dependências necessárias
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    git=1:2.* \
    curl=7.* \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Configurar diretório de trabalho
WORKDIR /app
RUN chown oncabito:oncabito /app

# Copiar e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --no-compile \
    --user \
    -r requirements.txt

# Copiar código fonte
COPY --chown=oncabito:oncabito src/ ./src/
COPY --chown=oncabito:oncabito main.py .

# Configurar usuário e permissões
USER oncabito

# Configurar filesystem read-only
VOLUME ["/app/data", "/app/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "from src.sentinela.core.config import TELEGRAM_TOKEN; print('OK' if TELEGRAM_TOKEN else 'FAIL')" || exit 1

# Comando de execução
CMD ["python3", "main.py"]
```

### 🛡️ **Container Hardening**

```yaml
# docker-compose.yml - Configuração segura
version: '3.8'

services:
  oncabito-bot:
    image: ghcr.io/gustsr/oncabito-gaming-bot:latest

    # Segurança
    user: "1000:1000"                    # UID:GID não-root
    read_only: true                      # Filesystem read-only
    cap_drop:                            # Remove capabilities
      - ALL
    cap_add:                             # Adiciona apenas necessárias
      - NET_BIND_SERVICE

    # Recursos limitados
    deploy:
      resources:
        limits:
          memory: 512M                   # Limite de memória
          cpus: '0.5'                    # Limite de CPU
          pids: 100                      # Limite de processos
        reservations:
          memory: 256M
          cpus: '0.25'

    # Volumes específicos (não bind mount root)
    volumes:
      - ./data:/app/data:rw
      - ./logs:/app/logs:rw
      - /tmp:/tmp:rw                     # Temp files

    # Rede isolada
    networks:
      - oncabito-net

    # Restart policy
    restart: unless-stopped

    # Health check
    healthcheck:
      test: ["CMD-SHELL", "python3 -c 'from src.sentinela.core.config import TELEGRAM_TOKEN; exit(0 if TELEGRAM_TOKEN else 1)'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  oncabito-net:
    driver: bridge
    internal: false                      # Acesso externo apenas se necessário
    ipam:
      config:
        - subnet: 172.20.0.0/24         # Subnet específica
```

### 🔍 **Auditoria de Segurança**

```bash
#!/bin/bash
# security_audit.sh

echo "🔍 Auditoria de Segurança - OnCabito Bot"
echo "======================================="

# 1. Verificar permissões de arquivos
echo "📁 Permissões de arquivos:"
ls -la /opt/oncabito-bot/.env
ls -la /opt/oncabito-bot/data/
ls -la /opt/oncabito-bot/logs/

# 2. Verificar container como não-root
echo "👤 Usuário do container:"
docker exec oncabito-bot whoami
docker exec oncabito-bot id

# 3. Verificar capabilities
echo "🔐 Capabilities do container:"
docker exec oncabito-bot capsh --print

# 4. Verificar processos
echo "🔄 Processos no container:"
docker exec oncabito-bot ps aux

# 5. Verificar rede
echo "🌐 Configuração de rede:"
docker network inspect oncabito-bot_oncabito-net

# 6. Verificar volumes
echo "💾 Volumes montados:"
docker inspect oncabito-bot | jq '.[0].Mounts'

# 7. Verificar logs de segurança
echo "📋 Logs de segurança recentes:"
docker logs oncabito-bot | grep -i "auth\|error\|fail" | tail -10

echo "✅ Auditoria concluída"
```

---

## 🔐 **PROTEÇÃO DE DADOS**

### 📊 **LGPD Compliance**

**1. Minimização de Dados:**
```python
# src/sentinela/utils/data_protection.py

def mask_cpf(cpf: str) -> str:
    """Mascara CPF para logs (LGPD compliance)"""
    if len(cpf) != 11:
        return "***.***.***-**"
    return f"{cpf[:3]}.***.***.{cpf[-2:]}"

def mask_sensitive_data(data: dict) -> dict:
    """Remove/mascara dados sensíveis para logs"""
    sensitive_fields = ['password', 'token', 'secret', 'cpf']

    masked_data = data.copy()
    for key, value in masked_data.items():
        if any(field in key.lower() for field in sensitive_fields):
            masked_data[key] = "***MASKED***"

    return masked_data
```

**2. Consentimento e Transparência:**
```python
# Mensagem de boas-vindas com informações LGPD
WELCOME_MESSAGE_LGPD = """
🤖 Olá! Sou o OnCabito, seu assistente virtual!

📋 **Proteção de Dados (LGPD):**
• Coletamos apenas seu CPF para verificação
• Dados armazenados apenas para funcionamento do bot
• Não compartilhamos com terceiros
• Você pode solicitar exclusão a qualquer momento

Para continuar, confirme que concorda com o tratamento dos seus dados.
[✅ Aceito] [❌ Não aceito]
"""

def process_lgpd_consent(user_id: int, consent: bool):
    """Processa consentimento LGPD"""
    if consent:
        # Marcar consentimento no banco
        update_user_consent(user_id, True, datetime.now())
    else:
        # Bloquear interações futuras
        block_user_interactions(user_id)
```

**3. Direito ao Esquecimento:**
```python
def delete_user_data(user_id: int) -> bool:
    """Remove todos os dados do usuário (direito ao esquecimento)"""
    try:
        # 1. Remover do banco de dados
        conn = get_db_connection()

        # Backup antes da exclusão (para auditoria)
        backup_user_data(user_id)

        # Exclusão em cascata
        conn.execute("DELETE FROM user_rules WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()

        # 2. Log da operação (auditoria)
        log_audit_event("USER_DATA_DELETED", user_id, "LGPD_REQUEST")

        return True
    except Exception as e:
        log_error(f"Erro ao deletar dados do usuário {user_id}: {e}")
        return False
```

### 🔒 **Criptografia e Hashing**

```python
# src/sentinela/utils/crypto.py

import hashlib
import hmac
from cryptography.fernet import Fernet

class DataProtection:
    def __init__(self):
        # Chave derivada de variável de ambiente
        self.key = self._derive_key()
        self.cipher = Fernet(self.key)

    def _derive_key(self) -> bytes:
        """Deriva chave de criptografia de forma segura"""
        secret = os.getenv('ENCRYPTION_SECRET', 'default-secret-change-me')
        salt = b'oncabito-bot-salt'  # Salt fixo para consistency
        key = hashlib.pbkdf2_hmac('sha256', secret.encode(), salt, 100000)
        return base64.urlsafe_b64encode(key[:32])

    def encrypt_sensitive_data(self, data: str) -> str:
        """Criptografa dados sensíveis"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Descriptografa dados sensíveis"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def hash_cpf(self, cpf: str) -> str:
        """Hash irreversível do CPF para índices"""
        salt = os.getenv('CPF_SALT', 'default-salt')
        return hashlib.sha256(f"{cpf}{salt}".encode()).hexdigest()

    def verify_cpf_hash(self, cpf: str, hash_value: str) -> bool:
        """Verifica hash do CPF"""
        return self.hash_cpf(cpf) == hash_value
```

### 💾 **Backup Seguro**

```bash
#!/bin/bash
# secure_backup.sh

BACKUP_DIR="/secure/backup/oncabito-bot"
DATE=$(date +%Y%m%d_%H%M%S)
ENCRYPTION_KEY_FILE="/secure/keys/backup.key"

echo "💾 Backup seguro do OnCabito Bot"

# 1. Criar backup do banco de dados
echo "📊 Backup do banco de dados..."
docker exec oncabito-bot sqlite3 /app/data/database/sentinela.db ".backup /tmp/backup.db"
docker cp oncabito-bot:/tmp/backup.db $BACKUP_DIR/db-$DATE.db

# 2. Criptografar backup
echo "🔒 Criptografando backup..."
gpg --symmetric --cipher-algo AES256 --compress-algo 1 \
    --s2k-digest-algo SHA512 --s2k-count 65536 \
    --passphrase-file $ENCRYPTION_KEY_FILE \
    --output $BACKUP_DIR/db-$DATE.db.gpg \
    $BACKUP_DIR/db-$DATE.db

# 3. Remover backup não criptografado
rm $BACKUP_DIR/db-$DATE.db

# 4. Backup das configurações (sem credenciais)
echo "⚙️ Backup das configurações..."
cat /opt/oncabito-bot/.env | grep -v "TOKEN\|PASSWORD\|SECRET" > $BACKUP_DIR/config-$DATE.env

# 5. Verificar integridade
echo "✅ Verificando integridade..."
sha256sum $BACKUP_DIR/db-$DATE.db.gpg > $BACKUP_DIR/db-$DATE.db.gpg.sha256

# 6. Limpeza (manter apenas 30 dias)
find $BACKUP_DIR -name "*.gpg" -mtime +30 -delete
find $BACKUP_DIR -name "*.sha256" -mtime +30 -delete

# 7. Upload para storage seguro (opcional)
# rclone copy $BACKUP_DIR/db-$DATE.db.gpg secure-cloud:/oncabito-backups/

echo "✅ Backup seguro concluído: $BACKUP_DIR/db-$DATE.db.gpg"
```

---

## 🌐 **SEGURANÇA DE REDE**

### 🔥 **Configuração de Firewall**

```bash
#!/bin/bash
# firewall_setup.sh

echo "🔥 Configurando firewall para OnCabito Bot"

# Ubuntu/Debian (UFW)
if command -v ufw &> /dev/null; then
    echo "Configurando UFW..."

    # Reset rules
    ufw --force reset

    # Default policies
    ufw default deny incoming
    ufw default allow outgoing

    # SSH access (restrito)
    ufw allow from 192.168.1.0/24 to any port 22    # Rede local apenas

    # HTTPS outbound (APIs)
    ufw allow out 443
    ufw allow out 80

    # DNS
    ufw allow out 53

    # Enable firewall
    ufw --force enable
    ufw status verbose
fi

# CentOS/RHEL (firewalld)
if command -v firewall-cmd &> /dev/null; then
    echo "Configurando firewalld..."

    # Default zone
    firewall-cmd --set-default-zone=public

    # SSH (restrictive)
    firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" service name="ssh" accept'

    # HTTPS outbound
    firewall-cmd --permanent --add-service=https
    firewall-cmd --permanent --add-service=http

    # Reload
    firewall-cmd --reload
    firewall-cmd --list-all
fi

echo "✅ Firewall configurado"
```

### 🔒 **SSH Hardening**

```bash
# /etc/ssh/sshd_config - Configuração segura

# Protocol and encryption
Protocol 2
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes256-ctr
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KexAlgorithms curve25519-sha256@libssh.org,diffie-hellman-group16-sha512

# Authentication
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
MaxAuthTries 3
LoginGraceTime 30

# Session limits
MaxSessions 2
MaxStartups 2:30:10
ClientAliveInterval 300
ClientAliveCountMax 2

# Restricted access
AllowUsers oncabito                      # Apenas usuário de deploy
DenyUsers root
AllowGroups docker

# Logging
LogLevel VERBOSE
SyslogFacility AUTH

# Disable features
PermitEmptyPasswords no
PermitUserEnvironment no
X11Forwarding no
AllowTcpForwarding no
GatewayPorts no
PermitTunnel no
```

### 🌐 **Rate Limiting e DDoS Protection**

```nginx
# /etc/nginx/sites-available/oncabito-bot (se usar reverse proxy)

server {
    listen 80;
    server_name oncabito-api.oncabo.com.br;

    # Rate limiting
    location / {
        limit_req zone=api burst=10 nodelay;
        limit_conn conn_limit_per_ip 10;

        # DDoS protection
        if ($request_method !~ ^(GET|POST)$) {
            return 405;
        }

        # Block common attacks
        if ($request_uri ~ "/\.") {
            return 403;
        }

        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

# Rate limiting zones
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=1r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
}
```

---

## 📋 **MONITORAMENTO DE SEGURANÇA**

### 🔍 **Log Auditoria**

```python
# src/sentinela/utils/audit.py

import logging
import json
from datetime import datetime
from typing import Dict, Any

class SecurityAuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('security_audit')
        handler = logging.FileHandler('/app/logs/security_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, user_id: int = None,
                  details: Dict[str, Any] = None):
        """Log de eventos de segurança"""

        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'details': details or {},
            'source_ip': self._get_source_ip(),
            'session_id': self._get_session_id()
        }

        self.logger.info(json.dumps(audit_entry))

    def log_authentication(self, user_id: int, success: bool, method: str):
        """Log de tentativas de autenticação"""
        self.log_event(
            'AUTHENTICATION',
            user_id=user_id,
            details={
                'success': success,
                'method': method,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def log_data_access(self, user_id: int, data_type: str, operation: str):
        """Log de acesso a dados sensíveis"""
        self.log_event(
            'DATA_ACCESS',
            user_id=user_id,
            details={
                'data_type': data_type,
                'operation': operation,
                'compliance': 'LGPD'
            }
        )

    def log_security_incident(self, incident_type: str, severity: str,
                            details: Dict[str, Any]):
        """Log de incidentes de segurança"""
        self.log_event(
            'SECURITY_INCIDENT',
            details={
                'incident_type': incident_type,
                'severity': severity,
                'details': details,
                'requires_response': severity in ['HIGH', 'CRITICAL']
            }
        )

# Uso prático
audit_logger = SecurityAuditLogger()

# Em handlers do bot
audit_logger.log_authentication(user.id, True, 'telegram')
audit_logger.log_data_access(user.id, 'cpf', 'verification')

# Em caso de erro de segurança
audit_logger.log_security_incident(
    'UNAUTHORIZED_ACCESS_ATTEMPT',
    'MEDIUM',
    {'attempted_resource': '/admin', 'user_agent': request.headers.get('User-Agent')}
)
```

### 🚨 **Alertas de Segurança**

```python
# src/sentinela/security/alerts.py

class SecurityAlertManager:
    def __init__(self):
        self.alert_thresholds = {
            'failed_auth': 5,           # 5 falhas em 5 minutos
            'data_access_burst': 10,    # 10 acessos em 1 minuto
            'api_errors': 20            # 20 erros em 5 minutos
        }

    def check_security_metrics(self):
        """Verifica métricas de segurança e dispara alertas"""

        # Verificar tentativas de auth falhando
        failed_auths = self._count_failed_auth_last_5min()
        if failed_auths >= self.alert_thresholds['failed_auth']:
            self._send_security_alert(
                'MULTIPLE_AUTH_FAILURES',
                f'{failed_auths} tentativas de autenticação falharam nos últimos 5 minutos'
            )

        # Verificar acessos suspeitos a dados
        data_access_burst = self._count_data_access_last_1min()
        if data_access_burst >= self.alert_thresholds['data_access_burst']:
            self._send_security_alert(
                'DATA_ACCESS_BURST',
                f'{data_access_burst} acessos a dados nos últimos 1 minuto'
            )

    def _send_security_alert(self, alert_type: str, message: str):
        """Envia alerta de segurança para administradores"""

        # Telegram alert para admins
        admin_chat_id = os.getenv('ADMIN_CHAT_ID')
        if admin_chat_id:
            alert_message = f"""
🚨 **ALERTA DE SEGURANÇA**

**Tipo:** {alert_type}
**Mensagem:** {message}
**Timestamp:** {datetime.now().isoformat()}
**Servidor:** {socket.gethostname()}

Verificar logs de auditoria imediatamente.
            """
            # Enviar via Telegram API
            self._send_telegram_alert(admin_chat_id, alert_message)

        # Log crítico
        logging.critical(f"SECURITY_ALERT: {alert_type} - {message}")

        # Email alert (se configurado)
        if os.getenv('SMTP_ENABLED'):
            self._send_email_alert(alert_type, message)
```

### 📊 **Métricas de Segurança**

```bash
#!/bin/bash
# security_metrics.sh

echo "🔍 Métricas de Segurança - OnCabito Bot"
echo "======================================"

# 1. Tentativas de autenticação
echo "🔐 Tentativas de autenticação (últimas 24h):"
docker exec oncabito-bot grep "AUTHENTICATION" /app/logs/security_audit.log | \
    grep "$(date --date='1 day ago' +%Y-%m-%d)" | \
    jq -r '.details.success' | sort | uniq -c

# 2. Acessos a dados sensíveis
echo "📊 Acessos a dados sensíveis (últimas 24h):"
docker exec oncabito-bot grep "DATA_ACCESS" /app/logs/security_audit.log | \
    grep "$(date --date='1 day ago' +%Y-%m-%d)" | \
    jq -r '.details.data_type' | sort | uniq -c

# 3. Incidentes de segurança
echo "🚨 Incidentes de segurança (últimas 24h):"
docker exec oncabito-bot grep "SECURITY_INCIDENT" /app/logs/security_audit.log | \
    grep "$(date --date='1 day ago' +%Y-%m-%d)" | \
    jq -r '.details.severity' | sort | uniq -c

# 4. Conexões SSH suspeitas
echo "🔌 Conexões SSH (últimas 24h):"
grep "sshd.*Accepted\|sshd.*Failed" /var/log/auth.log | \
    grep "$(date --date='1 day ago' +%b\ %d)" | \
    awk '{print $1, $2, $3, $11}' | sort | uniq -c

# 5. Tentativas de acesso bloqueadas pelo firewall
echo "🔥 Bloqueios do firewall (últimas 24h):"
grep "UFW BLOCK" /var/log/ufw.log | \
    grep "$(date --date='1 day ago' +%b\ %d)" | \
    awk '{print $12}' | sort | uniq -c | head -10

echo "✅ Métricas coletadas"
```

---

## 🎯 **RESPOSTA A INCIDENTES**

### 🚨 **Plano de Resposta**

```
🚨 Incident Response Plan
├── 1. DETECÇÃO (0-5 min)
│   ├─ Alertas automáticos
│   ├─ Monitoramento de logs
│   └─ Relatórios de usuários
│
├── 2. ANÁLISE (5-15 min)
│   ├─ Classificação de severidade
│   ├─ Identificação do escopo
│   └─ Coleta de evidências
│
├── 3. CONTENÇÃO (15-30 min)
│   ├─ Isolamento do sistema
│   ├─ Bloqueio de acessos
│   └─ Preservação de evidências
│
├── 4. ERRADICAÇÃO (30min-2h)
│   ├─ Remoção da ameaça
│   ├─ Correção de vulnerabilidades
│   └─ Fortalecimento de segurança
│
├── 5. RECUPERAÇÃO (2-24h)
│   ├─ Restauração de serviços
│   ├─ Monitoramento intensivo
│   └─ Validação de integridade
│
└── 6. LIÇÕES APRENDIDAS (1-7 dias)
    ├─ Post-mortem analysis
    ├─ Melhoria de processos
    └─ Atualização de documentação
```

### 🔒 **Scripts de Emergência**

```bash
#!/bin/bash
# emergency_lockdown.sh

echo "🚨 LOCKDOWN DE EMERGÊNCIA - OnCabito Bot"
echo "======================================"

# 1. Parar imediatamente o bot
echo "⛔ Parando bot..."
docker-compose down

# 2. Backup de emergência
echo "💾 Backup de emergência..."
cp -r /opt/oncabito-bot/data /secure/emergency-backup-$(date +%Y%m%d_%H%M%S)/
cp /opt/oncabito-bot/.env /secure/emergency-backup-$(date +%Y%m%d_%H%M%S)/.env

# 3. Bloquear tráfego
echo "🔥 Bloqueando tráfego..."
ufw deny out 443
ufw deny out 80

# 4. Preservar logs
echo "📋 Preservando logs..."
cp -r /opt/oncabito-bot/logs /secure/incident-logs-$(date +%Y%m%d_%H%M%S)/
cp /var/log/auth.log /secure/incident-logs-$(date +%Y%m%d_%H%M%S)/

# 5. Alertar administradores
echo "📢 Alertando administradores..."
# Enviar email/SMS de emergência

# 6. Documentar incidente
echo "📝 Documentando incidente..."
cat > /secure/incident-$(date +%Y%m%d_%H%M%S).log << EOF
INCIDENT REPORT
===============
Timestamp: $(date)
System: OnCabito Bot
Action: Emergency Lockdown
Reason: Security Incident
Status: System Offline
Next Steps: Manual investigation required
EOF

echo "🔒 SISTEMA EM LOCKDOWN - Investigação manual necessária"
```

---

## 📋 **CHECKLIST DE SEGURANÇA**

### ✅ **Pre-Deploy Security Checklist**

```
🔐 SECURITY CHECKLIST - OnCabito Bot

📋 Configuração Inicial
├── ☐ Usuário não-root criado
├── ☐ SSH configurado com chaves
├── ☐ Firewall configurado e ativo
├── ☐ Sistema atualizado
└── ☐ Logs de auditoria habilitados

🔒 Secrets Management
├── ☐ .env com permissões 600
├── ☐ Secrets do GitHub configurados
├── ☐ Rotação de chaves programada
├── ☐ Backup de credenciais seguro
└── ☐ Teste de acesso com credenciais

🐳 Container Security
├── ☐ Imagem sem vulnerabilidades conhecidas
├── ☐ Container roda como não-root
├── ☐ Recursos limitados (CPU/Memory)
├── ☐ Filesystem read-only
├── ☐ Health checks configurados
└── ☐ Network isolation ativa

📊 LGPD Compliance
├── ☐ Dados sensíveis mascarados em logs
├── ☐ Consentimento implementado
├── ☐ Direito ao esquecimento implementado
├── ☐ Auditoria de acesso a dados
└── ☐ Política de retenção definida

🌐 Network Security
├── ☐ HTTPS apenas (TLS 1.2+)
├── ☐ Rate limiting configurado
├── ☐ DDoS protection ativo
├── ☐ IPs suspeitos bloqueados
└── ☐ Monitoramento de tráfego

📋 Monitoring & Alerting
├── ☐ Logs de segurança configurados
├── ☐ Alertas automáticos ativos
├── ☐ Métricas de segurança coletadas
├── ☐ Dashboard de monitoramento
└── ☐ Plano de resposta a incidentes

💾 Backup & Recovery
├── ☐ Backup automático configurado
├── ☐ Backup criptografado
├── ☐ Teste de restore realizado
├── ☐ Backup offsite configurado
└── ☐ Plano de disaster recovery

🧪 Testing
├── ☐ Penetration testing realizado
├── ☐ Vulnerability scan executado
├── ☐ Audit de configuração realizado
├── ☐ Teste de resposta a incidentes
└── ☐ Validação de compliance
```

### 📅 **Cronograma de Manutenção de Segurança**

```
🗓️ MANUTENÇÃO DE SEGURANÇA

📆 Diário
├── ☐ Verificar alertas de segurança
├── ☐ Monitorar logs de auditoria
├── ☐ Verificar backup automático
└── ☐ Status de health checks

📆 Semanal
├── ☐ Análise de logs de segurança
├── ☐ Verificar atualizações de sistema
├── ☐ Teste de conectividade
├── ☐ Revisão de métricas
└── ☐ Limpeza de logs antigos

📆 Mensal
├── ☐ Auditoria de acessos
├── ☐ Revisão de configurações
├── ☐ Teste de backup/restore
├── ☐ Vulnerability scan
└── ☐ Treinamento de segurança

📆 Trimestral
├── ☐ Penetration testing
├── ☐ Revisão de políticas
├── ☐ Atualização de documentação
├── ☐ Teste de disaster recovery
└── ☐ Audit de compliance

📆 Anual
├── ☐ Security assessment completo
├── ☐ Revisão arquitetural
├── ☐ Atualização de certificações
├── ☐ Treinamento avançado
└── ☐ Planejamento estratégico
```

---

*Documentação de segurança criada em 23/09/2025 - OnCabito Gaming Bot v2.0*