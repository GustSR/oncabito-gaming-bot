# 🔒 GUIA: TÓPICOS RESTRITOS POR REGRAS

## 🎯 **OBJETIVO:**
Fazer com que novos membros só vejam/acessem tópicos de gaming **APÓS** aceitar as regras.

---

## ⚙️ **CONFIGURAÇÃO MANUAL NO TELEGRAM:**

### **PASSO 1: Criar Cargo Especial**
1. **Grupo → Administradores → Gerenciar Grupo**
2. **Adicionar Administrador → Criar cargo personalizado**
3. **Nome do cargo:** `🎮 Gamer Verificado`
4. **Permissões do cargo:**
   - ✅ Enviar mensagens
   - ✅ Enviar mídia
   - ✅ Adicionar links de preview
   - ✅ Enviar enquetes
   - ❌ Outras permissões administrativas

### **PASSO 2: Restringir Tópicos de Gaming**
Para cada tópico de jogo:

1. **Entre no tópico específico**
2. **Toque no nome do tópico → Gerenciar tópico**
3. **Permissões → Enviar mensagens**
4. **Desabilite para "Membros"**
5. **Habilite apenas para "🎮 Gamer Verificado"**

**Tópicos para restringir:**
- 🎮 Jogos FPS & Battle Royale
- 🧙 RPG & MMORPG
- ⚽️ Esportes & Corrida
- 🕹 Retro & Indie
- 🎧 Setup & Periféricos

**Tópicos que ficam ABERTOS:**
- 📋 Regras da Comunidade
- 👋 Boas-vindas Gamer OnCabo

---

## 🤖 **AUTOMAÇÃO DO BOT:**

### **FUNCIONAMENTO AUTOMÁTICO:**

1. **Novo membro entra** → Só vê tópicos de regras/boas-vindas
2. **Aceita regras** → Bot tenta promover automaticamente
3. **Se bot não tem permissão** → Notifica administradores
4. **Admin adiciona ao cargo** → Usuário acessa tópicos de gaming

### **NOTIFICAÇÃO PARA ADMINISTRADORES:**

Quando alguém aceita regras, admins recebem:
```
✅ USUÁRIO VERIFICADO - LIBERAR ACESSO

👤 Usuário: @username
🆔 ID: 123456789
📋 Status: Aceitou regras

🔧 Ação necessária:
• Adicione ao cargo 'Gamer Verificado'
• Ou libere acesso aos tópicos manualmente

🎮 Tópicos para liberar:
• 🎮 Jogos FPS & Battle Royale
• 🧙 RPG & MMORPG
• ⚽️ Esportes & Corrida
• 🕹 Retro & Indie
• 🎧 Setup & Periféricos
```

---

## 🎮 **EXPERIÊNCIA DO USUÁRIO:**

### **CENÁRIO 1: Novo Membro**
1. **Entra no grupo** → Vê apenas:
   - 📋 Regras da Comunidade
   - 👋 Boas-vindas Gamer OnCabo
2. **Tenta acessar outros tópicos** → "Você não tem permissão"
3. **Lê regras e clica "Aceito"** → Aguarda liberação
4. **Admin adiciona ao cargo** → Acesso liberado!

### **CENÁRIO 2: Usuário Verificado**
1. **Já aceitou regras** → Acesso completo
2. **Pode enviar mensagens** em todos os tópicos
3. **Participa normalmente** da comunidade

---

## 🔧 **IMPLEMENTAÇÃO TÉCNICA:**

### **BOT ATUALIZADO COM:**

1. **`permissions_service.py`** - Gerencia permissões
2. **Auto-promoção** quando possível
3. **Notificação de admins** quando necessário
4. **Integração com sistema de regras**

### **LIMITAÇÕES DA API TELEGRAM:**

❌ **Não é possível via API:**
- Definir permissões por tópico específico
- Criar cargos automaticamente
- Adicionar usuários a cargos (sem ser admin)

✅ **É possível via API:**
- Promover para administrador limitado
- Enviar notificações para admins
- Detectar quando regras são aceitas

---

## 🚨 **CONFIGURAÇÃO MANUAL NECESSÁRIA:**

### **PARA FUNCIONAMENTO COMPLETO:**

1. **Criar cargo "🎮 Gamer Verificado"**
2. **Dar permissões corretas ao cargo**
3. **Restringir tópicos aos cargos**
4. **Bot como administrador com permissão de promover**

### **COMANDO PARA TESTAR BOT PERMISSIONS:**

```bash
# Verificar permissões do bot
/test_bot_permissions
```

---

## 📊 **MONITORAMENTO:**

### **LOGS DO BOT:**
```bash
docker logs sentinela-bot | grep "grant_topic_access"
```

### **COMANDOS DE TESTE:**
- `/test_topics` - Testa configuração
- `/check_permissions @username` - Verifica permissões de usuário

---

## 🎯 **RESULTADO FINAL:**

**✅ ACESSO PROGRESSIVO:**
1. **Entrada** → Apenas regras/boas-vindas
2. **Aceita regras** → Bot tenta liberar acesso
3. **Admin confirma** → Acesso total aos tópicos

**✅ CONTROLE TOTAL:**
- Novos membros não "poluem" tópicos de gaming
- Apenas usuários verificados participam
- Processo automatizado com supervisão manual

**✅ EXPERIÊNCIA PREMIUM:**
- Comunidade mais organizada
- Membros comprometidos
- Gaming de qualidade garantida

---

## ⚠️ **IMPORTANTE:**

Esta funcionalidade requer **configuração manual** no Telegram por limitações da API. O bot **automatiza o que é possível** e **notifica** quando ação manual é necessária.

**Resultado:** Sistema híbrido automatizado + supervisão humana para máximo controle! 🎮

---

*Guia criado em 23/09/2025 - Sistema Sentinela OnCabo*