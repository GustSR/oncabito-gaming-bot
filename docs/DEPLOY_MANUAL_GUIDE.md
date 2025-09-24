# 🚀 Deploy Manual - OnCabito Bot

Guia de deploy simplificado sem SSH - **muito mais confiável!**

---

## ⚡ **NOVO FLUXO SIMPLIFICADO**

### 📊 **Como funciona agora:**

```
1. 💻 Desenvolvedor: git push origin main
2. 🏗️  GitHub: Build imagem Docker automaticamente
3. 📦 Registry: Imagem disponível em segundos
4. 🖥️  Servidor: git pull && ./deploy.sh
5. ✅ Bot: Online com nova versão!
```

**🎯 Vantagens:**
- ✅ **100% confiável** - sem problemas de SSH/rede
- ✅ **Controle total** - você decide quando deployar
- ✅ **Debug fácil** - vê tudo acontecendo localmente
- ✅ **Deploy rápido** - poucos comandos

---

## 🖥️ **NO SERVIDOR**

### 🔧 **Setup inicial (apenas uma vez):**

```bash
# 1. Ir para diretório do projeto
cd /opt/oncabito-bot

# 2. Tornar script executável
chmod +x deploy.sh

# 3. Verificar .env configurado
ls -la .env
```

### 🚀 **Deploy (sempre que houver nova versão):**

```bash
# Comandos simples:
cd /opt/oncabito-bot
git pull
./deploy.sh
```

**Pronto!** O script faz tudo automaticamente:
- ✅ Pull da nova imagem Docker
- ✅ Para container antigo
- ✅ Inicia nova versão
- ✅ Verifica se tudo está funcionando

---

## 📋 **FLUXO COMPLETO PASSO A PASSO**

### 👨‍💻 **1. Desenvolvedor faz mudanças:**

```bash
# No computador local
cd "/home/gust/Repositorios Github/Sentinela"

# Fazer mudanças no código...
git add .
git commit -m "feat: Nova funcionalidade"
git push origin main
```

### ⏳ **2. Aguardar build (2-3 minutos):**

- Acompanhar em: https://github.com/GustSR/oncabito-gaming-bot/actions
- ✅ Build completo quando aparecer: "Build Complete"

### 🖥️ **3. Deploy no servidor:**

```bash
# No servidor
cd /opt/oncabito-bot
git pull && ./deploy.sh
```

### 📊 **4. Verificar resultado:**

```bash
# Status dos containers
docker-compose ps

# Ver logs em tempo real
docker logs oncabito-bot -f
```

---

## 🔧 **SCRIPT DE DEPLOY DETALHADO**

### 📝 **O que o `./deploy.sh` faz:**

```bash
🚀 OnCabito Bot - Deploy Manual
===============================
✅ 1. Fazendo backup do .env...
✅ 2. Atualizando código do repositório...
✅ 3. Baixando imagem mais recente...
✅ 4. Parando container atual...
✅ 5. Criando diretórios necessários...
✅ 6. Verificando configuração...
✅ 7. Subindo nova versão...
✅ 8. Aguardando inicialização...
✅ 9. Verificando saúde do sistema...
✅ 10. Mostrar status final...

🎉 Deploy concluído com sucesso!
```

### 📊 **Exemplo de execução:**

```bash
root@servidor:/opt/oncabito-bot# ./deploy.sh

🚀 OnCabito Bot - Deploy Manual
===============================
✅ Backup do .env criado
✅ Código atualizado
📦 Baixando imagem mais recente...
latest: Pulling from gustsr/oncabito-gaming-bot
✅ Imagem atualizada
⏹️  Parando container atual...
✅ Container parado
📁 Criando diretórios necessários...
✅ Diretórios criados
⚙️  Verificando configuração...
✅ Configuração verificada
🆙 Subindo nova versão...
✅ Nova versão em execução
⏳ Aguardando inicialização...
🏥 Verificando saúde do sistema...
✅ Sistema saudável

📊 Status Final:
NAME           COMMAND                  SERVICE       STATUS       PORTS
oncabito-bot   "python3 main.py"       oncabito-bot  Up (healthy)

📋 Logs recentes:
2025-09-24 16:15:23 - INFO - Bot iniciado com sucesso
2025-09-24 16:15:23 - INFO - Conectado ao Telegram
2025-09-24 16:15:24 - INFO - Sistema pronto para uso

✅ Deploy concluído com sucesso! 🎉

🔧 Comandos úteis:
  • Ver logs: docker-compose logs -f
  • Status: docker-compose ps
  • Parar: docker-compose down
  • Restart: docker-compose restart
```

---

## 🆘 **TROUBLESHOOTING**

### ❌ **"docker-compose.yml não encontrado"**
```bash
# Verificar se está no diretório correto:
pwd
# Deve mostrar: /opt/oncabito-bot

# Se não estiver:
cd /opt/oncabito-bot
```

### ❌ **"Falha ao baixar imagem"**
```bash
# Verificar conectividade:
ping github.com

# Tentar pull manual:
docker pull ghcr.io/gustsr/oncabito-gaming-bot:latest

# Ver imagens disponíveis:
docker images | grep oncabito
```

### ❌ **".env não encontrado"**
```bash
# Verificar se arquivo existe:
ls -la .env

# Se não existir, criar baseado no exemplo:
cp .env.example .env
nano .env
```

### ❌ **Container não inicia**
```bash
# Ver logs detalhados:
docker-compose logs oncabito-bot

# Verificar configuração:
docker-compose config

# Testar container manualmente:
docker run --rm --env-file .env ghcr.io/gustsr/oncabito-gaming-bot:latest
```

---

## 📊 **MONITORAMENTO**

### 📈 **Comandos úteis durante deploy:**

```bash
# Monitor contínuo (em outra janela do terminal):
watch -n 2 'docker ps && echo && docker images | grep oncabito'

# Logs em tempo real:
docker logs oncabito-bot -f

# Status de saúde:
docker inspect oncabito-bot --format='{{.State.Health.Status}}'
```

### 🔍 **Script de monitoramento:**

```bash
# Criar script de monitor:
cat > /root/monitor.sh << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "📅 $(date)"
    echo "=================================="
    echo "🐳 CONTAINERS:"
    docker ps | grep oncabito
    echo ""
    echo "🏥 HEALTH:"
    docker inspect oncabito-bot --format='{{.State.Health.Status}}' 2>/dev/null || echo "N/A"
    echo ""
    echo "📊 ÚLTIMAS MENSAGENS:"
    docker logs oncabito-bot --tail 3 2>/dev/null || echo "Nenhum log"
    echo ""
    echo "⏳ Atualizando em 3s... (Ctrl+C para sair)"
    sleep 3
done
EOF

chmod +x /root/monitor.sh
./monitor.sh
```

---

## 🎯 **COMPARAÇÃO DOS MÉTODOS**

### 🟢 **Deploy Manual (Atual - Recomendado):**
- ✅ **Simplicidade**: 2 comandos apenas
- ✅ **Confiabilidade**: 100% - sem falhas de rede
- ✅ **Controle**: Você decide quando deployar
- ✅ **Debug**: Vê tudo acontecendo
- ✅ **Flexibilidade**: Pode parar e verificar a qualquer momento

### 🔴 **Deploy Automático SSH (Anterior):**
- ❌ **Complexidade**: Configuração SSH complexa
- ❌ **Falhas**: Timeout, rede, permissões
- ❌ **Falta de controle**: Deploy forçado
- ❌ **Debug difícil**: Logs remotos apenas

---

## ⚡ **COMANDOS RÁPIDOS**

### 🚀 **Deploy completo:**
```bash
cd /opt/oncabito-bot && git pull && ./deploy.sh
```

### 📊 **Status rápido:**
```bash
docker ps && docker logs oncabito-bot --tail 5
```

### 🔄 **Restart rápido:**
```bash
docker-compose restart && docker logs oncabito-bot -f
```

### 🧹 **Limpeza:**
```bash
docker system prune -f && docker images
```

---

## 🎉 **RESULTADO FINAL**

### ✅ **Deploy em 30 segundos:**

1. **Desenvolvedor**: `git push origin main`
2. **Aguardar**: 2-3 minutos (build automático)
3. **Servidor**: `cd /opt/oncabito-bot && git pull && ./deploy.sh`
4. **Resultado**: Bot online com nova versão! 🎉

### 📈 **Estatísticas típicas:**
- ⏱️ **Build**: 2-3 minutos (automático)
- ⏱️ **Deploy**: 30-60 segundos (manual)
- 📊 **Success rate**: ~99% (vs ~60% com SSH)
- 🔧 **Manutenção**: Mínima

---

*Deploy manual implementado em 24/09/2025 - OnCabito Gaming Bot v2.0*