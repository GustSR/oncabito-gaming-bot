# 🤖 Mapeamento Completo de Respostas do Bot

## 📍 Locais de Interação

### 1️⃣ **PRIVADO (DM com o usuário)**
O bot tem interação completa e responde a tudo.

### 2️⃣ **GRUPO - Tópico de Suporte** (🆘 Suporte Gamer)
Interações limitadas e específicas.

### 3️⃣ **GRUPO - Outros Tópicos**
❌ **Bot NÃO responde nada** - ignora completamente.

---

## 🔵 Respostas no PRIVADO (DM)

### Comandos:
| Comando | Resposta | Arquivo:Linha |
|---------|----------|--------------|
| `/start` | Boas-vindas + início verificação CPF | telegram_bot_handler.py:304 |
| `/suporte` | Inicia fluxo de criação de ticket | telegram_bot_handler.py:508 |
| `/status` | Mostra tickets ativos do usuário | telegram_bot_handler.py:544 |

### Fluxos Interativos:
| Situação | Resposta | Arquivo:Linha |
|----------|----------|--------------|
| **Aguardando CPF** | Processa CPF e valida com HubSoft | telegram_bot_handler.py:1063-1076 |
| **Em fluxo de suporte (descrição)** | Processa descrição do problema | support_form_handler.py:818+ |
| **Em fluxo de suporte (foto)** | Aceita foto como anexo | telegram_bot_handler.py:1175 |
| **Callback de botão** | Processa escolhas (categoria, jogo, etc) | telegram_bot_handler.py:933+ |

### Mensagens Aleatórias:
| Contexto | Resposta | Arquivo:Linha |
|----------|----------|--------------|
| Usuário verificado + mensagem qualquer | "💬 Mensagem recebida!\nPara criar um atendimento, use /suporte\nPara verificar status, use /status" | telegram_bot_handler.py:1110-1115 |
| Usuário pendente verificação | "⏳ **Aguardando verificação de CPF**\n\n📝 Por favor, envie seu CPF (apenas números) para continuar." | cpf_verification_handler.py:176 |
| Foto enviada fora de fluxo | "📷 Foto recebida! Para criar atendimento com anexos use /suporte" | telegram_bot_handler.py:1182-1186 |

---

## 🟢 Respostas no GRUPO - Tópico de Suporte

### Comandos:
| Comando | Resposta | Arquivo:Linha |
|---------|----------|--------------|
| `/suporte` | "👋 Olá @user! Recebi seu pedido e já estou te chamando no privado!" + deleta comando | telegram_bot_handler.py:500-506 |

### Notificações Automáticas (Bot → Equipe):
| Evento | Mensagem | Arquivo:Linha |
|--------|----------|--------------|
| Ticket criado | "🎫 **NOVO CHAMADO - VIA BOT**\n📋 Protocolo: ...\n👤 Cliente: ...\n🎯 Categoria: ...\n🎮 Jogo: ...\n📝 Descrição: ..." | support_form_handler.py:831-844 |

### Mensagens Aleatórias:
| Situação | Resposta | Arquivo:Linha |
|----------|----------|--------------|
| Texto qualquer | ❌ **Ignora silenciosamente** | telegram_bot_handler.py:1067-1069 |
| Foto qualquer | ❌ **Ignora silenciosamente** | telegram_bot_handler.py:1167-1171 |

---

## 🔴 Respostas no GRUPO - Outros Tópicos

| Qualquer Interação | Resposta | Arquivo:Linha |
|--------------------|----------|--------------|
| Comandos | ❌ **Ignora** (alguns comandos como /suporte são deletados) | telegram_bot_handler.py:493-497 |
| Texto | ❌ **Ignora silenciosamente** | telegram_bot_handler.py:1067-1069 |
| Fotos | ❌ **Ignora silenciosamente** | telegram_bot_handler.py:1167-1171 |
| Callbacks | ❌ **Ignora** (não há botões fora do contexto) | N/A |

---

## 🎯 Resumo por Tipo de Mensagem

### 📝 Texto:
- **Privado**: Responde sempre (comandos, fluxos, ou mensagem genérica)
- **Grupo/Tópico Suporte**: Ignora (exceto `/suporte` que redireciona)
- **Grupo/Outros Tópicos**: Ignora completamente

### 📷 Fotos:
- **Privado**: Responde sempre (aceita em fluxo ou sugere /suporte)
- **Grupo/Tópico Suporte**: Ignora
- **Grupo/Outros Tópicos**: Ignora completamente

### 🔘 Botões (Callbacks):
- **Privado**: Processa sempre
- **Grupo**: Não há botões enviados para grupo (apenas DM)

### 📢 Notificações (Bot → Usuários):
- **Privado**: Confirmações de ticket, status, erros
- **Grupo/Tópico Suporte**: Apenas notificação de novo ticket (para equipe)
- **Grupo/Canal Admin**: Notificação completa de ticket (HTML formatado)

---

## 🔧 Alterações Recentes (Esta Branch)

### ✅ Implementado:
1. **Bloqueio global de tópicos**: Bot só responde no tópico de suporte configurado
2. **Respostas genéricas apenas no privado**: Mensagens como "💬 Mensagem recebida!" só no DM
3. **Notificação dupla**: Canal admin (completa) + Tópico suporte (simples)
4. **Verificação de tópico no /suporte**: Comando só funciona no tópico correto

### 📍 Arquivos Modificados:
- `telegram_bot_handler.py`: Linhas 493-497, 1059-1069, 1109-1117, 1159-1186
- `support_form_handler.py`: Linhas 787-850

---

**Última atualização**: 29/10/2025
**Branch**: `fix/notification-and-topic-validation`
