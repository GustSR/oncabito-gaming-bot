# 🔍 DESCOBERTA AUTOMÁTICA DE TÓPICOS

## ✅ **FUNCIONALIDADE IMPLEMENTADA**

O bot agora pode **identificar automaticamente** os IDs e nomes dos tópicos do grupo, facilitando a configuração!

---

## 🚀 **COMO FUNCIONA**

### **1. DESCOBERTA AUTOMÁTICA**
- Bot monitora **todas as mensagens** no grupo
- Identifica automaticamente **IDs dos tópicos**
- Deduz **nomes dos tópicos** baseado no contexto
- Salva tudo no **banco de dados** para consulta

### **2. COMANDOS DISPONÍVEIS**

#### **📋 `/topics` - Listar Tópicos**
Mostra todos os tópicos descobertos:
```
📋 TÓPICOS DESCOBERTOS NO GRUPO

🏠 Grupo: -1001234567890
📊 Total: 4 tópicos

1. 📋 Regras
   🆔 ID: 123
   📅 Descoberto: 2025-09-23 10:30:45
   🕒 Última atividade: 2025-09-23 12:15:30

2. 👋 Boas-vindas
   🆔 ID: 456
   📅 Descoberto: 2025-09-23 10:35:20
   🕒 Última atividade: 2025-09-23 12:10:15

3. 🎮 Gaming
   🆔 ID: 789
   📅 Descoberto: 2025-09-23 11:00:00
   🕒 Última atividade: 2025-09-23 12:20:45

4. 💬 Chat Geral
   🆔 ID: 012
   📅 Descoberto: 2025-09-23 11:15:30
   🕒 Última atividade: 2025-09-23 12:25:10
```

#### **🔧 `/auto_config` - Configuração Automática**
Sugere configurações baseadas nos tópicos descobertos:
```
🔧 CONFIGURAÇÃO AUTOMÁTICA SUGERIDA

📋 Tópico de Regras:
   • Nome: 📋 Regras
   • ID: 123
   • Configuração: RULES_TOPIC_ID="123"

👋 Tópico de Boas-vindas:
   • Nome: 👋 Boas-vindas
   • ID: 456
   • Configuração: WELCOME_TOPIC_ID="456"

📂 Outros Tópicos (2):
   • 🎮 Gaming (ID: 789)
   • 💬 Chat Geral (ID: 012)

💾 Para aplicar as configurações:
1. Copie os IDs sugeridos
2. Adicione no arquivo .env
3. Reinicie o bot
4. Use /test_topics para validar
```

#### **🧪 `/test_topics` - Testar Configuração**
Valida se a configuração atual está funcionando:
```
🧪 TESTE DE CONFIGURAÇÃO DE TÓPICOS

📋 Configuração Atual:
• Grupo ID: -1001234567890
• Tópico Regras: 123
• Tópico Boas-vindas: 456

🔍 Tópicos Descobertos: 4

✅ Tópico Regras encontrado: 📋 Regras
✅ Tópico Boas-vindas encontrado: 👋 Boas-vindas

✅ Status: Configuração funcionando
🎯 Bot responderá apenas nos tópicos configurados
```

---

## 🎯 **PROCESSO PASSO A PASSO**

### **PASSO 1: Descobrir Tópicos**
1. **Envie mensagens** em diferentes tópicos do grupo
2. Bot **identifica automaticamente** os IDs
3. Aguarde alguns minutos para descoberta completa

### **PASSO 2: Consultar Descobertos**
1. Envie `/topics` no **chat privado** com o bot
2. Bot lista todos os tópicos descobertos
3. Anote os IDs dos tópicos desejados

### **PASSO 3: Configuração Automática**
1. Envie `/auto_config` no **chat privado**
2. Bot sugere configurações baseadas nos nomes
3. Copie as linhas de configuração sugeridas

### **PASSO 4: Aplicar Configuração**
1. Edite o arquivo `.env`:
```bash
RULES_TOPIC_ID="123"
WELCOME_TOPIC_ID="456"
```
2. Reinicie o bot:
```bash
docker stop sentinela-bot
docker rm sentinela-bot
docker build -t sentinela-bot .
docker run -d --name sentinela-bot --env-file .env sentinela-bot
```

### **PASSO 5: Validar**
1. Envie `/test_topics` no **chat privado**
2. Verifique se configuração está funcionando
3. Teste enviando mensagem nos tópicos configurados

---

## 🧠 **INTELIGÊNCIA DE NOMES**

O bot reconhece automaticamente nomes de tópicos baseado em palavras-chave:

| **Palavras-chave** | **Nome Sugerido** |
|-------------------|-------------------|
| regra, rule, norma | 📋 Regras |
| bem-vindo, welcome, boas-vindas | 👋 Boas-vindas |
| anúncio, announcement, aviso | 📢 Anúncios |
| suporte, support, ajuda, help | 🆘 Suporte |
| game, jogo, gaming | 🎮 Gaming |
| geral, general, chat | 💬 Chat Geral |
| *outros* | Tópico {ID} |

---

## 🔄 **FUNCIONAMENTO TÉCNICO**

### **Detecção Automática:**
- Handler intercepta **todas as mensagens** do grupo
- Extrai `message_thread_id` de cada mensagem
- Salva no banco com timestamp e contexto

### **Banco de Dados:**
Nova tabela `group_topics`:
```sql
CREATE TABLE group_topics (
    topic_id INTEGER PRIMARY KEY,
    topic_name TEXT NOT NULL,
    discovered_at TIMESTAMP,
    last_activity TIMESTAMP,
    last_message_id INTEGER,
    is_active BOOLEAN DEFAULT 1
);
```

### **Cache Inteligente:**
- Mantém cache em memória para performance
- Atualiza automaticamente com novas descobertas
- Persiste informações entre reinicializações

---

## 📊 **MONITORAMENTO**

### **Logs de Descoberta:**
```bash
# Ver logs do bot
docker logs sentinela-bot | grep "Tópico descoberto"

# Exemplo de output:
INFO - Tópico descoberto: 📋 Regras (ID: 123)
INFO - Tópico descoberto: 👋 Boas-vindas (ID: 456)
```

### **Teste Manual:**
```bash
# Executar teste completo
docker exec sentinela-bot python3 scripts/test_topics_discovery.py

# Ver status dos tópicos no banco
docker exec sentinela-bot sqlite3 database/sentinela.db "SELECT * FROM group_topics;"
```

---

## 🎮 **EXEMPLO PRÁTICO**

### **Cenário:** Configurar grupo com 4 tópicos

1. **📋 Regras** (ID: 123) - Para regras do grupo
2. **👋 Boas-vindas** (ID: 456) - Para mensagens de entrada
3. **🎮 Gaming** (ID: 789) - Chat sobre jogos
4. **📢 Anúncios** (ID: 012) - Comunicados oficiais

### **Configuração:**
```bash
# .env
RULES_TOPIC_ID="123"
WELCOME_TOPIC_ID="456"

# Bot responderá apenas nos tópicos 123 e 456
# Ignorará completamente os tópicos 789 e 012
```

### **Resultado:**
- ✅ Novos membros → Boas-vindas no tópico 456
- ✅ Regras obrigatórias → Interação no tópico 123
- ❌ Chat gaming → Bot ignora completamente
- ❌ Anúncios → Bot ignora completamente

---

## 🚨 **TROUBLESHOOTING**

### **Bot não descobre tópicos:**
- Verificar se bot está no grupo
- Enviar algumas mensagens nos tópicos
- Verificar logs: `docker logs sentinela-bot`

### **Comando /topics retorna vazio:**
- Aguardar algumas mensagens nos tópicos
- Bot precisa ver mensagens para descobrir
- Usar `/auto_config` pode ajudar na descoberta

### **Configuração não funciona:**
- Usar `/test_topics` para verificar status
- Conferir se IDs estão corretos no .env
- Reiniciar bot após alterar .env

---

## 🎯 **RESULTADO FINAL**

**✅ DESCOBERTA AUTOMÁTICA IMPLEMENTADA!**

Agora você pode:
1. **🔍 Descobrir automaticamente** IDs de tópicos
2. **📋 Listar todos** os tópicos do grupo
3. **🔧 Configurar automaticamente** baseado em sugestões
4. **🧪 Validar** se configuração está funcionando
5. **🎯 Usar bot apenas** nos tópicos específicos

**Sem necessidade de descobrir IDs manualmente!** 🚀

---

*Sistema implementado em 23/09/2025 - Sentinela OnCabo*