# Checklist de Configuração - Sistema Sentinela

Este documento fornece um checklist completo para configurar corretamente o sistema após as últimas implementações.

## ✅ Configurações Obrigatórias

### 1. **Token do Bot Telegram**
```bash
TELEGRAM_TOKEN="SEU_TOKEN_DO_BOTFATHER"
```
- [ ] Obtido via @BotFather no Telegram
- [ ] Token válido e ativo

### 2. **ID do Grupo Principal**
```bash
TELEGRAM_GROUP_ID="-1002966479273"
```
- [ ] ID do grupo OnCabo onde o bot atuará
- [ ] Use @userinfobot no grupo para obter
- [ ] Formato: número negativo com aspas

### 3. **IDs dos Administradores**
```bash
ADMIN_USER_IDS="123456789,987654321"
```
- [ ] **CRÍTICO:** IDs reais dos administradores do sistema
- [ ] Use @userinfobot para descobrir cada User ID
- [ ] Separados por vírgula, sem espaços extras
- [ ] **SEM ESTA CONFIGURAÇÃO, COMANDOS ADMINISTRATIVOS NÃO FUNCIONAM**

### 4. **Canal de Notificações Técnicas**
```bash
TECH_NOTIFICATION_CHANNEL_ID="-1003102389025"
```
- [ ] Canal privado para receber alertas do sistema
- [ ] Formato: número negativo com aspas
- [ ] Bot deve ser administrador do canal

## ⚙️ Configurações de Tópicos

### Obrigatório para /suporte:
```bash
SUPPORT_TOPIC_ID="148"
```
- [ ] ID do tópico onde chamados de suporte são criados
- [ ] Bot deve ter permissão para postar no tópico

### Opcionais (mas recomendados):
```bash
RULES_TOPIC_ID="87"
WELCOME_TOPIC_ID="89"
```
- [ ] Tópicos para regras e boas-vindas

## 🔗 Configurações HubSoft

### Para Produção (Recomendado):
```bash
HUBSOFT_ENABLED="true"
HUBSOFT_HOST="https://api.oncabo.hubsoft.com.br/"
HUBSOFT_CLIENT_ID="77"
HUBSOFT_CLIENT_SECRET="sua_secret_aqui"
HUBSOFT_USER="seu_email@oncabo.com.br"
HUBSOFT_PASSWORD="sua_senha_aqui"
```
- [ ] Credenciais válidas do HubSoft
- [ ] Usuário com permissões adequadas
- [ ] Host correto da API

### Para Testes (Alternativa):
```bash
HUBSOFT_ENABLED="false"
```
- [ ] Sistema funcionará apenas com tickets locais
- [ ] Útil para desenvolvimento e testes

## 📁 Configurações do Banco

```bash
DATABASE_FILE="data/database/sentinela.db"
```
- [ ] Diretório existe ou será criado automaticamente
- [ ] Permissões de escrita no diretório

## 🔍 Validação Pós-Configuração

### 1. **Teste dos Administradores**
Execute no chat privado com o bot:
- [ ] `/help` - Deve mostrar comandos administrativos
- [ ] `/health_hubsoft` - Deve funcionar sem erro de permissão
- [ ] `/admin_tickets` - Deve funcionar sem erro de permissão

### 2. **Teste de Usuário Comum**
Com outro usuário (não admin):
- [ ] `/help` - Deve mostrar apenas comandos básicos
- [ ] `/admin_tickets` - Deve dar mensagem de "não disponível"
- [ ] `/sync_tickets` - Deve dar mensagem de "restrito para administradores"

### 3. **Teste do Sistema de Suporte**
- [ ] `/start` - Verificação de CPF funciona
- [ ] `/suporte` - Formulário de suporte funciona
- [ ] `/status` - Consulta de atendimentos funciona

### 4. **Teste de Conectividade HubSoft**
Se HUBSOFT_ENABLED="true":
- [ ] `/health_hubsoft` - Mostra status "ONLINE"
- [ ] Tickets criados aparecem no HubSoft
- [ ] Sincronização automática funciona

## ⚠️ Problemas Comuns e Soluções

### **Comandos administrativos não funcionam:**
**Causa:** `ADMIN_USER_IDS` não configurado ou IDs errados
**Solução:**
1. Use @userinfobot para obter seu User ID
2. Configure corretamente no .env
3. Reinicie o bot

### **HubSoft mostra OFFLINE:**
**Causa:** Credenciais incorretas ou host errado
**Solução:**
1. Verifique todas as credenciais HubSoft
2. Teste login manual no painel HubSoft
3. Verifique URL da API

### **Bot não responde no grupo:**
**Causa:** ID do grupo incorreto
**Solução:**
1. Use @userinfobot no grupo correto
2. Verifique se o ID tem formato negativo
3. Confirme que bot está no grupo

### **Notificações não chegam:**
**Causa:** Canal técnico incorreto ou bot sem permissão
**Solução:**
1. Verifique ID do canal
2. Adicione bot como admin do canal
3. Teste envio manual

## 📋 Checklist de Primeira Execução

Antes de usar em produção:

### Configuração:
- [ ] Todas as variáveis obrigatórias configuradas
- [ ] IDs dos administradores reais configurados
- [ ] HubSoft testado e funcionando (se habilitado)
- [ ] Canal de notificações configurado

### Testes:
- [ ] Bot responde a comandos
- [ ] Sistema de controle de acesso funciona
- [ ] Suporte funciona end-to-end
- [ ] Sincronização funciona (se HubSoft habilitado)

### Monitoramento:
- [ ] Logs do sistema sendo gerados
- [ ] Notificações chegando no canal técnico
- [ ] Banco de dados sendo criado corretamente

## 🚀 Comandos de Verificação Rápida

Execute estes comandos como admin para validar o sistema:

1. **Verificar configuração:**
   ```
   /help
   ```
   Deve mostrar comandos administrativos.

2. **Verificar HubSoft:**
   ```
   /health_hubsoft
   ```
   Deve mostrar status detalhado.

3. **Testar sincronização:**
   ```
   /sync_tickets
   ```
   Deve executar sem erros.

4. **Verificar controle de acesso:**
   Teste com usuário não-admin - deve ser bloqueado.

## 📞 Suporte

Se alguma configuração não estiver funcionando:

1. **Verifique os logs** - Procure por erros específicos
2. **Confira o .env** - Compare com .env.example
3. **Teste isoladamente** - Use comandos individuais
4. **Verifique permissões** - Bot precisa de admin nos canais

## 🎯 Resultado Esperado

Com tudo configurado corretamente, você terá:

- ✅ **Sistema de suporte** funcionando com formulário inteligente
- ✅ **Controle de acesso** separando usuários e administradores
- ✅ **Sincronização automática** com HubSoft (se habilitado)
- ✅ **Monitoramento** com notificações para administradores
- ✅ **Fallback robusto** quando HubSoft está offline
- ✅ **Experiência otimizada** para usuários finais

O sistema está pronto para produção quando todos os itens do checklist estiverem completos! 🎮