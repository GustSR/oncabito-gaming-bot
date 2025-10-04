# 🏛️ Decisões Arquiteturais (ADR - Architectural Decision Records)

## Índice
- [ADR-001: HubSoft como Single Source of Truth para Tickets](#adr-001-hubsoft-como-single-source-of-truth-para-tickets)

---

## ADR-001: HubSoft como Single Source of Truth para Tickets

**Status:** ✅ APROVADO
**Data:** 2025-10-03
**Contexto:** Sistema de tickets de suporte
**Decisores:** Equipe de Desenvolvimento

### 📋 Contexto e Problema

Durante a migração para Clean Architecture, surgiu a questão sobre onde e como persistir os dados de tickets de suporte. As opções consideradas foram:

1. Persistir localmente no SQLite E no HubSoft (duplicação de dados)
2. Persistir apenas no HubSoft (fonte única)
3. Persistir localmente com sincronização periódica

**Problema identificado:** A tabela `support_tickets` estava sendo acessada diretamente pela camada de presentation, violando a Clean Architecture. Além disso, haveria risco de dessincronização entre banco local e HubSoft.

### 🎯 Decisão

**Tickets de suporte NÃO serão persistidos localmente** no banco de dados SQLite. O **HubSoft é a única fonte da verdade** (Single Source of Truth) para todos os dados de tickets.

### 💡 Motivação

#### Vantagens da abordagem escolhida:

1. **✅ Evitar Dessincronização**
   - Dados sempre consistentes entre bot e HubSoft
   - Não há conflito entre "versão local" vs "versão HubSoft"
   - Mudanças feitas por técnicos no HubSoft aparecem imediatamente

2. **✅ Simplicidade e Manutenibilidade**
   - Menos código para manter
   - Menos bugs potenciais
   - Menos migrations de banco
   - Não precisa gerenciar sincronização bidirecional

3. **✅ Dados Sempre Atualizados**
   - Status do ticket reflete a realidade do sistema
   - Atualizações em tempo real
   - Sem cache desatualizado

4. **✅ Menos Estado para Gerenciar**
   - Não precisamos duplicar regras de negócio
   - HubSoft já gerencia todo o ciclo de vida do ticket
   - Bot apenas consome e exibe dados

### 🔄 Implementação

#### Fluxo de Criação de Ticket:
```python
1. Usuário solicita ticket via /suporte
2. Bot valida dados
3. Cria ticket no HubSoft via API (fonte única)
4. Obtém protocolo do HubSoft
5. Exibe protocolo ao usuário
6. NÃO salva localmente
```

#### Fluxo de Consulta de Status:
```python
1. Usuário solicita /status
2. Bot busca tickets do HubSoft via API
3. Exibe lista atualizada
4. NÃO consulta banco local
```

#### Código Afetado:

**Removido:**
- `_get_tickets_from_old_table()` - Método que acessava SQLite diretamente
- Import `aiosqlite` da camada presentation

**Adicionado:**
- `HubSoftIntegrationUseCase.get_user_tickets()` - Busca todos os tickets
- `HubSoftIntegrationUseCase.get_user_active_tickets()` - Busca apenas ativos

**Arquivos modificados:**
- `src/sentinela/presentation/handlers/telegram_bot_handler.py` (linhas 340, 508)
- `src/sentinela/application/use_cases/hubsoft_integration_use_case.py` (novos métodos)

### ⚠️ Consequências

#### Positivas:
- ✅ Zero conflitos de dados
- ✅ Código mais simples e limpo
- ✅ Menos manutenção
- ✅ Sempre atualizado
- ✅ Clean Architecture respeitada

#### Negativas:
- ⚠️ Dependência da disponibilidade da API HubSoft
- ⚠️ Latência de rede em cada consulta
- ⚠️ Sem dados históricos se HubSoft estiver indisponível

#### Mitigações para Negativas:
- Sistema HubSoft tem alta disponibilidade (SLA 99.9%)
- Latência aceitável para o volume atual de usuários
- Fallback: Mensagem de erro clara quando API indisponível

### 🚫 Alternativas Consideradas e Rejeitadas

#### ❌ Opção 1: Persistência Local + Sincronização
**Por que foi rejeitada:**
- Complexidade alta demais
- Risco de dados dessincronizados
- Precisa gerenciar conflitos (local vs remoto)
- Mais migrations, mais código, mais bugs

#### ❌ Opção 2: Cache Local (Redis/Memória)
**Por que foi rejeitada:**
- Overhead desnecessário para volume atual
- Adiciona dependência (Redis)
- Dados ainda podem ficar desatualizados
- Complexidade de invalidação de cache

#### ❌ Opção 3: Tabela Local como Espelho
**Por que foi rejeitada:**
- Ainda precisa sincronização
- Dados podem ficar desatualizados
- Violaria princípio de Single Source of Truth

### 📊 Impacto

#### Componentes Afetados:
- ✅ `telegram_bot_handler.py` - Usa apenas `HubSoftIntegrationUseCase`
- ✅ Tabela `support_tickets` - **DEPRECATED** (não mais usada para novos tickets)
- ✅ Comandos `/suporte` e `/status` - Agora buscam do HubSoft

#### Componentes NÃO Afetados:
- ✅ Outras tabelas (users, cpf_verifications, etc)
- ✅ Sistema de eventos
- ✅ Repositories de outras entidades

### 🔍 Validação

Para validar esta decisão:

1. ✅ Verificar que `/suporte` cria ticket apenas no HubSoft
2. ✅ Verificar que `/status` busca dados apenas do HubSoft
3. ✅ Confirmar que NÃO há consultas SQL a `support_tickets` em presentation
4. ✅ Testar que dados exibidos refletem mudanças feitas no HubSoft

### 📚 Referências

- Clean Architecture - Robert C. Martin
- Single Source of Truth Pattern
- API-First Design Principles
- Tabela `support_tickets` marcada como DEPRECATED em `migrations/001_create_initial_schema.sql`

### 📝 Notas

Esta decisão pode ser revisitada no futuro SE:
1. Volume de usuários aumentar significativamente (> 10.000 tickets/dia)
2. HubSoft API apresentar instabilidade crônica
3. Requisitos de relatórios históricos offline surgirem

Por enquanto, mantemos a simplicidade e a confiabilidade do Single Source of Truth.

---

**Última atualização:** 2025-10-03
**Próxima revisão:** Quando atingir 1.000 tickets/mês
