# Mapeamento Completo de Mensagens e Interações do Bot Sentinela

> Documentação gerada em 14/10/2025
>
> Este documento mapeia **TODAS** as mensagens e interações que o bot pode ter com usuários/clientes.

---

## Índice

1. [Fluxo de Verificação de CPF](#1-fluxo-de-verificação-de-cpf)
2. [Fluxo de Suporte (Formulário de Ticket)](#2-fluxo-de-suporte-formulário-de-ticket)
3. [Fluxo de Status de Tickets](#3-fluxo-de-status-de-tickets)
4. [Fluxo de Boas-Vindas e Regras](#4-fluxo-de-boas-vindas-e-regras)
5. [Fluxo de Usuário Não Verificado](#5-fluxo-de-usuário-não-verificado)
6. [Mensagens de Erro e Sistema](#6-mensagens-de-erro-e-sistema)

---

## 1. Fluxo de Verificação de CPF

### 1.1. Início do Fluxo (`/start`)

#### **Cenário 1A: Usuário já é membro do grupo (Verificado)**

**Condição**: `chat.type == 'private'` E usuário é membro do grupo

**Resposta para Admin**:
```
👋 Olá, {nome}! Como administrador, o que você gostaria de fazer?

[Botões]
📋 Listar Tickets | 📊 Estatísticas
🔄 Sync HubSoft | ⚙️ Configurações
```

**Resposta para Membro Normal**:
```
👋 Olá, {nome}! Você já está em nosso grupo de suporte. O que deseja fazer?

[Botões]
➕ Abrir novo chamado | 🔍 Verificar chamado
```

---

#### **Cenário 1B: Usuário NÃO é membro (Novo/Não Verificado)**

**Condição**: `chat.type == 'private'` E usuário não é membro do grupo

**Mensagem de Boas-Vindas**:
```html
🎮 <b>Olá, {nome}! Eu sou o OnCabito!</b> 🤖

Sou o assistente oficial responsável por gerenciar o melhor
grupo de suporte gaming da OnCabo! 🔥

Nossa comunidade é exclusiva para assinantes do plano
OnCabo Gaming, onde você encontra:

🎯 Suporte técnico especializado em jogos
👥 Outros gamers para jogar em squad
🏆 Dicas, torneios e muito mais!

📋 <b>PARA LIBERAR SEU ACESSO</b>

Para verificar se você tem um plano ativo e liberar sua
entrada no grupo, preciso validar seu CPF.

🆔 <b>Por favor, envie seu CPF (apenas números):</b>

Exemplo: 12345678900
```

**Arquivo**: `telegram_bot_handler.py:276-290`

---

#### **Cenário 1C: Comando `/start` usado no grupo**

**Condição**: `chat.type != 'private'`

**Mensagem**:
```html
👋 Olá, {nome}!

Para começar, me envie uma mensagem <b>privada</b> clicando
no meu nome e usando o comando /start.

Lá eu vou te ajudar a acessar o grupo! 🎮
```

**Arquivo**: `telegram_bot_handler.py:340-349`

---

### 1.2. Processamento do CPF

#### **Mensagem de Processamento**

**Quando**: Usuário envia CPF (11 dígitos)

**Mensagem Temporária**:
```html
🔍 <b>Verificando seu CPF...</b>

Aguarde um momento enquanto consulto nossa base de dados.
```

**Arquivo**: `cpf_verification_handler.py:167-171`

---

#### **Resultado 1: CPF Verificado com Sucesso ✅**

**Condição**: CPF encontrado na base HubSoft com plano ativo

**Mensagem**:
```html
✅ <b>PARABÉNS, {nome_cliente}!</b> 🎉

Seu plano OnCabo Gaming está ativo e verificado com sucesso!

🔗 **LINK DE ACESSO AO GRUPO:**
{link_de_convite}

⏰ <b>Atenção:</b> Este link é pessoal e pode ser usado <b>apenas 1 vez</b>!

Clique no link para entrar no grupo. Nos vemos lá! 🔥
```

**Arquivo**: `cpf_verification_handler.py:237-244`

---

#### **Resultado 2: CPF Não Encontrado ❌**

**Condição**: CPF não encontrado ou plano inativo

**Mensagem**:
```html
❌ <b>Ops! Não encontrei seu CPF vinculado a um plano OnCabo Gaming ativo.</b>

Infelizmente, o acesso ao grupo é exclusivo para assinantes do plano OnCabo Gaming.

📌 <b>QUER FAZER PARTE?</b>
Acesse nosso site em {site_url} ou fale conosco pelo WhatsApp em {whatsapp}
para contratar e entrar na comunidade!

Estamos te esperando! 🚀
```

**Arquivo**: `cpf_verification_handler.py:258-265`

---

#### **Resultado 3: CPF Duplicado (Conflito) ⚠️**

**Condição**: CPF já cadastrado em outra conta do Telegram

**Mensagem**:
```markdown
⚠️ **Conflito de CPF Encontrado** ⚠️

Olá! Verifiquei que este CPF já está associado à conta **@{username_antigo}**.

Para garantir a segurança, cada CPF só pode estar vinculado a um único usuário no Telegram.

**O que você gostaria de fazer?**

[Botões]
✅ Usar nesta conta (remover da antiga)
❌ Cancelar e tentar outro CPF
```

**Arquivo**: `cpf_verification_handler.py:192-210`

---

### 1.3. Resolução de Conflito de CPF Duplicado

#### **Opção A: Usuário escolhe "Usar nesta conta"**

**Mensagem de Sucesso**:
```markdown
✅ **Conflito Resolvido!**

O CPF foi associado à sua conta e removido da(s) conta(s) antiga(s).

Seja bem-vindo(a) ao grupo!

🔗 **Seu novo link de acesso:**
{link_de_convite}
```

**Arquivo**: `cpf_verification_handler.py:502-507`

**Mensagem enviada para a conta antiga (removida)**:
```markdown
⚠️ **Atualização de Conta**

Seu CPF foi transferido para outra conta do Telegram (ID: {novo_id}).

Como resultado, você foi removido do grupo OnCabo Gaming.

Se você acredita que isso foi um erro, por favor entre em contato com o suporte.
```

**Arquivo**: `cpf_verification_handler.py:392-400`

---

#### **Opção B: Usuário escolhe "Cancelar"**

**Mensagem**:
```markdown
🚫 **Verificação Cancelada**

Você cancelou a resolução do conflito de CPF.

Para tentar novamente com outro CPF, por favor, use o comando /start.
```

**Arquivo**: `cpf_verification_handler.py:537-542`

---

### 1.4. Lembrete de CPF (5 minutos após /start)

**Condição**: Usuário não enviou CPF após 5 minutos

**Mensagem**:
```
👋 Olá! Só um lembrete amigável de que estou aguardando seu CPF para continuarmos com a verificação.
Pode me enviar apenas os números, por favor? 😊
```

**Arquivo**: `cpf_verification_handler.py:567-572`

---

### 1.5. Mensagens de Status de Verificação

Quando usuário já tem verificação em andamento ou finalizada:

#### **Status: PENDING (Aguardando)**
```markdown
⏳ **Aguardando verificação de CPF**

📝 Por favor, envie seu CPF (apenas números) para continuar.

Digite /ajuda se precisar de mais informações.
```

#### **Status: IN_PROGRESS (Em Andamento)**
```markdown
🔄 **Verificação em andamento**

Aguarde enquanto processamos suas informações.

Em caso de dúvidas, digite /ajuda
```

#### **Status: FAILED (Falhou)**
```markdown
❌ **Verificação não concluída**

Suas tentativas foram esgotadas ou houve um erro.

🔄 Para tentar novamente, digite /start
```

#### **Status: CANCELLED (Cancelada)**
```markdown
🚫 **Verificação cancelada**

Você cancelou o processo de verificação.

🔄 Para tentar novamente, digite /start
```

#### **Status: EXPIRED (Expirada)**
```markdown
⏱️ **Verificação expirada**

O prazo para verificação expirou.

🔄 Para tentar novamente, digite /start
```

**Arquivo**: `cpf_verification_handler.py:120-136`

---

## 2. Fluxo de Suporte (Formulário de Ticket)

### 2.1. Início do Fluxo (`/suporte`)

#### **Cenário 2A: Comando usado no GRUPO por usuário VERIFICADO**

**Mensagem no Grupo**:
```markdown
👋 Olá, @{username}! Recebi seu pedido de suporte e já estou te chamando no privado para começarmos! 🚀
```

*Comando é deletado do grupo*

**Mensagem no Privado (Passo 1 - Categoria)**:
```markdown
🎮 **SUPORTE GAMER ONCABO**

Olá! Fico feliz em te ajudar! 😊

Vou te guiar passo a passo para resolver seu problema da melhor forma.

{barra_progresso} - **Tipo do Problema**

Primeiro, me conta: qual dessas opções descreve melhor o que está acontecendo?

[Botões]
🌐 Conectividade/Ping | ⚡ Performance/FPS
🎮 Problemas no Jogo | 💻 Configuração
📞 Outros
❌ Cancelar
```

**Arquivo**: `telegram_bot_handler.py:427-465`

---

#### **Cenário 2B: Usuário já tem ticket ATIVO**

**Condição**: Usuário já tem um atendimento em andamento

**Mensagem**:
```markdown
Olá, @{username}! 😊

🎮 Vejo que você já tem um atendimento em andamento (Protocolo: `{protocolo}`, Status: {status}).

Por favor, aguarde a resolução antes de abrir um novo chamado.
```

**Arquivo**: `telegram_bot_handler.py:418-423`

---

#### **Cenário 2C: Comando usado no GRUPO por usuário NÃO VERIFICADO**

*O comando é deletado do grupo*

**Mensagem no Privado**:
```
Olá! Para usar os comandos do bot no grupo, você precisa primeiro verificar seu CPF.

Vamos fazer isso agora! Por favor, me envie seu CPF (apenas números) aqui no privado.
```

*Inicia fluxo de verificação de CPF*

**Arquivo**: `telegram_bot_handler.py:368-374`

---

### 2.2. Etapas do Formulário de Suporte

#### **Passo 1: Seleção de Categoria**

Já mostrado acima. Usuário escolhe entre:
- 🌐 Conectividade/Ping
- ⚡ Performance/FPS
- 🎮 Problemas no Jogo
- 💻 Configuração
- 📞 Outros

---

#### **Passo 2: Seleção de Severidade**

**Mensagem**:
```markdown
{barra_progresso} - **Severidade do Problema**

Para priorizar seu atendimento, qual o impacto do problema?

[Botões]
🔴 Crítico - Não consigo jogar
🟠 Alto - Jogo muito prejudicado
🟡 Médio - Incômodo, mas jogável
🟢 Baixo - Melhoria/Sugestão
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~230)

---

#### **Passo 3: Seleção de Jogo**

**Mensagem**:
```markdown
{barra_progresso} - **Jogo Afetado**

Qual jogo está tendo o problema?

[Botões]
CS2 | Valorant
League of Legends | Fortnite
Apex Legends | COD Warzone
Rocket League | Outros
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~336)

---

#### **Passo 4: Descrição do Problema**

**Mensagem**:
```markdown
{barra_progresso} - **Descrição do Problema**

Agora me conte com detalhes o que está acontecendo:

• Quando começou?
• Como o problema se manifesta?
• Já tentou algo para resolver?

💡 Quanto mais detalhes, melhor conseguiremos te ajudar!

[Botões]
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~369)

---

#### **Passo 5: Horário/Timing**

**Mensagem**:
```markdown
{barra_progresso} - **Quando acontece?**

O problema ocorre:

[Botões]
⏰ Sempre
🕐 Em horários específicos
📅 Em dias específicos
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~442)

---

#### **Passo 6: Anexos (Opcional)**

**Mensagem**:
```markdown
{barra_progresso} - **Prints/Evidências (Opcional)**

Tem alguma captura de tela que possa ajudar?

Você pode enviar até 5 imagens.

[Botões]
➡️ Pular esta etapa
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~541-548)

**Mensagem ao receber foto**:
```markdown
📸 **Imagem {número}/5 recebida!**

Pode enviar mais {restante} imagem(ns) ou clicar em "Avançar".

[Botões]
➡️ Avançar
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~814)

---

#### **Passo 7: Confirmação**

**Mensagem**:
```markdown
{barra_progresso} - **Confirmação dos Dados**

📋 **Resumo do seu chamado:**

📂 **Categoria:** {categoria}
🎮 **Jogo:** {jogo}
🔴 **Severidade:** {severidade}

📝 **Descrição:**
{descricao}

⏰ **Ocorrência:** {timing}

📸 **Anexos:** {quantidade} imagem(ns)

Tudo certo para enviar?

[Botões]
✅ Confirmar e Enviar
✏️ Editar Categoria | ✏️ Editar Descrição
⬅️ Voltar | ❌ Cancelar
```

**Arquivo**: `support_form_handler.py` (linha ~603)

---

### 2.3. Finalização do Formulário

#### **Sucesso na Criação do Ticket**

**Mensagem**:
```markdown
✅ **Chamado criado com sucesso!**

📋 **Protocolo:** {protocolo}
📂 **Categoria:** {categoria}
🎮 **Jogo:** {jogo}
🔴 **Prioridade:** {severidade}

📅 **Status:** Aguardando análise

Nossa equipe técnica já foi notificada e em breve entrará em contato!

💡 Use /status para acompanhar o andamento do seu chamado.

Obrigado pela confiança! 🙏
```

**Arquivo**: `support_form_handler.py` (linha ~754)

---

#### **Erro na Criação do Ticket**

**Mensagem**:
```markdown
❌ **Erro ao criar chamado**

{mensagem_erro}

Por favor, tente novamente ou entre em contato com o suporte.

[Botão]
🔄 Tentar Novamente
```

**Arquivo**: `support_form_handler.py` (linha ~736)

---

### 2.4. Cancelamento do Formulário

**Mensagem**:
```markdown
🚫 **Formulário de suporte cancelado**

Seus dados foram descartados.

Se precisar de ajuda, pode usar /suporte novamente a qualquer momento! 😊
```

**Arquivo**: `support_form_handler.py` (linha ~781)

---

## 3. Fluxo de Status de Tickets

### 3.1. Comando `/status` no GRUPO (Usuário Verificado)

*Comando é deletado do grupo*

#### **Cenário 3A: Usuário SEM tickets ativos**

**Mensagem no Grupo (tópico de suporte)**:
```markdown
👋 Olá, @{username}! Você não possui atendimentos ativos no momento.
```

**Arquivo**: `telegram_bot_handler.py:497`

---

#### **Cenário 3B: Usuário COM tickets ativos**

**Mensagem no Grupo (tópico de suporte)**:
```markdown
👋 Olá, @{username}!

Seu chamado mais recente (`{protocolo}`) está com o status: **{status}**.

[Botão]
📋 Ver histórico completo
```

**Arquivo**: `telegram_bot_handler.py:503-508`

*Ao clicar em "Ver histórico completo", a mensagem completa é enviada no PRIVADO*

---

### 3.2. Comando `/status` no PRIVADO

#### **Cenário 3C: Usuário SEM tickets**

**Mensagem**:
```markdown
📋 **Seus Atendimentos**

👋 Olá! Você ainda não tem nenhum atendimento aberto.

💡 **Precisa de ajuda?**
Use o comando /suporte para abrir um novo chamado!
```

**Arquivo**: `telegram_bot_handler.py:146-148`

---

#### **Cenário 3D: Usuário COM tickets (histórico completo)**

**Mensagem**:
```markdown
📋 **Seus Atendimentos**

📊 **Resumo:** {total} atendimento(s) no total
🟢 Ativos: {ativos} | ✅ Finalizados: {finalizados}

🔴 **ATENDIMENTOS ATIVOS**

{emoji} **{protocolo}**
   📂 {categoria} | 📅 {status} • Aberto há {dias} dia(s)
   🎮 {jogo}

✅ **ÚLTIMOS ATENDIMENTOS FINALIZADOS**

{emoji} **{protocolo}**
   📂 {categoria} | 🏁 Status: {status}
   💬 **Solução:** {descricao_fechamento}

... e mais {X} finalizado(s)

💡 **Precisa de ajuda?**
Use o comando /suporte para abrir um novo chamado!
```

**Arquivo**: `telegram_bot_handler.py:154-192`

---

### 3.3. Comando `/status` por usuário NÃO VERIFICADO

*Comando é deletado do grupo*

**Mensagem no Privado**:
```
Olá! Para usar os comandos do bot no grupo, você precisa primeiro verificar seu CPF.

Vamos fazer isso agora! Por favor, me envie seu CPF (apenas números) aqui no privado.
```

*Inicia fluxo de verificação de CPF*

---

## 4. Fluxo de Boas-Vindas e Regras

### 4.1. Novo Membro Entra no Grupo

**Condição**: Usuário entra no grupo pela primeira vez OU não tem regras aceitas

#### **Mensagem de Boas-Vindas (Tópico de Boas-Vindas)**

```html
🎮 <b>Bem-vindo(a), {nome}!</b>

Ficamos muito felizes em ter você conosco no grupo OnCabo Gaming! 🔥

Aqui você encontra:
• 🎯 Suporte técnico especializado em jogos
• 👥 Outros gamers para jogar em squad
• 🏆 Torneios, eventos e muito mais!

Para começar, dê uma olhada nas regras do grupo! 📋
```

**Arquivo**: `telegram_bot_handler.py:1229-1234`

---

#### **Mensagem de Regras (Tópico de Regras)**

```html
📜 <b>Regras do Grupo OnCabo Gaming</b>

Olá, {nome}! Antes de começar, é importante que você leia e aceite nossas regras:

1. Seja respeitoso com todos os membros
2. Não faça spam ou flood
3. Use os tópicos corretos para cada assunto
4. Mantenha o foco em gaming e suporte
5. Respeite a privacidade dos outros

Para confirmar que leu e aceita as regras, clique no botão abaixo:

[Botão]
✅ Li e aceito as regras
```

**Arquivo**: `telegram_bot_handler.py:1238-1247`

---

### 4.2. Aceitação de Regras

**Quando**: Usuário clica em "✅ Li e aceito as regras"

#### **Mensagem de Confirmação (edita a mensagem anterior)**

```html
✅ <b>Regras Aceitas!</b>

Obrigado, {nome}! Você aceitou as regras do grupo.

Agora você tem acesso total a todos os recursos! 🎮

Divirta-se e aproveite a comunidade! 🔥
```

**Arquivo**: `telegram_bot_handler.py:1295-1302`

**Notificação (popup)**:
```
✅ Regras aceitas com sucesso! Bem-vindo(a) ao grupo! 🎮
```

---

### 4.3. Membro Sai do Grupo

**Quando**: Usuário sai ou é removido do grupo

**Ação**: Usuário é desativado no banco de dados automaticamente

**Arquivo**: `telegram_bot_handler.py:1189-1201`

*Não há mensagem enviada ao usuário neste caso*

---

## 5. Fluxo de Usuário Não Verificado

### 5.1. Usuário Não Verificado Tenta Usar Comando no Grupo

**Comandos afetados**: `/suporte`, `/status`

**Ação**:
1. Comando é **deletado do grupo**
2. Mensagem enviada no **privado**
3. Fluxo de **verificação de CPF** é iniciado

**Mensagem no Privado**:
```
Olá! Para usar os comandos do bot no grupo, você precisa primeiro verificar seu CPF.

Vamos fazer isso agora! Por favor, me envie seu CPF (apenas números) aqui no privado.
```

**Arquivo**: `telegram_bot_handler.py:368-374`

---

### 5.2. Usuário Verificado mas com Status != Active

**Cenário**: Usuário tem verificação COMPLETED mas status de usuário não é 'active'

**Mensagem**:
```markdown
Olá! Vejo que você já se verificou antes, mas algo parece estar errado com seu acesso.
Por favor, use /start para reiniciar o processo ou contate o suporte.
```

**Arquivo**: `telegram_bot_handler.py:970-973`

---

### 5.3. Primeira Interação com o Bot (Mensagem de Texto Aleatória)

**Condição**: Usuário nunca teve verificação e envia qualquer texto (que não seja CPF)

**Ação**: Inicia fluxo de boas-vindas automaticamente

**Mensagem**:
*Mesma mensagem de boas-vindas do `/start`*

**Arquivo**: `telegram_bot_handler.py:936-937`

---

### 5.4. Usuário Verificado Envia Mensagem de Texto Aleatória

**Condição**: Usuário está ativo mas envia texto que não faz parte de nenhum fluxo

**Mensagem**:
```
💬 Mensagem recebida!

Para criar um atendimento, use /suporte
Para verificar status, use /status

📋 Digite /ajuda para ver todos os comandos.
```

**Arquivo**: `telegram_bot_handler.py:944-950`

---

## 6. Mensagens de Erro e Sistema

### 6.1. Erro ao Processar CPF

**Mensagem**:
```html
❌ <b>Erro ao verificar CPF.</b>

Tente novamente ou entre em contato com o suporte.
```

**Arquivo**: `cpf_verification_handler.py:281-284`

---

### 6.2. Erro ao Processar Mensagem de Texto

**Mensagem**:
```
❌ Erro ao processar mensagem.
```

**Arquivo**: `telegram_bot_handler.py:978-980`

---

### 6.3. Erro ao Processar Foto

**Mensagem**:
```
❌ Erro ao processar foto. Tente novamente.
```

**Arquivo**: `telegram_bot_handler.py:1010-1012`

---

### 6.4. Erro Geral no Bot

**Mensagem**:
```
❌ Ocorreu um erro inesperado. Tente novamente mais tarde.
```

**Arquivo**: `telegram_bot_handler.py:1330-1333`

---

### 6.5. Sistema de Verificação Indisponível

**Mensagem**:
```
⚠️ Sistema de verificação indisponível.

Tente novamente mais tarde.
```

**Arquivo**: `cpf_verification_handler.py:96`

---

### 6.6. Nenhuma Verificação Encontrada

**Mensagem**:
```
⚠️ Nenhuma verificação encontrada.

Digite /start para iniciar.
```

**Arquivo**: `cpf_verification_handler.py:105`

---

### 6.7. Erro ao Verificar Informações (Problema de Permissão)

**Mensagem**:
```
🤖 Ops! Tive um problema para verificar suas informações.
Por favor, tente novamente em alguns instantes ou contate o suporte se o erro persistir.
```

**Arquivo**: `telegram_bot_handler.py:266-269`

---

### 6.8. Limite de Tentativas de Verificação Atingido

**Mensagem**:
```markdown
⚠️ **Limite de Tentativas Atingido**

Você realizou muitas tentativas de verificação nas últimas 24 horas.
Por favor, aguarde e tente novamente amanhã ou entre em contato com o suporte se acreditar que isso é um erro.
```

**Arquivo**: `telegram_bot_handler.py:313-317`

---

### 6.9. Foto Recebida Fora do Fluxo de Suporte

**Mensagem**:
```markdown
📷 Foto recebida!

Para criar um atendimento com anexos, use /suporte
```

**Arquivo**: `telegram_bot_handler.py:1002-1005`

---

## Resumo de Estatísticas

### Quantidade de Mensagens Únicas: **~60 mensagens diferentes**

### Quantidade de Interações (Botões): **~40 botões inline**

### Handlers Principais:
1. **TelegramBotHandler** - 1334 linhas
2. **SupportFormHandler** - 904 linhas
3. **CPFVerificationHandler** - 606 linhas

### Fluxos Principais:
1. ✅ Verificação de CPF (10 mensagens)
2. 🎫 Formulário de Suporte (15 mensagens)
3. 📊 Status de Tickets (5 mensagens)
4. 👋 Boas-Vindas e Regras (4 mensagens)
5. 🚫 Usuário Não Verificado (6 mensagens)
6. ⚠️ Erros e Sistema (10 mensagens)

---

## Diagrama de Fluxos (Próxima Seção)

Nos próximos documentos, cada um destes fluxos terá um diagrama detalhado mostrando:
- Pontos de decisão
- Caminhos possíveis
- Mensagens enviadas
- Ações executadas
- Transições de estado

---

**Fim do Mapeamento de Mensagens**

*Documento gerado automaticamente a partir do código-fonte em 14/10/2025*
