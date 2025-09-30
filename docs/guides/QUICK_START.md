# 🚀 Guia Rápido - Sentinela Bot

## Instalação em 5 Minutos

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/sentinela.git
cd sentinela
```

### 2. Configure o Ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite com suas credenciais
nano .env
```

**Variáveis obrigatórias:**
```env
# Telegram
TELEGRAM_TOKEN="seu_token_aqui"
TELEGRAM_GROUP_ID="id_do_grupo"

# HubSoft API
HUBSOFT_API_BASE_URL="https://api.hubsoft.com.br"
HUBSOFT_CLIENT_ID="seu_client_id"
HUBSOFT_CLIENT_SECRET="seu_secret"
```

### 3. Instale Dependências

```bash
pip install -r requirements.txt
```

### 4. Execute o Bot

```bash
# Modo produção
python main.py

# Ou bot direto do Telegram
python telegram_bot_real.py
```

## Comandos Básicos

### Usuários

```
/start - Inicia o bot
/help - Mostra ajuda
/verificar_cpf - Inicia verificação de CPF
/status - Verifica status de verificação
/suporte - Abre formulário de suporte
```

### Administradores

```
/stats - Estatísticas do sistema
/broadcast - Envia mensagem para todos
/ban <user_id> - Bane usuário
/unban <user_id> - Remove banimento
```

## Estrutura Básica

```
sentinela/
├── main.py                 # ← Inicie aqui
├── telegram_bot_real.py    # Bot do Telegram
├── .env                    # Suas configurações
├── requirements.txt        # Dependências
└── src/sentinela/         # Código-fonte
```

## Próximos Passos

1. **Desenvolvedores:** Leia [Arquitetura](../architecture/OVERVIEW.md)
2. **Administradores:** Configure [Deploy](./DEPLOYMENT.md)
3. **Usuários:** Veja [Comandos Completos](./COMMANDS.md)

## Problemas Comuns

### Bot não inicia
```bash
# Verifique se o token está correto
grep TELEGRAM_TOKEN .env

# Teste conexão
python -c "from telegram import Bot; Bot('SEU_TOKEN').get_me()"
```

### Erro de permissão no grupo
- Adicione o bot como administrador no grupo
- Dê permissões de: Gerenciar usuários, Excluir mensagens, Banir usuários

### Banco de dados não cria
```bash
# Crie o diretório manualmente
mkdir -p data/database
chmod 755 data/database
```

## Suporte

- 📖 [Documentação Completa](../README.md)
- 🐛 [Reportar Bug](https://github.com/seu-usuario/sentinela/issues)
- 💬 [Discussões](https://github.com/seu-usuario/sentinela/discussions)
