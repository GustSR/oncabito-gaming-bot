# 📚 Documentação Completa do Bot Sentinela

> Índice centralizado de toda a documentação de mensagens e interações

---

## 🎯 Objetivo

Esta documentação mapeia **100%** das mensagens, interações e fluxos do Bot Sentinela (OnCabito Gaming Bot). Cada interação possível com usuários está documentada com:

- ✅ Mensagem exata enviada
- ✅ Condições para acontecer
- ✅ Arquivo e linha no código
- ✅ Diagramas de fluxo completos
- ✅ Pontos de decisão
- ✅ Caminhos alternativos

---

## 📖 Documentos Disponíveis

### 1. [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md)

**Conteúdo**: Todas as mensagens que o bot pode enviar, organizadas por fluxo.

**Inclui**:
- ✅ ~60 mensagens únicas mapeadas
- ✅ Texto completo de cada mensagem
- ✅ Contexto de quando acontece
- ✅ Localização no código (arquivo:linha)
- ✅ Condições para ser enviada

**Seções**:
1. Fluxo de Verificação de CPF
2. Fluxo de Suporte (Formulário de Ticket)
3. Fluxo de Status de Tickets
4. Fluxo de Boas-Vindas e Regras
5. Fluxo de Usuário Não Verificado
6. Mensagens de Erro e Sistema

**Use quando**: Você quer saber **qual mensagem** é enviada em cada situação.

---

### 2. [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md)

**Conteúdo**: Diagramas ASCII completos de todos os fluxos de interação.

**Inclui**:
- ✅ 6 diagramas principais
- ✅ 33 pontos de decisão
- ✅ 44 caminhos possíveis
- ✅ Fluxo visual de cada interação

**Diagramas Disponíveis**:
1. **Fluxo de Verificação de CPF**
   - Comando `/start`
   - Processamento de CPF
   - Resolução de duplicatas
   - Lembretes automáticos

2. **Fluxo de Suporte (Formulário)**
   - Comando `/suporte`
   - 7 passos do formulário
   - Persistência no banco
   - Criação de ticket HubSoft

3. **Fluxo de Status de Tickets**
   - Comando `/status`
   - Diferença grupo vs. privado
   - Histórico completo
   - Status em tempo real

4. **Fluxo de Boas-Vindas**
   - Novo membro entra
   - Mensagens de regras
   - Aceitação de regras
   - Saída do grupo

5. **Fluxo de Proteção (Guarda)**
   - Usuário não verificado tenta usar comando
   - Redirecionamento automático
   - Inicialização de verificação

6. **Fluxo de Duplicata (Checkup Proativo)**
   - CRON diário
   - Detecção de duplicatas
   - Mensagem aos envolvidos
   - Resolução de conflito

**Use quando**: Você quer **visualizar o fluxo completo** de uma interação.

---

### 3. [ANALISE_COMPLETA_REPOSITORIO.md](./ANALISE_COMPLETA_REPOSITORIO.md)

**Conteúdo**: Análise técnica completa de toda a arquitetura do bot.

**Inclui**:
- ✅ Visão geral do projeto
- ✅ Arquitetura (Clean Architecture + DDD)
- ✅ Camadas (Domain, Application, Infrastructure, Presentation)
- ✅ Estrutura do banco de dados
- ✅ Sistema de migrações
- ✅ Funcionalidades principais
- ✅ Configuração e deploy

**Use quando**: Você quer entender a **arquitetura técnica** do bot.

---

## 🔍 Como Usar Esta Documentação

### Cenário 1: "Quero saber o que acontece quando o usuário faz X"

**Exemplo**: *"O que acontece quando um usuário não verificado manda `/suporte` no grupo?"*

**Passos**:
1. Abra [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md)
2. Vá para a seção **"5. Fluxo de Proteção (Guarda)"**
3. Veja o diagrama visual completo
4. Para detalhes das mensagens, vá para [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) seção 5

---

### Cenário 2: "Quero ver todas as mensagens de erro"

**Passos**:
1. Abra [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md)
2. Vá para a seção **"6. Mensagens de Erro e Sistema"**
3. Veja todas as 10 mensagens de erro possíveis

---

### Cenário 3: "Quero entender o formulário de suporte completo"

**Passos**:
1. Abra [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md)
2. Vá para **"2. Fluxo de Suporte (Formulário)"**
3. Veja os 7 passos com diagrama visual
4. Para texto exato de cada passo, vá para [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) seção 2.2

---

### Cenário 4: "Quero entender a arquitetura do banco de dados"

**Passos**:
1. Abra [ANALISE_COMPLETA_REPOSITORIO.md](./ANALISE_COMPLETA_REPOSITORIO.md)
2. Vá para **"Estrutura do Banco de Dados"**
3. Veja as 8 tabelas principais com schema SQL completo

---

## 📊 Estatísticas Gerais

### Mensagens e Interações

| Métrica | Quantidade |
|---------|------------|
| **Mensagens únicas** | ~60 |
| **Botões inline** | ~40 |
| **Comandos** | 5 principais |
| **Fluxos principais** | 6 |
| **Pontos de decisão** | 33 |
| **Caminhos possíveis** | 44 |

### Arquivos de Código

| Handler | Linhas | Responsabilidade |
|---------|--------|------------------|
| **TelegramBotHandler** | 1.334 | Coordenação geral |
| **SupportFormHandler** | 904 | Formulário de suporte |
| **CPFVerificationHandler** | 606 | Verificação de CPF |
| **Total** | 2.844 | - |

### Tabelas no Banco

| Tabela | Registros Típicos | Propósito |
|--------|------------------|-----------|
| `users` | ~500 | Usuários verificados |
| `cpf_verifications` | ~1.000 | Histórico de verificações |
| `support_sessions` | ~50 | Formulários em andamento |
| `duplicate_conflicts` | ~10 | Conflitos de CPF |
| `group_invites` | ~100 | Convites gerados |
| `hubsoft_integrations` | ~200 | Fila de integrações |
| `administrators` | ~5 | Admins do sistema |

---

## 🎯 Fluxos Mais Importantes

### 1. Verificação de CPF (Crítico)

**Por quê**: É o **gatekeeper** do sistema. Sem verificação, usuário não entra no grupo.

**Documentação**:
- Diagrama: [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md) seção 1
- Mensagens: [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) seção 1

**Proteções**:
- ✅ Máximo 3 tentativas em 24h
- ✅ Expiração em 10 minutos
- ✅ Detecção de duplicatas
- ✅ Hash SHA-256 (nunca salva CPF em texto)
- ✅ Link único de convite (1 uso)

---

### 2. Formulário de Suporte (Feature Principal)

**Por quê**: Principal **funcionalidade** do bot - criar tickets de suporte.

**Documentação**:
- Diagrama: [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md) seção 2
- Mensagens: [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) seção 2

**Diferenciais**:
- ✅ **Persistência**: Progresso salvo no banco (sobrevive a reinicializações)
- ✅ 7 passos guiados
- ✅ Validações em cada etapa
- ✅ Suporte a anexos (até 5 imagens)
- ✅ Edição antes de confirmar
- ✅ Integração com HubSoft API

---

### 3. Proteção de Grupo (Segurança)

**Por quê**: **Impede** que usuários não verificados poluam o grupo.

**Documentação**:
- Diagrama: [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md) seção 5
- Mensagens: [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) seção 5

**Funcionamento**:
1. Detecta comando no grupo
2. Verifica se usuário está verificado
3. Se NÃO: deleta comando + redireciona para privado
4. Se SIM: executa comando normalmente

**Comandos protegidos**: `/suporte`, `/status`

---

## 🔐 Proteções e Segurança

### Todas as Proteções Implementadas

| Proteção | Onde | Como Funciona |
|----------|------|---------------|
| **CPF Hash** | `cpf_validation_service` | SHA-256, nunca salva texto puro |
| **Rate Limiting** | `cpf_verification_use_case` | Max 3 tentativas/24h |
| **Link Único** | `create_chat_invite_link` | member_limit=1 |
| **Expiração Verificação** | `cpf_verification` entity | 10 minutos |
| **Expiração Sessão** | `support_sessions` table | 24 horas |
| **Guarda de Grupo** | `_check_and_redirect...` | Bloqueia não verificados |
| **Desativação Auto** | `handle_new_member` | User sai = desativa |
| **Duplicata Proativa** | `daily_cpf_checkup` | CRON diário às 3h |
| **Ticket Único** | `handle_support_command` | 1 ticket ativo por vez |

---

## 🚀 Próximos Passos

### Se você é desenvolvedor:

1. ✅ Leia [ANALISE_COMPLETA_REPOSITORIO.md](./ANALISE_COMPLETA_REPOSITORIO.md) - entenda a arquitetura
2. ✅ Veja [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md) - visualize os fluxos
3. ✅ Consulte [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) - quando alterar mensagens

### Se você é gestor/produto:

1. ✅ Leia [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) - veja todas as mensagens
2. ✅ Veja [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md) seção 2 - entenda o formulário de suporte
3. ✅ Consulte estatísticas neste README

### Se você é suporte/atendimento:

1. ✅ Leia [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) seções 1, 2 e 6
2. ✅ Veja [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md) seções 1 e 2
3. ✅ Use como guia para explicar aos usuários

---

## 📝 Manutenção da Documentação

### Quando atualizar?

**Sempre que**:
- ✅ Adicionar nova mensagem ao bot
- ✅ Criar novo fluxo de interação
- ✅ Modificar mensagem existente
- ✅ Adicionar novo comando
- ✅ Mudar lógica de um fluxo

### Como atualizar?

1. **Mensagem nova/alterada**:
   - Edite [MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md](./MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md)
   - Adicione arquivo:linha
   - Descreva condições

2. **Fluxo novo/alterado**:
   - Edite [DIAGRAMAS_FLUXOS_BOT.md](./DIAGRAMAS_FLUXOS_BOT.md)
   - Atualize diagrama ASCII
   - Adicione pontos de decisão

3. **Arquitetura alterada**:
   - Edite [ANALISE_COMPLETA_REPOSITORIO.md](./ANALISE_COMPLETA_REPOSITORIO.md)
   - Atualize seções afetadas
   - Corrija estatísticas

---

## 📞 Contato

**Dúvidas sobre a documentação?**
- Consulte o código-fonte nos arquivos referenciados
- Cada mensagem tem localização (arquivo:linha)
- Use `grep` para encontrar mensagens específicas

**Exemplo**:
```bash
grep -r "Olá! Sou o OnCabito" src/
```

---

## ✨ Créditos

**Documentação gerada por**: Claude Code (Anthropic)
**Data**: 14 de outubro de 2025
**Versão do Bot**: 1.5.0
**Branch**: `fix/critical-architecture-issues`

---

**Total de Documentação**: 3 arquivos, ~5.000 linhas, 100% de cobertura de mensagens e fluxos.

🎉 **Toda interação possível com o bot está documentada!**
