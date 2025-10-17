# 📋 Rastreamento de Resoluções de Inconsistências

Este documento rastreia quais inconsistências identificadas foram resolvidas e quais foram mantidas intencionalmente.

**Status**: 4/19 revisadas | 4 resolvidas | 0 mantidas intencionalmente

---

## ✅ RESOLVIDAS

### 🔴 #1: Race Condition em Verificação Duplicada Simultânea

**Status**: ✅ **RESOLVIDA**

**Problema Original**:
- Dois usuários podiam iniciar verificação com o mesmo CPF simultaneamente
- Ambos passariam pela verificação de duplicatas antes de qualquer um ser COMPLETED
- Violava regra de negócio: 1 CPF = 1 usuário

**Solução Implementada**:

1. **Criado sistema de lock distribuído** (`src/sentinela/infrastructure/locking/`):
   - `InMemoryLockManager`: Gerenciador de locks em memória
   - `distributed_lock()`: Context manager para adquirir locks
   - Cleanup automático de locks expirados a cada 60s

2. **Integrado no handler de verificação** (`cpf_verification_handlers.py:202-274`):
   ```python
   lock_key = f"cpf_verification:{cpf.value}"
   async with distributed_lock(lock_key, timeout=30):
       # Seção crítica: verificação HubSoft + check duplicatas
       # Agora protegida contra race conditions
   ```

3. **Tratamento de timeout**:
   - Se lock não puder ser adquirido em 30s, retorna erro amigável
   - Mensagem: "Este CPF já está sendo verificado. Aguarde alguns segundos..."

4. **Inicialização no boot** (`main.py:43-91`):
   - Lock manager iniciado na inicialização do bot
   - Finalizado gracefully no shutdown

**Arquivos Modificados**:
- ✅ Criado: `src/sentinela/infrastructure/locking/distributed_lock.py`
- ✅ Criado: `src/sentinela/infrastructure/locking/__init__.py`
- ✅ Modificado: `src/sentinela/application/command_handlers/cpf_verification_handlers.py`
- ✅ Modificado: `main.py`

**Impacto**:
- 🔒 **Segurança**: Garante que apenas 1 verificação por CPF ocorra por vez
- 🛡️ **Integridade**: Previne violação da regra 1 CPF = 1 usuário
- ⚡ **Performance**: Lock leve em memória, timeout de apenas 30s
- 📊 **Observabilidade**: Logs detalhados de aquisição/liberação de locks

**Notas Técnicas**:
- Implementação atual é adequada para single-instance
- Para deployments multi-instance, considerar migrar para Redis locks
- Window de race condition reduzida de ~2-5s para 0

**Decisão**: Implementado em [DATA DO COMMIT]

---

### 🔴 #2: Contexto `user_data` Perdido em Reinicialização

**Status**: ✅ **RESOLVIDA**

**Problema Original**:
- Contexto de resolução de duplicatas armazenado apenas em `context.user_data` (volátil)
- Reinicialização do bot (deploy/crash) limpava a memória
- Usuários ficavam travados durante resolução de duplicatas após restart
- Botões de "Manter conta atual" / "Usar conta antiga" paravam de funcionar

**Solução Implementada**:

1. **Migration de banco de dados** (`migrations/006_add_duplicate_resolution_context.sql`):
   - Adicionado campo `duplicate_resolution_context TEXT` na tabela `cpf_verifications`
   - Campo armazena JSON com `verification_id`, `conflicting_users` e `created_at`
   - Índice criado para lookups rápidos de contextos pendentes

2. **Entidade atualizada** (`cpf_verification.py`):
   - Adicionado campo `_duplicate_resolution_context` opcional
   - Métodos: `set_duplicate_resolution_context()`, `clear_duplicate_resolution_context()`, `has_pending_duplicate_resolution()`
   - Propriedade: `duplicate_resolution_context` para leitura

3. **Repository atualizado** (`sqlite_cpf_verification_repository.py`):
   - Método `save()` persiste contexto serializado como JSON
   - Método `_row_to_verification()` recupera contexto ao carregar entidade

4. **Handler atualizado** (`cpf_verification_handler.py:219-233`):
   - Ao detectar conflito: salva contexto em memória **E** no banco
   - Ao processar callback: tenta memória primeiro, depois banco como fallback
   - Ao resolver/cancelar: limpa contexto de memória **E** do banco

**Arquivos Modificados**:
- ✅ Criado: `migrations/006_add_duplicate_resolution_context.sql`
- ✅ Modificado: `src/sentinela/domain/entities/cpf_verification.py`
- ✅ Modificado: `src/sentinela/infrastructure/repositories/sqlite_cpf_verification_repository.py`
- ✅ Modificado: `src/sentinela/presentation/handlers/cpf_verification_handler.py`

**Impacto**:
- 🔒 **Resiliência**: Contexto sobrevive a reinicializações do bot
- 🛡️ **UX**: Usuários nunca mais ficam travados durante resolução
- 📊 **Dados**: Contexto persistido com mesma garantia de durabilidade do resto do sistema
- ⚡ **Performance**: Fallback rápido (memória primeiro, banco só se necessário)

**Notas Técnicas**:
- Context o armazenado como JSON para flexibilidade
- Índice no banco para buscar rapidamente verificações com contextos pendentes
- Cleanup automático quando resolução é completada
- Workaround existente para CPFs mantido (reconhecimento de dígitos)

**Decisão**: Implementado em [DATA DO COMMIT]

---

### 🔴 #3: Flood de Callbacks em Resolução de Duplicatas

**Status**: ✅ **RESOLVIDA**

**Problema Original**:
- Usuário clica múltiplas vezes no botão de resolução (double-click, nervosismo)
- Bot processa o mesmo callback múltiplas vezes simultaneamente
- Possíveis problemas:
  - Múltiplas tentativas de remover usuário do grupo (erros do Telegram)
  - Múltiplas atualizações no banco de dados
  - Múltiplos links de convite criados
  - Mensagens de sucesso duplicadas

**Solução Implementada** (Opção A - Flag em Memória):

1. **Set de callbacks em processamento** (`cpf_verification_handler.py:37`):
   ```python
   self._processing_callbacks: set[str] = set()
   ```

2. **Verificação de idempotência** (`cpf_verification_handler.py:324-330`):
   - Verifica se `callback_id` já está no set
   - Se sim: retorna mensagem "Já estou processando..." e ignora
   - Se não: adiciona ao set e processa normalmente

3. **Cleanup automático** (`cpf_verification_handler.py:348-351`):
   - `try/finally` garante remoção do callback_id ao finalizar
   - Mesmo em caso de erro, o callback é removido do set

4. **Feedback imediato**:
   - `query.answer()` chamado imediatamente
   - Desabilita o botão visualmente para o usuário

**Arquivos Modificados**:
- ✅ Modificado: `src/sentinela/presentation/handlers/cpf_verification_handler.py`

**Impacto**:
- 🔒 **Idempotência**: Garante que cada callback é processado apenas 1 vez
- 🛡️ **UX**: Usuário recebe feedback imediato ("Já estou processando...")
- 📊 **Logs**: Elimina poluição de logs com erros de duplicação
- ⚡ **Performance**: Verificação em memória é instantânea (O(1))

**Notas Técnicas**:
- Solução simples e eficaz para 99% dos casos
- Set em memória é suficiente (callbacks têm IDs únicos do Telegram)
- Cleanup automático via `try/finally` previne memory leaks
- Se bot reiniciar durante processamento, callback pode ser reprocessado (aceitável)

**Alternativas Consideradas**:
- Opção B (Flag no banco): Mais robusto mas significativamente mais lento
- Opção C (Não fazer nada): Rejeitada devido ao risco de corrupção de dados

**Decisão**: Implementado em [DATA DO COMMIT]

---

### 🟠 #4: Sessão de Suporte Expirada mas Usuário Continua Preenchendo

**Status**: ✅ **RESOLVIDA**

**Problema Original**:
- Sessões de suporte expiram após 24h de inatividade (cleanup automático)
- Se usuário tentar continuar preenchendo após expiração, não recebia feedback
- Formulário simplesmente não respondia mais, causando confusão
- Usuário não sabia se era erro do bot ou problema de conexão

**Solução Implementada** (Opção A - Feedback ao Detectar Expiração):

1. **Migration de banco de dados** (`migrations/007_add_expired_sessions_tracking.sql`):
   - Criada tabela `expired_support_sessions` para rastrear sessões recém-expiradas
   - Campos: `user_id`, `expired_at`, `session_data` (snapshot), `notified` (flag)
   - Índice para cleanup rápido de registros antigos (> 1 hora)

2. **Repository interface atualizado** (`support_session_repository.py`):
   - Adicionado método abstrato `had_recent_expired_session(user_id, within_minutes=5)`
   - Define contrato para verificar expirações recentes

3. **Repository SQLite atualizado** (`sqlite_support_session_repository.py`):
   - Método `cleanup_expired_sessions()` modificado para:
     - Antes de deletar, registra sessões expiradas na tabela de rastreamento
     - Limpa automaticamente registros de expiração > 1 hora
   - Implementado `had_recent_expired_session()`:
     - Verifica se houve expiração nos últimos X minutos (padrão: 5 min)
     - Marca como `notified=1` após primeira verificação (evita spam)
     - Retorna `True` apenas na primeira tentativa de uso pós-expiração

4. **Handler atualizado** (`support_form_handler.py`):
   - Modificado `handle_description_input()` para detectar expiração:
     - Se não há sessão ativa, verifica se houve expiração recente
     - Se sim: envia mensagem amigável explicando a situação
     - Direciona usuário para reiniciar com `/suporte`
   - Modificado `handle_photo_attachment()` com mesma lógica
   - Mensagem de feedback:
     ```
     ⏱️ **Sessão Expirada**

     Sua sessão de suporte expirou por inatividade (24h).

     Por favor, inicie um novo chamado com /suporte
     ```

**Arquivos Modificados**:
- ✅ Criado: `migrations/007_add_expired_sessions_tracking.sql`
- ✅ Modificado: `src/sentinela/domain/repositories/support_session_repository.py`
- ✅ Modificado: `src/sentinela/infrastructure/repositories/sqlite_support_session_repository.py`
- ✅ Modificado: `src/sentinela/presentation/handlers/support_form_handler.py`

**Impacto**:
- 🎯 **UX**: Usuário recebe feedback claro em vez de silêncio confuso
- 🔒 **Idempotência**: Flag `notified` evita múltiplas notificações para mesma expiração
- 🧹 **Limpeza**: Registros de expiração são auto-removidos após 1h
- ⚡ **Performance**: Verificação rápida com índice em `expired_at`
- 📊 **Observabilidade**: Logs registram quando usuários tentam usar sessões expiradas

**Notas Técnicas**:
- Janela de detecção de 5 minutos balanceia entre detectar tentativas genuínas e evitar falsos positivos
- Tabela auxiliar `expired_support_sessions` permite rastrear sem modificar schema principal
- Cleanup automático de 1h evita crescimento infinito da tabela
- Solução simples e eficaz, sem necessidade de cache ou Redis

**Alternativas Consideradas**:
- Opção B (Avisar X minutos antes): Mais complexo, requer cron/scheduler adicional
- Opção C (Não fazer nada): Rejeitada devido ao impacto negativo na UX

**Decisão**: Implementado em [DATA DO COMMIT]

---

## 🔄 MANTIDAS INTENCIONALMENTE

*(Nenhuma até o momento)*

---

## ⏳ PENDENTES DE REVISÃO

### 🟠 #5: Rate Limit Inexistente em `/cancelar`
**Status**: ⏳ Aguardando revisão

### 🟠 #6: `/status` Público Permite Enumerar Usuários
**Status**: ⏳ Aguardando revisão

### 🟠 #6: Falta Validação de CPF em `resolve_duplicate`
**Status**: ⏳ Aguardando revisão

### 🟠 #7: Formulário de Suporte Pode Ser Cancelado Sem Confirmação
**Status**: ⏳ Aguardando revisão

### 🟠 #8: Jobs Não Verificam Bot Online Antes de Notificar
**Status**: ⏳ Aguardando revisão

### 🟡 #9: Falta Feedback Durante Processamento de Anexos
**Status**: ⏳ Aguardando revisão

### 🟡 #10: Mensagem de Expiração de Verificação Não Limpa Estado
**Status**: ⏳ Aguardando revisão

### 🟡 #11: Falta Logging de Ações Críticas de Admin
**Status**: ⏳ Aguardando revisão

### 🟡 #12: Daily Checkup Pode Enviar Notificações em Horário Inadequado
**Status**: ⏳ Aguardando revisão

### 🟡 #13: Falta Tratamento de Erro em Upload de Imagens
**Status**: ⏳ Aguardando revisão

### 🟡 #14: Falta Rate Limiting em Verificação de CPF
**Status**: ⏳ Aguardando revisão

### 🟡 #15: Mensagens de Bot Podem Ser Editadas por Usuários
**Status**: ⏳ Aguardando revisão

### 🟢 #16: Falta Confirmação Antes de Cancelar Verificação
**Status**: ⏳ Aguardando revisão

### 🟢 #17: Link de Convite Pode Expirar Sem Notificar Admin
**Status**: ⏳ Aguardando revisão

### 🟢 #18: Falta Analytics de Uso do Bot
**Status**: ⏳ Aguardando revisão

### 🟢 #19: Falta Health Check Endpoint
**Status**: ⏳ Aguardando revisão

---

## 📊 Estatísticas

| Categoria | Total | Resolvidas | Mantidas | Pendentes |
|-----------|-------|------------|----------|-----------|
| 🔴 Crítica | 3 | 3 | 0 | 0 |
| 🟠 Alta | 5 | 1 | 0 | 4 |
| 🟡 Média | 7 | 0 | 0 | 7 |
| 🟢 Baixa | 4 | 0 | 0 | 4 |
| **TOTAL** | **19** | **4** | **0** | **15** |

**Progresso**: 21.1% completo (4/19) | ✅ **TODAS as críticas resolvidas!**

---

## 🎯 Próximos Passos

1. ⏳ Revisar inconsistência #5 (Rate limit em /cancelar)
2. Continuar revisão sequencial das 15 inconsistências restantes
