# 🚀 GUIA: CRIAR REPOSITÓRIO NO GITHUB

Instruções para publicar o OnCabito Bot no GitHub.

---

## 📋 **PRÉ-REQUISITOS CONCLUÍDOS**

✅ **Repositório Git inicializado**
✅ **Commit inicial criado** (50 arquivos)
✅ **.gitignore configurado** (protege credenciais)
✅ **Estrutura organizada** e profissional

---

## 🌐 **PASSO 1: CRIAR REPOSITÓRIO NO GITHUB**

### 1️⃣ **Acesse GitHub.com**
- Faça login na sua conta
- Clique em **"New repository"** (botão verde)

### 2️⃣ **Configurações do Repositório**
```
Repository name: oncabito-gaming-bot
Description: 🤖 Bot oficial da comunidade gamer OnCabo - Verificação automática, gestão de tópicos e checkups diários
Visibility: Private (recomendado) ou Public
```

### 3️⃣ **NÃO marque nenhuma opção**
- ❌ **NÃO** marque "Add a README file"
- ❌ **NÃO** marque "Add .gitignore"
- ❌ **NÃO** marque "Choose a license"

*(Já temos todos esses arquivos localmente)*

### 4️⃣ **Clique em "Create repository"**

---

## 🔗 **PASSO 2: CONECTAR REPOSITÓRIO LOCAL**

Após criar no GitHub, você verá uma página com comandos. Use esta opção:

### **"…or push an existing repository from the command line"**

```bash
# No diretório do projeto (/home/gust/Repositorios Github/Sentinela/)
git remote add origin https://github.com/SEU_USUARIO/oncabito-gaming-bot.git
git branch -M main
git push -u origin main
```

**⚠️ SUBSTITUA:** `SEU_USUARIO` pelo seu username do GitHub

---

## 📋 **PASSO 3: COMANDOS PARA EXECUTAR**

Execute estes comandos **UM POR VEZ** no terminal:

```bash
# 1. Navegar para o diretório do projeto
cd "/home/gust/Repositorios Github/Sentinela"

# 2. Adicionar o remote do GitHub (substitua SEU_USUARIO)
git remote add origin https://github.com/SEU_USUARIO/oncabito-gaming-bot.git

# 3. Verificar se foi adicionado corretamente
git remote -v

# 4. Push inicial para o GitHub
git push -u origin main
```

---

## 🔐 **AUTENTICAÇÃO NO GITHUB**

### **Opção 1: Personal Access Token (Recomendado)**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Scopes: marque `repo` (full control of private repositories)
4. Copie o token gerado
5. Use como senha quando o git pedir

### **Opção 2: SSH Keys**
Se preferir SSH, configure uma chave SSH:
```bash
ssh-keygen -t ed25519 -C "gaming@oncabo.com.br"
cat ~/.ssh/id_ed25519.pub
# Copie a chave e adicione em GitHub → Settings → SSH keys
```

---

## 📊 **VERIFICAÇÃO FINAL**

Após o push, verifique no GitHub:

✅ **50 arquivos** enviados
✅ **README.md** exibindo corretamente
✅ **Estrutura de pastas** organizada:
```
📁 deployment/  - Scripts de instalação
📁 docs/        - Documentação completa
📁 src/         - Código fonte
📁 tools/       - Utilitários
```

---

## 🛡️ **SEGURANÇA**

### ✅ **Arquivos PROTEGIDOS (não vão para GitHub):**
- `.env` - Credenciais do bot
- `data/database/*.db` - Banco de dados
- `logs/*.log` - Logs com informações sensíveis
- `.claude/` - Arquivos temporários

### ✅ **Arquivos INCLUÍDOS:**
- `.env.example` - Template de configuração
- Toda documentação
- Código fonte completo
- Scripts de deployment

---

## 🎯 **PRÓXIMOS PASSOS**

Após publicar no GitHub:

1. **Configure Actions (opcional):**
   - CI/CD para testes automáticos
   - Deploy automático

2. **Issues/Projects:**
   - Organize tarefas futuras
   - Bug tracking

3. **Releases:**
   - Tag versões estáveis
   - Changelog organizado

4. **Wiki:**
   - Documentação estendida
   - Tutoriais para admins

---

## 🆘 **PROBLEMAS COMUNS**

### ❌ **"Repository already exists"**
```bash
git remote remove origin
git remote add origin https://github.com/SEU_USUARIO/oncabito-gaming-bot.git
```

### ❌ **"Authentication failed"**
- Verifique username/password
- Use Personal Access Token como senha
- Configure SSH se preferir

### ❌ **"Permission denied"**
- Verifique se o repositório é seu
- Confirme que tem permissões de escrita

---

## 🎮 **COMANDO RESUMIDO**

Se tudo estiver configurado corretamente:

```bash
cd "/home/gust/Repositorios Github/Sentinela"
git remote add origin https://github.com/SEU_USUARIO/oncabito-gaming-bot.git
git push -u origin main
```

**🚀 Substitua `SEU_USUARIO` e execute!**

---

*Guia criado em 23/09/2025 - OnCabito Gaming Bot v2.0*