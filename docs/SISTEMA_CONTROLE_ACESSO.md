# Sistema de Controle de Acesso

Este documento descreve o sistema completo de controle de acesso implementado para separar comandos por níveis de permissão, garantindo que apenas usuários autorizados possam executar comandos administrativos.

## 📋 Visão Geral

O sistema foi desenvolvido para resolver a necessidade de:
- **Separar comandos por níveis de acesso** (usuário comum vs admin)
- **Proteger comandos administrativos** de acesso não autorizado
- **Fornecer feedback claro** sobre permissões e comandos disponíveis
- **Facilitar o gerenciamento** de permissões

## 🏗️ Arquitetura

### Níveis de Acesso

```python
class AccessLevel(Enum):
    USER = "user"           # Usuários comuns (verificados)
    ADMIN = "admin"         # Administradores do sistema
    SUPER_ADMIN = "super_admin"  # Super administradores (futuro)
```

### Distribuição de Comandos

#### 👤 **Usuários Comuns (USER):**
- `/start` - Verificação de CPF e acesso ao sistema
- `/status` - Consulta status dos atendimentos
- `/suporte` - Abertura de chamados de suporte
- `/help` - Lista de comandos disponíveis

#### 👑 **Administradores (ADMIN):**
- **Todos os comandos de usuário comum** +
- `/test_group` - Teste de acesso ao grupo
- `/topics` - Lista tópicos descobertos
- `/auto_config` - Configuração automática de tópicos
- `/test_topics` - Teste de configuração de tópicos
- `/scan_topics` - Descoberta forçada de tópicos
- `/admin_tickets` - Consulta avançada de tickets
- `/sync_tickets` - Sincronização manual HubSoft
- `/health_hubsoft` - Status da integração HubSoft

## 🔒 Sistema de Verificação

### Determinação de Nível de Acesso

```python
def get_user_access_level(user_id: int) -> AccessLevel:
    # 1. Verifica se está na lista de ADMIN_USER_IDS
    if user_id in ADMIN_USER_IDS:
        return AccessLevel.ADMIN

    # 2. Verifica se é usuário verificado (tem CPF no sistema)
    user_data = get_user_data(user_id)
    if user_data and user_data.get('cpf'):
        return AccessLevel.USER

    # 3. Fallback para usuário básico
    return AccessLevel.USER
```

### Verificação de Permissões

O sistema oferece duas formas de verificação:

#### 1. **Por Nível de Acesso** (`@require_access`)
```python
@require_access(AccessLevel.ADMIN)
async def admin_command(update, context):
    # Comando que requer nível de admin
```

#### 2. **Por Comando Específico** (`@require_command_permission`)
```python
@require_command_permission("admin_tickets")
async def admin_tickets_command(update, context):
    # Comando que verifica permissão específica
```

## 🛡️ Implementação dos Decorators

### `@require_command_permission`

Usado na maioria dos comandos para verificação específica:

```python
@require_command_permission("sync_tickets")
async def sync_tickets_command(update, context):
    # Não precisa mais verificar ADMIN_USER_IDS manualmente
    # O decorator se encarrega de tudo
```

**Vantagens:**
- ✅ Verificação automática baseada na configuração
- ✅ Mensagens de erro padronizadas
- ✅ Log automático de tentativas não autorizadas
- ✅ Fácil manutenção das permissões

## 🔧 Configuração de Permissões

### Arquivo de Configuração
As permissões são centralizadas em `src/sentinela/core/access_control.py`:

```python
COMMAND_PERMISSIONS = {
    AccessLevel.USER: {
        "start", "status", "suporte", "help"
    },
    AccessLevel.ADMIN: {
        # Inclui todos os comandos de usuário comum
        "start", "status", "suporte", "help",
        # Comandos administrativos
        "admin_tickets", "sync_tickets", "health_hubsoft",
        "test_group", "topics", "auto_config", "test_topics", "scan_topics"
    }
}
```

### Administradores
Configurados via variável de ambiente `ADMIN_USER_IDS` no `.env`:

```bash
ADMIN_USER_IDS=[123456789, 987654321]
```

## 💬 Sistema de Feedback

### Mensagens de Erro Contextuais

#### Comando Não Autorizado:
```
🚫 Comando não autorizado

O comando /admin_tickets existe, mas não está disponível para seu nível de acesso.

👤 Seu nível: 👤 Usuário

💡 Comandos disponíveis para você:
• /start
• /status
• /suporte
• /help

📱 Use /help para ver detalhes dos comandos.
```

#### Comando Não Encontrado:
```
❓ Comando não encontrado

O comando /inexistente não existe no sistema.

💡 Comandos disponíveis para você:
• /start
• /status
• /suporte
• /help

📱 Use /help para ver detalhes dos comandos.
```

### Comando /help Contextual

O comando `/help` mostra apenas os comandos disponíveis para o nível do usuário:

#### Para Usuários Comuns:
```
📚 COMANDOS DISPONÍVEIS

👤 Seu nível: 👤 Usuário

🎮 COMANDOS DE USUÁRIO:
• /start - Inicia verificação de CPF e acesso ao sistema
• /status - Consulta status dos seus atendimentos
• /suporte - Abre um novo chamado de suporte
• /help - Mostra esta lista de comandos disponíveis

💡 COMO USAR:
1️⃣ Use /start se ainda não verificou seu CPF
2️⃣ Use /suporte para abrir chamados
3️⃣ Use /status para acompanhar seus tickets
```

#### Para Administradores:
```
📚 COMANDOS DISPONÍVEIS

👤 Seu nível: 👑 Administrador

🎮 COMANDOS DE USUÁRIO:
• /start - Inicia verificação de CPF e acesso ao sistema
• /status - Consulta status dos seus atendimentos
• /suporte - Abre um novo chamado de suporte
• /help - Mostra esta lista de comandos disponíveis

👑 COMANDOS ADMINISTRATIVOS:
• /admin_tickets - Consulta avançada de tickets (admin)
• /auto_config - Sugere configuração automática de tópicos
• /health_hubsoft - Verifica status da integração HubSoft
• /scan_topics - Força descoberta de tópicos via API
• /sync_tickets - Força sincronização manual de tickets
• /test_group - Testa acesso e configuração do grupo
• /test_topics - Testa configuração atual de tópicos
• /topics - Lista tópicos descobertos no grupo

🔧 RECURSOS ADMINISTRATIVOS:
• Gestão de tópicos do grupo
• Consulta avançada de tickets
• Sincronização manual HubSoft
• Monitoramento de sistema
• Health checks e diagnósticos

💡 Comandos administrativos funcionam apenas em chat privado.
```

## 📊 Logging e Monitoramento

### Logs de Acesso

#### Acesso Autorizado (Admin):
```
INFO: Acesso autorizado: @admin_user (ID: 123456789, Nível: admin) executando comando administrativo
```

#### Acesso Negado:
```
WARNING: Acesso negado: @user_comum (ID: 987654321, Nível: user) tentou acessar comando que requer admin
```

#### Comando Não Autorizado:
```
WARNING: Comando não autorizado: @user_comum (ID: 987654321) tentou usar /admin_tickets
```

## 🔄 Fluxo de Verificação

### Processo de Autorização:

1. **Usuário executa comando** → `/admin_tickets`
2. **Decorator intercepta** → `@require_command_permission("admin_tickets")`
3. **Determina nível do usuário** → `get_user_access_level(user_id)`
4. **Verifica permissão** → `has_permission(user_id, "admin_tickets")`
5. **Resultado:**
   - ✅ **Autorizado**: Executa comando original
   - ❌ **Negado**: Envia mensagem de erro + log

### Handler de Comandos Desconhecidos:

1. **Usuário digita comando** → `/comando_inexistente`
2. **Nenhum handler específico encontrado**
3. **Handler genérico intercepta** → `handle_unknown_command`
4. **Verifica se comando existe no sistema**
5. **Envia mensagem apropriada:**
   - Comando existe mas sem permissão
   - Comando não existe

## 🚀 Benefícios Implementados

### 🔒 **Segurança:**
- ✅ Comandos administrativos protegidos
- ✅ Verificação automática de permissões
- ✅ Log de tentativas não autorizadas
- ✅ Mensagens de erro que não revelam estrutura interna

### 👥 **Experiência do Usuário:**
- ✅ Mensagens de erro claras e úteis
- ✅ Comando `/help` contextual
- ✅ Lista apenas comandos disponíveis
- ✅ Orientação sobre como usar o sistema

### 🔧 **Manutenibilidade:**
- ✅ Configuração centralizada de permissões
- ✅ Decorators reutilizáveis
- ✅ Fácil adição de novos comandos
- ✅ Separação clara de responsabilidades

### 📈 **Escalabilidade:**
- ✅ Suporte a múltiplos níveis de acesso
- ✅ Sistema preparado para SUPER_ADMIN
- ✅ Verificação baseada em configuração
- ✅ Extensível para novos tipos de permissão

## 📝 Como Adicionar Novo Comando

### 1. Definir Nível de Acesso
```python
# Em access_control.py
COMMAND_PERMISSIONS = {
    AccessLevel.ADMIN: {
        # ... comandos existentes ...
        "novo_comando"  # Adicionar aqui
    }
}
```

### 2. Criar Handler com Decorator
```python
@require_command_permission("novo_comando")
async def novo_comando_handler(update, context):
    # Implementação do comando
    pass
```

### 3. Registrar Handler
```python
# Em handlers.py register_handlers()
application.add_handler(CommandHandler("novo_comando", novo_comando_handler))
```

### 4. Adicionar Descrição ao /help
```python
# Em help_command
command_descriptions = {
    # ... descrições existentes ...
    "novo_comando": "Descrição do novo comando"
}
```

O sistema está completamente implementado e pronto para uso, fornecendo controle granular de acesso com excelente experiência do usuário e facilidade de manutenção.