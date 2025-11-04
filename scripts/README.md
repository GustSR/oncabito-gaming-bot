# 📦 Scripts de Operação e Manutenção

Este diretório contém scripts utilitários para automação, manutenção e diagnóstico do OnCabo Gaming Bot.

## 📂 Estrutura

```
scripts/
├── dev/                    # Ferramentas de desenvolvimento
│   └── dev.sh             # Helper principal de desenvolvimento
│
├── tasks/                 # Tarefas automatizadas (executadas via cron)
│   ├── daily_cpf_checkup.py       # Checkup diário completo (6 fases)
│   ├── verify_data_integrity.py   # Verificação de integridade do banco
│   └── export_critical_data.py    # Export de backup em JSON
│
└── tools/                 # Ferramentas manuais de administração
    └── clear_group_messages.py    # Limpeza de mensagens do grupo
```

## 🔧 Scripts de Desenvolvimento

### `dev/dev.sh` - Helper de Desenvolvimento
**Symlink na raiz**: `./dev.sh`

Script principal para facilitar desenvolvimento local. Gerencia container Docker de desenvolvimento.

**Comandos disponíveis**:
```bash
./dev.sh start      # Inicia bot em modo desenvolvimento
./dev.sh stop       # Para o bot
./dev.sh restart    # Reinicia bot (útil após mudanças no código)
./dev.sh logs       # Mostra logs em tempo real
./dev.sh shell      # Abre shell dentro do container
./dev.sh rebuild    # Rebuild completo (quando muda requirements.txt)
./dev.sh clean      # Remove container e imagem
./dev.sh help       # Mostra ajuda completa
```

**Características**:
- Usa `Dockerfile.dev` otimizado para desenvolvimento
- Hot-reload automático quando muda código
- Volumes montados para edição em tempo real
- Logs coloridos e formatados

---

## ⏰ Scripts de Tarefas Automatizadas

### `tasks/daily_cpf_checkup.py` - Checkup Diário Completo
**Execução**: Automática via cron (cada 30 min, 6:00-23:59)

**6 Fases de Verificação**:
1. **Sincronização de Administradores**
   - Busca admins atuais via `bot.get_chat_administrators()`
   - Atualiza tabela `administrators` no banco
   - Marca admins removidos como inativos

2. **Conflitos de CPF Expirados**
   - Processa conflitos de CPF duplicado com timeout de 24h
   - Remove usuários que não resolveram conflito no prazo

3. **Detecção de CPFs Duplicados**
   - Varre todos os usuários ativos
   - Identifica CPFs usados por múltiplos usuários
   - Cria registros de conflito para resolução

4. **Verificações Expiradas**
   - Remove verificações de CPF não completadas
   - Libera slots para novas verificações

5. **Contratos Cancelados**
   - Consulta HubSoft API para status de contratos
   - Remove usuários com contratos cancelados
   - **Protege administradores** de remoção automática

6. **Usuários Não-Verificados**
   - Remove usuários que não completaram verificação em 24h
   - **Protege administradores** de remoção

**Execução manual**:
```bash
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/daily_cpf_checkup.py
```

**Logs**: `logs/checkup.log`

---

### `tasks/verify_data_integrity.py` - Verificação de Integridade
**Execução**: Automática via cron (diário às 6:00 AM)

**O que verifica**:
- Integridade do banco SQLite (`PRAGMA integrity_check`)
- Usuários órfãos (sem dados relacionados)
- Verificações órfãs (sem usuário correspondente)
- Perda de dados críticos (alerta se > 5%)
- Inconsistências entre tabelas relacionadas

**Execução manual**:
```bash
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/verify_data_integrity.py
```

**Logs**: `logs/integrity.log`

---

### `tasks/export_critical_data.py` - Export de Dados
**Execução**: Automática via cron (diário às 6:30 AM)

**O que exporta**:
- Todos os usuários ativos e banidos
- Verificações de CPF (todas com status)
- Tickets de suporte abertos e fechados
- Formato JSON com timestamp
- Backup incremental

**Execução manual**:
```bash
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/export_critical_data.py
```

**Logs**: `logs/export.log`

---

## 🛠️ Scripts de Ferramentas Manuais

### `tools/clear_group_messages.py` - Limpeza de Mensagens
**Uso**: Manual (quando necessário limpar histórico do grupo)

**⚠️ ATENÇÃO**: Deleção é IRREVERSÍVEL! Use com extremo cuidado.

**O que faz**:
- Deleta todas as mensagens do grupo Telegram
- **Preserva mensagens fixadas automaticamente**
- Suporta modo dry-run para simulação segura
- Rate limiting para respeitar API do Telegram

**Uso recomendado**:
```bash
# 1. SEMPRE teste primeiro em dry-run
docker exec oncabo-gaming-bot python3 /app/scripts/tools/clear_group_messages.py \
    --dry-run --limit 100

# 2. Revise o output para confirmar que mensagens fixadas serão preservadas

# 3. Execute com limite menor para teste real
docker exec oncabo-gaming-bot python3 /app/scripts/tools/clear_group_messages.py \
    --confirm --limit 50

# 4. Se tudo ok, execute para limpar todas
docker exec oncabo-gaming-bot python3 /app/scripts/tools/clear_group_messages.py \
    --confirm
```

**Opções**:
- `--dry-run`: Modo simulação (não deleta nada)
- `--limit N`: Limita quantas mensagens processar (padrão: 1000)
- `--confirm`: Confirma deleção sem prompt interativo (necessário para docker exec)

**Exemplo de output**:
```
============================================================
🧹 LIMPEZA DE MENSAGENS DO GRUPO
============================================================
📅 Data/Hora: 03/11/2025 18:39:04
🆔 Group ID: -1002966479273
🔍 Modo: DRY RUN (simulação)
📊 Limite: 100 mensagens
============================================================

✅ Grupo encontrado: ONCABO Gamer | Comunidade & Suporte
📌 Mensagem fixada encontrada: ID 35

============================================================
📊 RESULTADO FINAL
============================================================
✅ Mensagens deletadas: 100
📌 Mensagens fixadas puladas: 1
⚠️  Erros/não encontradas: 0

⚠️  MODO DRY-RUN: Nenhuma mensagem foi realmente deletada
💡 Execute sem --dry-run para deletar de verdade
============================================================
```

---

## 📚 Referências

**Deploy e Automação**:
- Scripts de deploy: `../deployment/` (auto-update, setup-cron, etc)
- Configuração de cron jobs: `../deployment/setup-cron.sh`

**Desenvolvimento**:
- Helper principal: `./dev.sh` (symlink de `dev/dev.sh`)
- Docker Compose: `../docker-compose.yml`
- Dockerfile dev: `../Dockerfile.dev`

**Documentação**:
- README principal: `../README.md`
- Deployment: `../deployment/README.md`
- Arquitetura: `../docs/architecture/`
