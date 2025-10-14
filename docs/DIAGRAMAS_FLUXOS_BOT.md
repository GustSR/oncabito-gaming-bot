# Diagramas de Fluxos do Bot Sentinela

> Documentação gerada em 14/10/2025
>
> Diagramas detalhados de TODOS os fluxos de interação do bot

---

## Índice

1. [Fluxo de Verificação de CPF](#1-fluxo-de-verificação-de-cpf)
2. [Fluxo de Suporte (Formulário)](#2-fluxo-de-suporte-formulário)
3. [Fluxo de Status de Tickets](#3-fluxo-de-status-de-tickets)
4. [Fluxo de Boas-Vindas](#4-fluxo-de-boas-vindas)
5. [Fluxo de Proteção (Guarda)](#5-fluxo-de-proteção-guarda)

---

## 1. Fluxo de Verificação de CPF

### Diagrama Completo

```
                                    USUÁRIO ENVIA /START
                                            │
                                            ▼
                          ┌─────────────────┴─────────────────┐
                          │                                   │
                          │        Chat é PRIVADO?            │
                          │                                   │
                          └─────────┬───────────────┬─────────┘
                                   SIM            NÃO
                                    │              │
                                    ▼              ▼
                    ┌───────────────────┐   [Mensagem: "Me envie
                    │ Usuário é membro  │    mensagem privada"]
                    │   do grupo?       │          │
                    └─────┬─────────┬───┘          │
                         SIM       NÃO             │
                          │         │              │
                          ▼         ▼              │
                   ┌──────────┐  ┌──────────┐     │
                   │ É admin? │  │  FLUXO   │     │
                   └──┬───┬───┘  │   NOVO   │     │
                     SIM NÃO     │ USUÁRIO  │     │
                      │   │      └────┬─────┘     │
                      │   │           │           │
                      ▼   ▼           ▼           ▼
                   [Menu]  [Menu]  [Boas-vindas] [FIM]
                   [Admin] [User]      │
                      │      │          │
                      └──────┴──────────┴─────────── FIM


                      FLUXO NOVO USUÁRIO (Detalhado)
                      ═══════════════════════════════

                           [Mensagem de Boas-Vindas]
                           "Olá! Sou o OnCabito..."
                           "Envie seu CPF:"
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Cria Verificação     │
                         │ Status: PENDING      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Agenda Lembrete      │
                         │ (5 minutos)          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Aguarda CPF          │
                         │ waiting_cpf = True   │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
               USUÁRIO ENVIA CPF            TIMEOUT (5min)
                    │                               │
                    ▼                               ▼
         [Mensagem: "Verificando..."]    [Mensagem: "Lembrete
                    │                      de CPF aguardando"]
                    ▼                               │
         ┌──────────────────┐                      │
         │ Valida Formato   │                      │
         └────────┬─────────┘                      │
                  │                                 │
        ┌─────────┴──────────┐                     │
       CPF      CPF          CPF                   │
      VÁLIDO  INVÁLIDO    DUPLICADO                │
        │         │          │                      │
        ▼         ▼          ▼                      │
    [Busca]  [Erro]   [Detecta Conflito]           │
    [HubSoft] [Msg]         │                       │
        │                   ▼                       │
        │         ┌─────────────────────┐           │
        │         │ Mensagem: Conflito  │           │
        │         │ com @usuario_antigo │           │
        │         └─────────┬───────────┘           │
        │                   │                       │
        │         ┌─────────┴─────────┐             │
        │        [Botão]           [Botão]          │
        │      "Usar nesta        "Cancelar"        │
        │       conta"                │              │
        │         │                   │              │
        │         ▼                   ▼              │
        │    [Remove]           [Cancela]           │
        │    [Antigo]          [Verificação]        │
        │    [Cria Link]            │               │
        │         │                 │               │
        │         └─────────┬───────┘               │
        │                   │                       │
        ▼                   ▼                       ▼
   ┌────────────────────────────────────────────────┐
   │         RESULTADO DA VERIFICAÇÃO                │
   └────┬───────────────────────────┬───────────────┘
        │                           │
   ENCONTRADO                  NÃO ENCONTRADO
   (Plano Ativo)               (Sem Plano)
        │                           │
        ▼                           ▼
  ┌─────────────┐           ┌──────────────┐
  │ Cria Link   │           │ Mensagem:    │
  │ de Convite  │           │ "CPF não     │
  │ (1 uso)     │           │  encontrado" │
  └──────┬──────┘           └──────┬───────┘
         │                         │
         ▼                         ▼
  [Mensagem:              [Links para Site]
   "PARABÉNS!             [e WhatsApp]
   Link: {url}"]                  │
         │                        │
         ▼                        ▼
  ┌─────────────┐         ┌─────────────┐
  │ Salva User  │         │   FIM       │
  │ Status:     │         └─────────────┘
  │ ACTIVE      │
  └──────┬──────┘
         │
         ▼
    ┌────────┐
    │  FIM   │
    └────────┘
```

---

## 2. Fluxo de Suporte (Formulário)

### Diagrama Completo

```
                          USUÁRIO ENVIA /SUPORTE
                                    │
                                    ▼
                     ┌──────────────────────────┐
                     │ Guarda de Verificação    │
                     │ (check_and_redirect...)  │
                     └────────┬─────────────────┘
                              │
                    ┌─────────┴──────────┐
                   SIM                  NÃO
             (É grupo E                (Privado OU
              NÃO verificado)          Verificado)
                    │                     │
                    ▼                     ▼
            [Deleta Comando]    ┌────────────────┐
            [Redireciona para   │ Verifica se    │
             Verificação CPF]   │ tem ticket     │
                    │            │ ATIVO          │
                    ▼            └────┬───────────┘
                 [FIM]                │
                              ┌───────┴────────┐
                            TEM              NÃO TEM
                             │                  │
                             ▼                  ▼
                    [Mensagem: "Você      ┌─────────────┐
                     já tem ticket        │ Inicia      │
                     {protocolo}"]        │ Formulário  │
                             │            └──────┬──────┘
                             ▼                   │
                          [FIM]                  │
                                                 │
                    ┌────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────────────────┐
    │           FORMULÁRIO DE SUPORTE (7 PASSOS)         │
    └───────────────────────────────────────────────────┘
                    │
                    ▼
    ═════════════════════════════════════════════════════

                PASSO 1: CATEGORIA
                ═══════════════════

        [Mensagem: "Qual tipo de problema?"]
                    │
        ┌───────────┼───────────┬─────────┬────────┐
        │           │           │         │        │
        ▼           ▼           ▼         ▼        ▼
   [Conecti-]  [Perfor-]  [Problemas] [Config] [Outros]
   [vidade]    [mance]    [no Jogo]
        │           │           │         │        │
        └───────────┴───────────┴─────────┴────────┘
                    │
                    ▼

                PASSO 2: SEVERIDADE
                ═══════════════════

        [Mensagem: "Qual o impacto?"]
                    │
        ┌───────────┼───────────┬─────────┐
        │           │           │         │
        ▼           ▼           ▼         ▼
    [Crítico]   [Alto]     [Médio]   [Baixo]
    [🔴]        [🟠]       [🟡]      [🟢]
        │           │           │         │
        └───────────┴───────────┴─────────┘
                    │
                    ▼

                PASSO 3: JOGO
                ═════════════

        [Mensagem: "Qual jogo?"]
                    │
        ┌───────────┼───────────┬─────────┬────────┐
        │           │           │         │        │
        ▼           ▼           ▼         ▼        ▼
      [CS2]    [Valorant]   [LoL]   [Fortnite] [Outros]
        │           │           │         │        │
        └───────────┴───────────┴─────────┴────────┘
                    │
                    ▼

                PASSO 4: DESCRIÇÃO
                ══════════════════

        [Mensagem: "Descreva o problema"]
                    │
                    ▼
        ┌───────────────────────┐
        │ Aguarda Texto         │
        │ (mínimo 10 chars)     │
        └───────────┬───────────┘
                    │
                    ▼

                PASSO 5: TIMING
                ═══════════════

        [Mensagem: "Quando acontece?"]
                    │
        ┌───────────┼───────────┬─────────────┐
        │           │           │             │
        ▼           ▼           ▼             ▼
    [Sempre]  [Horário]  [Dias]      [Não sei]
                    │
        └───────────┴───────────┴─────────────┘
                    │
                    ▼

                PASSO 6: ANEXOS (OPCIONAL)
                ══════════════════════════

        [Mensagem: "Envie prints (opcional)"]
                    │
        ┌───────────┴───────────┐
        │                       │
    [Envia Fotos]          [Pular]
    (até 5)                    │
        │                      │
        ▼                      │
    [Armazena                  │
     file_ids]                 │
        │                      │
        └──────────────────────┘
                    │
                    ▼

                PASSO 7: CONFIRMAÇÃO
                ════════════════════

        [Resumo de todos os dados]
                    │
        ┌───────────┴───────────┬──────────┐
        │                       │          │
    [Confirmar]            [Editar]   [Cancelar]
        │                       │          │
        ▼                       │          ▼
    ┌────────────┐             │      [Limpa]
    │ Envia para │             │      [Sessão]
    │  HubSoft   │             │         │
    └─────┬──────┘             │         ▼
          │                    │      [FIM]
          ▼                    │
    ┌────────────┐             │
    │  Sucesso?  │             │
    └─────┬──────┘             │
          │                    │
    ┌─────┴─────┐              │
   SIM         NÃO             │
    │           │              │
    ▼           ▼              ▼
[Ticket]    [Erro]      [Volta para]
[Criado]    [Msg]       [Passo escolhido]
[Limpa]       │                │
[Sessão]      │                │
    │         │                │
    ▼         ▼                ▼
[Mensagem:  [Tenta]     [Continua]
 "Sucesso!  [Novamente] [Formulário]
  {proto}"]      │
    │            │
    ▼            ▼
  [FIM]        [FIM]

═════════════════════════════════════════════════════

    PERSISTÊNCIA (FEATURE ESPECIAL)
    ═══════════════════════════════

    A cada passo, o estado é salvo no banco:

    ┌─────────────────────────────────────┐
    │  support_sessions (tabela SQLite)   │
    ├─────────────────────────────────────┤
    │ user_id: 123456789                  │
    │ current_step: "descricao"           │
    │ state_json: {                       │
    │   "categoria": "conectividade",     │
    │   "severidade": "alta",             │
    │   "jogo": "CS2",                    │
    │   "descricao": "Ping alto..."       │
    │ }                                   │
    │ expires_at: 24h depois              │
    └─────────────────────────────────────┘

    Se o BOT REINICIAR:
    ├─ Usuário pode continuar de onde parou
    ├─ Usa /suporte novamente
    └─ Bot carrega progresso do banco
```

---

## 3. Fluxo de Status de Tickets

### Diagrama Completo

```
                          USUÁRIO ENVIA /STATUS
                                    │
                                    ▼
                     ┌──────────────────────────┐
                     │ Guarda de Verificação    │
                     │ (check_and_redirect...)  │
                     └────────┬─────────────────┘
                              │
                    ┌─────────┴──────────┐
                   SIM                  NÃO
             (É grupo E                (Privado OU
              NÃO verificado)          Verificado)
                    │                     │
                    ▼                     ▼
            [Deleta Comando]    ┌────────────────┐
            [Redireciona para   │ É GRUPO ou     │
             Verificação CPF]   │ PRIVADO?       │
                    │            └────┬───────────┘
                    ▼                 │
                 [FIM]      ┌─────────┴─────────┐
                           GRUPO             PRIVADO
                            │                   │
                            ▼                   ▼
                   ┌────────────────┐   ┌────────────────┐
                   │ Busca Tickets  │   │ Busca TODOS os │
                   │ ATIVOS do user │   │ Tickets (Full) │
                   └────────┬───────┘   └────────┬───────┘
                            │                    │
                  ┌─────────┴─────────┐          │
                TEM                NÃO TEM       │
                 │                    │          │
                 ▼                    ▼          │
         ┌──────────────┐    ┌────────────┐     │
         │ Pega ÚLTIMO  │    │ Mensagem:  │     │
         │ ticket ativo │    │ "Sem       │     │
         └──────┬───────┘    │  tickets"  │     │
                │            └─────┬──────┘     │
                ▼                  │             │
         [Mensagem no Grupo:       │             │
          "Chamado {proto}         │             │
           Status: {status}"]      │             │
                │                  │             │
                ▼                  │             │
         [Botão: "Ver              │             │
          histórico completo"]     │             │
                │                  │             │
                │ [Clica]          │             │
                ▼                  │             │
         ┌──────────────┐          │             │
         │ Envia FULL   │          │             │
         │ no PRIVADO   │          │             │
         └──────┬───────┘          │             │
                │                  │             │
                └──────────────────┴─────────────┘
                                   │
                                   ▼
                                 [FIM]


            MENSAGEM COMPLETA (PRIVADO)
            ═══════════════════════════

            ┌────────────────────────────┐
            │ 📋 Seus Atendimentos       │
            ├────────────────────────────┤
            │ 📊 Resumo:                 │
            │   Total: X                 │
            │   Ativos: Y                │
            │   Finalizados: Z           │
            ├────────────────────────────┤
            │ 🔴 ATIVOS                  │
            │   {emoji} {protocolo}      │
            │   📂 {categoria}           │
            │   📅 {status} • {dias}d    │
            │   🎮 {jogo}                │
            ├────────────────────────────┤
            │ ✅ FINALIZADOS (últimos 3) │
            │   {emoji} {protocolo}      │
            │   📂 {categoria}           │
            │   🏁 {status}              │
            │   💬 Solução: {desc}       │
            │                            │
            │   ... e mais X tickets     │
            ├────────────────────────────┤
            │ 💡 Precisa de ajuda?       │
            │ Use /suporte               │
            └────────────────────────────┘
```

---

## 4. Fluxo de Boas-Vindas

### Diagrama Completo

```
                    NOVO MEMBRO ENTRA NO GRUPO
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Evento: ChatMember    │
                    │ Status: member        │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Busca User no Banco   │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                   SIM                     NÃO
             (User existe)          (User novo)
                    │                       │
                    ▼                       │
        ┌───────────────────┐              │
        │ Rules Accepted?   │              │
        └───────┬───────────┘              │
                │                          │
        ┌───────┴───────┐                  │
       SIM             NÃO                 │
        │               │                  │
        ▼               │                  │
    [Pula Boas-        │                  │
     Vindas]           │                  │
        │               │                  │
        ▼               ▼                  ▼
     [FIM]    ┌────────────────────────────┐
              │   INICIA FLUXO DE          │
              │   BOAS-VINDAS              │
              └────────────┬───────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │ MENSAGEM 1:                │
              │ Tópico de Boas-Vindas      │
              ├────────────────────────────┤
              │ 🎮 Bem-vindo, {nome}!      │
              │                            │
              │ Ficamos felizes em ter     │
              │ você conosco!              │
              │                            │
              │ 🎯 Suporte técnico         │
              │ 👥 Gamers para squad       │
              │ 🏆 Torneios e eventos      │
              └────────────┬───────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │ MENSAGEM 2:                │
              │ Tópico de Regras           │
              ├────────────────────────────┤
              │ 📜 Regras do Grupo         │
              │                            │
              │ 1. Seja respeitoso         │
              │ 2. Não faça spam           │
              │ 3. Use tópicos corretos    │
              │ 4. Foco em gaming          │
              │ 5. Respeite privacidade    │
              │                            │
              │ [Botão]                    │
              │ ✅ Li e aceito as regras   │
              └────────────┬───────────────┘
                           │
                           ▼
                 ┌─────────────────┐
                 │ Aguarda Ação    │
                 │ do Usuário      │
                 └─────────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         [Clica Botão]            [Ignora]
              │                         │
              ▼                         ▼
    ┌──────────────────┐         ┌────────────┐
    │ Salva no Banco:  │         │ Fica       │
    │ rules_accepted   │         │ Pendente   │
    │ = TRUE           │         └─────┬──────┘
    └────────┬─────────┘               │
             │                         │
             ▼                         ▼
    [Edita Mensagem:           [Pode ver grupo
     "Regras Aceitas!          mas sem confirmar
      Bem-vindo!"]             aceitação]
             │                         │
             ▼                         ▼
         [Popup:                    [FIM]
          "Sucesso!"]
             │
             ▼
          [FIM]


    CASO ESPECIAL: USUÁRIO SAI DO GRUPO
    ════════════════════════════════════

                USUÁRIO SAI/É REMOVIDO
                         │
                         ▼
              ┌──────────────────────┐
              │ Evento: ChatMember   │
              │ Status: left/kicked  │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Busca User no Banco  │
              └──────────┬───────────┘
                         │
                    ┌────┴────┐
                   SIM      NÃO
                    │         │
                    ▼         ▼
          ┌─────────────┐  [FIM]
          │ Desativa    │
          │ User no DB  │
          │ Status:     │
          │ inactive    │
          └──────┬──────┘
                 │
                 ▼
          ┌─────────────┐
          │ Reseta      │
          │ rules_      │
          │ accepted    │
          │ = FALSE     │
          └──────┬──────┘
                 │
                 ▼
              [FIM]
```

---

## 5. Fluxo de Proteção (Guarda)

### Diagrama Completo

```
        USUÁRIO NÃO VERIFICADO USA COMANDO NO GRUPO
        (/suporte, /status, etc.)
                         │
                         ▼
            ┌────────────────────────────┐
            │ _check_and_redirect_       │
            │ unverified_group_user()    │
            └────────────┬───────────────┘
                         │
                         ▼
            ┌────────────────────────────┐
            │ É GRUPO?                   │
            └────────┬───────────────────┘
                     │
         ┌───────────┴───────────┐
        SIM                     NÃO
         │                       │
         ▼                       ▼
    ┌─────────────┐      ┌──────────────┐
    │ Usuário     │      │ Continua     │
    │ Verificado? │      │ Fluxo Normal │
    └──────┬──────┘      └──────┬───────┘
           │                    │
    ┌──────┴──────┐             ▼
   SIM           NÃO         [return True]
    │             │
    ▼             ▼
[return     ┌────────────────────┐
 True]      │ PROTEÇÃO ATIVADA   │
            └─────────┬──────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ PASSO 1:            │
            │ Deleta comando      │
            │ do grupo            │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ PASSO 2:            │
            │ Envia mensagem      │
            │ no PRIVADO:         │
            │                     │
            │ "Você precisa       │
            │  verificar seu CPF" │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ PASSO 3:            │
            │ Inicia Verificação  │
            │ no Banco            │
            │ Status: PENDING     │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ PASSO 4:            │
            │ Define flag:        │
            │ waiting_cpf = True  │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ PASSO 5:            │
            │ return False        │
            │ (para execução      │
            │  do comando)        │
            └─────────┬───────────┘
                      │
                      ▼
                   [FIM]


    FLUXO COMPLETO VISUAL
    ═══════════════════════

    GRUPO                           PRIVADO
    ═════                           ═══════

    Usuário:                        Bot:
    "/suporte"                      "Olá! Você precisa
         │                           verificar seu CPF."
         │                                  │
         ▼                                  ▼
    [Mensagem                        "Me envie seu CPF
     deletada]                        (apenas números)"
         │                                  │
         │                                  ▼
         │                           ┌──────────────┐
         │                           │ Aguarda CPF  │
         │                           └──────┬───────┘
         │                                  │
         │                           Usuário envia CPF
         │                                  │
         │                                  ▼
         │                           [Verifica CPF]
         │                                  │
         │                         ┌────────┴────────┐
         │                      VÁLIDO            INVÁLIDO
         │                         │                  │
         │                         ▼                  ▼
         │                   [Link de           [Mensagem
         │                    Convite]           de Erro]
         │                         │
         │                         ▼
         └─────────────────►  [Usuário entra
                               no grupo
                               VERIFICADO]
```

---

## 6. Fluxo de Duplicata (Checkup Proativo)

### Diagrama Completo

```
                CRON JOB DIÁRIO (3h AM)
                         │
                         ▼
            ┌────────────────────────┐
            │ Script: daily_cpf_     │
            │ checkup.py             │
            └────────────┬───────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Busca todos Users      │
            │ com Status ACTIVE      │
            └────────────┬───────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Agrupa por CPF_HASH    │
            └────────────┬───────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ CPF com 2+ users?      │
            └────────┬───────────────┘
                     │
         ┌───────────┴───────────┐
        NÃO                     SIM
         │                       │
         ▼                       ▼
      [OK]          ┌────────────────────┐
         │          │ DUPLICATA          │
         │          │ DETECTADA!         │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Cria Conflict      │
         │          │ no Banco           │
         │          │ Status: PENDING    │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Para cada User     │
         │          │ envolvido:         │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────────┐
         │          │ Envia DM:              │
         │          │                        │
         │          │ ⚠️ Detectamos que seu  │
         │          │ CPF está em 2 contas   │
         │          │                        │
         │          │ Contas:                │
         │          │ • @user1 (ID: 111)     │
         │          │ • @user2 (ID: 222)     │
         │          │                        │
         │          │ Escolha qual manter:   │
         │          │                        │
         │          │ [Botão] Manter ID 111  │
         │          │ [Botão] Manter ID 222  │
         │          └─────────┬──────────────┘
         │                    │
         │                    ▼
         │          ┌─────────────────────┐
         │          │ Aguarda Resposta    │
         │          │ (Qualquer um dos    │
         │          │  usuários pode      │
         │          │  responder)         │
         │          └──────────┬──────────┘
         │                     │
         │          ┌──────────┴──────────┐
         │          │                     │
         │    [Usuário 1]            [Usuário 2]
         │     responde               responde
         │          │                     │
         │          └──────────┬──────────┘
         │                     │
         │                     ▼
         │          ┌────────────────────┐
         │          │ Escolheu ID: XXX   │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Remove outros IDs  │
         │          │ do grupo           │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Desativa Users     │
         │          │ removidos no DB    │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Envia DM para      │
         │          │ removidos:         │
         │          │                    │
         │          │ "Seu CPF foi       │
         │          │  transferido para  │
         │          │  outra conta"      │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Cria Link Convite  │
         │          │ para ID mantido    │
         │          └─────────┬──────────┘
         │                    │
         │                    ▼
         │          ┌────────────────────┐
         │          │ Marca Conflict     │
         │          │ Status: RESOLVED   │
         │          └─────────┬──────────┘
         │                    │
         ▼                    ▼
      [FIM]               [FIM]
```

---

## Resumo de Proteções e Validações

### Proteções Implementadas

| Proteção | Localização | Descrição |
|----------|-------------|-----------|
| **Guarda de Grupo** | `_check_and_redirect_unverified_group_user` | Impede comandos de não verificados no grupo |
| **Limite de Tentativas** | `cpf_verification_use_case` | Máximo 3 tentativas de CPF em 24h |
| **Expiração de Verificação** | `cpf_verification` entity | Verificação expira em 10 minutos |
| **Link Único** | `create_chat_invite_link` | Link de convite usado apenas 1 vez |
| **Sessão com Timeout** | `support_sessions` table | Formulário expira em 24h |
| **Ticket Ativo** | `handle_support_command` | Bloqueia novo ticket se já tem ativo |
| **Duplicata Proativa** | `daily_cpf_checkup` | Detecta CPFs duplicados diariamente |
| **Desativação Automática** | `handle_new_member` | Desativa user ao sair do grupo |

---

## Estatísticas de Fluxos

### Pontos de Decisão por Fluxo

| Fluxo | Decisões | Caminhos Possíveis | Mensagens Únicas |
|-------|----------|-------------------|------------------|
| **Verificação CPF** | 8 | 12 | 15 |
| **Suporte** | 10 | 15 | 20 |
| **Status** | 5 | 6 | 8 |
| **Boas-Vindas** | 3 | 4 | 4 |
| **Guarda** | 3 | 2 | 3 |
| **Duplicata** | 4 | 5 | 5 |

**Total**: 33 pontos de decisão, 44 caminhos possíveis, ~60 mensagens únicas

---

**Fim dos Diagramas**

*Documento gerado automaticamente em 14/10/2025*
