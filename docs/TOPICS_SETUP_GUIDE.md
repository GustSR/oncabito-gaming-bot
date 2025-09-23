# 🎯 GUIA COMPLETO: BOT COM TÓPICOS E REGRAS OBRIGATÓRIAS

## 📋 **FUNCIONALIDADES IMPLEMENTADAS**

### ✅ **1. DETECÇÃO DE NOVOS MEMBROS**
- Bot detecta automaticamente quando alguém entra no grupo
- Envia mensagem de boas-vindas personalizada
- Marca usuário como "pendente de aceitar regras"

### ✅ **2. SISTEMA DE TÓPICOS**
- Bot responde **APENAS** em tópicos específicos configurados
- Ignora mensagens no grupo geral
- Suporte para tópico de regras e boas-vindas

### ✅ **3. REAÇÕES OBRIGATÓRIAS ÀS REGRAS**
- Usuários têm **24 horas** para aceitar regras
- Botão inline "✅ Li e aceito as regras"
- Remoção automática após expiração

### ✅ **4. NOTIFICAÇÕES ADMINISTRATIVAS**
- Administradores recebem relatórios de remoções
- Logs detalhados de todas as ações

---

## ⚙️ **CONFIGURAÇÃO PASSO A PASSO**

### **PASSO 1: Configurar Variáveis de Ambiente**

Adicione ao seu arquivo `.env`:

```bash
# Configurações existentes
TELEGRAM_TOKEN="seu_token_aqui"
TELEGRAM_GROUP_ID="-1001234567890"

# NOVAS CONFIGURAÇÕES DE TÓPICOS
RULES_TOPIC_ID="123"          # ID do tópico de regras (opcional)
WELCOME_TOPIC_ID="456"        # ID do tópico de boas-vindas (opcional)
```

### **PASSO 2: Descobrir IDs dos Tópicos**

#### **Método 1: Via Bot API**
1. Envie uma mensagem no tópico desejado
2. Adicione temporariamente este código no bot:
```python
print(f"Topic ID: {update.message.message_thread_id}")
```

#### **Método 2: Via URL do Telegram**
- URL do tópico: `https://t.me/c/1234567890/123/456`
- O último número (`456`) é o `message_thread_id`

### **PASSO 3: Configurar Permissões do Bot**

O bot precisa ser **administrador** com permissões:
- ✅ Excluir mensagens
- ✅ Banir usuários
- ✅ Convidar usuários
- ✅ Gerenciar tópicos (se aplicável)

### **PASSO 4: Criar Estrutura do Grupo**

#### **Sugestão de Tópicos:**
1. **📋 Regras** - ID para `RULES_TOPIC_ID`
2. **👋 Boas-vindas** - ID para `WELCOME_TOPIC_ID`
3. **🎮 Chat Geral** - Onde membros conversam
4. **📊 Anúncios** - Comunicações oficiais

---

## 🚀 **COMPORTAMENTO DO BOT**

### **QUANDO ALGUÉM ENTRA NO GRUPO:**

1. **Mensagem de Boas-vindas** (no tópico configurado):
```
🎮 Bem-vindo à Comunidade Gamer OnCabo, @usuario! 🎮

🔥 Você acaba de entrar na melhor comunidade de gamers! 🔥

📋 IMPORTANTE: Para participar ativamente do grupo, você precisa:
✅ Ler e aceitar nossas regras
✅ Reagir com 👍 na mensagem de regras

📌 Vá para o tópico 'Regras' e reaja à mensagem principal!

🚀 Aproveite a comunidade e bons jogos!
```

2. **Lembrete no Tópico de Regras**:
```
📋 @usuario, leia as regras acima e reaja com 👍!

⚠️ Sua participação no grupo depende da aceitação das regras.
⏰ Você tem 24 horas para reagir, caso contrário será removido automaticamente.

[✅ Li e aceito as regras] <- Botão clicável
```

### **SISTEMA DE INTERAÇÃO:**

- **Chat Privado**: Bot funciona normalmente (verificação de CPF, etc.)
- **Grupo Geral**: Bot **ignora completamente**
- **Tópicos Configurados**: Bot responde e interage
- **Outros Tópicos**: Bot ignora

---

## 🔧 **AUTOMAÇÃO E SCRIPTS**

### **Script de Verificação de Regras** (`check_rules_expiry.py`):

**Execução:** A cada 6 horas
```bash
# Adicionar ao cron
0 */6 * * * /path/to/run_rules_check.sh >> /path/to/logs/rules_check.log 2>&1
```

**Funcionalidade:**
- Verifica usuários que não aceitaram regras em 24h
- Remove automaticamente do grupo
- Notifica administradores

### **Script de Checkup Diário** (existente):
- Continua funcionando normalmente
- Agora também notifica sobre remoções por regras

---

## 📱 **EXPERIÊNCIA DO USUÁRIO**

### **CENÁRIO 1: Usuário Aceita Regras**
1. **Entra no grupo** → Recebe boas-vindas
2. **Vai ao tópico de regras** → Clica no botão
3. **✅ Sucesso!** → Pode participar normalmente

### **CENÁRIO 2: Usuário Ignora Regras**
1. **Entra no grupo** → Recebe boas-vindas
2. **Não vai ao tópico** → Fica pendente
3. **24h depois** → Removido automaticamente
4. **Administradores notificados** → Relatório enviado

---

## 🎛️ **CONFIGURAÇÕES AVANÇADAS**

### **Personalizar Tempo de Expiração:**

No arquivo `welcome_service.py`:
```python
# Alterar de 24h para outro valor
save_user_joining(user_id, username, expires_hours=48)  # 48 horas
```

### **Personalizar Mensagens:**

Edite as mensagens em `welcome_service.py`:
- `send_welcome_message()` - Boas-vindas
- `send_rules_reminder()` - Lembrete de regras

### **Adicionar Mais Tópicos:**

No arquivo `.env`:
```bash
ADMIN_TOPIC_ID="789"     # Tópico administrativo
SUPPORT_TOPIC_ID="012"   # Tópico de suporte
```

Atualizar `should_bot_respond_in_topic()` em `welcome_service.py`.

---

## 📊 **MONITORAMENTO E LOGS**

### **Ver Logs do Bot:**
```bash
docker logs sentinela-bot
```

### **Ver Logs de Regras:**
```bash
tail -f /path/to/logs/rules_check.log
```

### **Testar Sistema:**
```bash
# Testar detecção de tópicos
docker exec sentinela-bot python3 scripts/test_topics.py

# Testar verificação de regras
docker exec sentinela-bot python3 scripts/check_rules_expiry.py
```

---

## 🚨 **TROUBLESHOOTING**

### **Bot não detecta novos membros:**
- Verificar se bot é administrador
- Verificar permissões de leitura de mensagens

### **Bot responde fora dos tópicos:**
- Verificar configuração de `RULES_TOPIC_ID` e `WELCOME_TOPIC_ID`
- Verificar filtros em `should_bot_respond_in_topic()`

### **Botão de regras não funciona:**
- Verificar se `CallbackQueryHandler` está registrado
- Verificar logs de erro no `handle_rules_button()`

### **Usuários não são removidos:**
- Verificar permissões de ban do bot
- Verificar se script de verificação está rodando

---

## 📝 **EXEMPLO DE .env COMPLETO**

```bash
# Bot Telegram
TELEGRAM_TOKEN="1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TELEGRAM_GROUP_ID="-1001234567890"

# Tópicos (IDs dos tópicos específicos)
RULES_TOPIC_ID="123"
WELCOME_TOPIC_ID="456"

# Links de convite
INVITE_LINK_EXPIRE_TIME="3600"
INVITE_LINK_MEMBER_LIMIT="1"

# API HubSoft (existente)
HUBSOFT_HOST="https://api.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="seu_client_id"
HUBSOFT_CLIENT_SECRET="seu_client_secret"
HUBSOFT_USER="seu_usuario"
HUBSOFT_PASSWORD="sua_senha"

# Banco de dados
DATABASE_FILE="database/sentinela.db"
```

---

## 🎯 **RESULTADO FINAL**

**✅ BOT CONFIGURADO PARA:**
1. **Responder APENAS em tópicos específicos**
2. **Detectar novos membros automaticamente**
3. **Exigir aceitação de regras em 24h**
4. **Remover automaticamente quem não aceitar**
5. **Notificar administradores de todas as ações**

**🎮 EXPERIÊNCIA PREMIUM PARA A COMUNIDADE GAMER ONCABO!**

---

*Guia criado em 23/09/2025 - Sistema Sentinela OnCabo*