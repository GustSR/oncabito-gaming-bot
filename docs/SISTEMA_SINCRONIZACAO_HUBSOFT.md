# Sistema de Sincronização HubSoft

Este documento descreve o sistema completo de sincronização implementado para manter a consistência entre os dados locais e o HubSoft, incluindo fallback offline e recovery automático.

## 📋 Visão Geral

O sistema foi desenvolvido para resolver os seguintes problemas:
- **Falta de sincronização** entre status local e HubSoft
- **Protocolos desvinculados** de tickets criados offline
- **Inconsistência de estado** entre sistemas
- **Ausência de recovery** quando HubSoft volta online

## 🏗️ Arquitetura

### Componentes Principais

1. **HubSoftSyncService** (`src/sentinela/services/hubsoft_sync_service.py`)
   - Gerencia sincronização bidirecional
   - Health check do HubSoft
   - Sincronização de tickets offline
   - Atualização de status de tickets ativos

2. **HubSoftMonitorService** (`src/sentinela/services/hubsoft_monitor_service.py`)
   - Monitoramento contínuo em background
   - Detecção automática de mudanças de status
   - Recovery automático quando HubSoft volta online
   - Notificações para administradores

3. **Banco de Dados Atualizado** (`src/sentinela/clients/db_client.py`)
   - Novos campos de sincronização
   - Funções para gerenciar tickets offline
   - Estatísticas de sincronização

4. **Comando /status Melhorado** (`src/sentinela/bot/handlers.py`)
   - Sincronização automática antes de exibir dados
   - Indicadores visuais de status de sincronização
   - Informações detalhadas sobre conectividade

## 🔄 Fluxos de Sincronização

### 1. Criação de Tickets

#### Cenário Online (HubSoft disponível):
```
Usuário cria ticket → Cria no HubSoft → Salva localmente com ID HubSoft
```

#### Cenário Offline (HubSoft indisponível):
```
Usuário cria ticket → Salva apenas localmente → Protocolo LOC######
```

### 2. Recovery Automático

Quando HubSoft volta online:
```
Monitor detecta → Busca tickets offline → Cria no HubSoft → Atualiza dados locais → Mapeia protocolos
```

### 3. Sincronização de Status

#### Automática (a cada 15 minutos quando online):
```
Monitor executa → Busca status no HubSoft → Atualiza dados locais
```

#### Manual (comando /status):
```
Usuário consulta → Health check → Sincronização → Exibição atualizada
```

## 🗃️ Estrutura do Banco de Dados

### Novos Campos na Tabela `support_tickets`:

- `hubsoft_protocol`: Protocolo oficial do HubSoft
- `sync_status`: Status da sincronização ('pending', 'synced', 'failed')
- `synced_at`: Timestamp da última sincronização bem-sucedida
- `last_sync_attempt`: Timestamp da última tentativa de sincronização
- `sync_error`: Mensagem de erro da sincronização (se houver)

## 🖥️ Comandos Administrativos

### `/sync_tickets [tipo]`
Força sincronização manual de tickets.

**Argumentos:**
- `offline`: Sincroniza apenas tickets offline
- `status`: Atualiza apenas status de tickets ativos
- `all` (padrão): Executa sincronização completa

**Exemplo:**
```
/sync_tickets offline
```

### `/health_hubsoft`
Verifica status detalhado da integração HubSoft.

**Informações fornecidas:**
- Status de conectividade
- Estatísticas de sincronização
- Última verificação
- Ações recomendadas

### `/status` (Melhorado)
Comando do usuário com sincronização automática.

**Melhorias:**
- Health check automático antes da consulta
- Sincronização de status em tempo real
- Indicadores visuais de conectividade
- Informações sobre última sincronização

## 🔍 Monitoramento

### Verificações Automáticas

- **Health Check**: A cada 5 minutos
- **Sincronização de Status**: A cada 15 minutos (quando online)
- **Recovery de Tickets**: A cada 30 minutos (quando online)

### Notificações para Administradores

#### Mudança de Status:
- HubSoft Online → Offline
- HubSoft Offline → Online

#### Recovery Bem-sucedido:
- Número de tickets sincronizados
- Falhas encontradas (se houver)

## 🚀 Processo de Recovery

### Detecção de Volta Online
```
Monitor → Health Check → Status mudou para Online → Trigger Recovery
```

### Sincronização de Tickets Offline
1. Busca todos os tickets sem `hubsoft_atendimento_id`
2. Para cada ticket:
   - Reconstrói dados do formulário
   - Cria atendimento no HubSoft
   - Atualiza dados locais
   - Mapeia protocolo local → protocolo HubSoft
   - Adiciona contexto histórico no HubSoft

### Vínculo de Protocolos
- **Local**: `LOC000123` (ticket criado offline)
- **HubSoft**: `#HUB456789` (protocolo oficial após sincronização)
- **Mapeamento**: Ticket mantém ambos os protocolos para referência

## 📊 Indicadores de Status

### No Comando /status:

#### Sistema Online:
- 🟢 Indicador verde
- "Sincronizado"
- Hora da última sincronização
- Status em tempo real

#### Sistema Offline:
- 🔄 Indicador de sincronização pendente
- "Sincronização Pendente"
- Avisos sobre dados locais
- Garantia de que nada será perdido

#### Por Ticket:
- 🟢 Ticket sincronizado
- 🔄 Aguardando sincronização
- Tooltip com hora da última sincronização

## ⚙️ Configuração

### Variáveis de Ambiente

- `HUBSOFT_ENABLED`: Habilita/desabilita integração HubSoft
- `ADMIN_USER_IDS`: Lista de IDs de administradores para notificações

### Intervalos Configuráveis

No `HubSoftMonitorService`:
- `_monitor_interval`: Intervalo principal (padrão: 5 minutos)
- `_quick_check_interval`: Verificações rápidas (padrão: 1 minuto)

## 🔧 Manutenção

### Logs Importantes

- Health checks (a cada 30 minutos)
- Mudanças de status do HubSoft
- Início/fim de processos de recovery
- Estatísticas de sincronização

### Monitoramento Manual

Use `/health_hubsoft` para verificar:
- Status atual da conectividade
- Número de tickets pendentes de sincronização
- Última sincronização bem-sucedida
- Ações recomendadas

## 🛡️ Garantias do Sistema

### Alta Disponibilidade
- ✅ Sistema funciona mesmo com HubSoft offline
- ✅ Nenhum ticket é perdido
- ✅ Recovery automático quando volta online

### Consistência de Dados
- ✅ Status sincronizados automaticamente
- ✅ Mapeamento bidirecional de protocolos
- ✅ Histórico preservado no HubSoft

### Experiência do Usuário
- ✅ Indicadores visuais claros
- ✅ Informações sobre status de sincronização
- ✅ Transparência sobre disponibilidade do sistema

## 📈 Benefícios Implementados

1. **Zero Downtime**: Sistema continua funcionando mesmo com HubSoft offline
2. **Sincronização Inteligente**: Recovery automático e transparente
3. **Visibilidade Total**: Administradores têm controle completo do status
4. **Experiência Melhorada**: Usuários sempre sabem o status de seus tickets
5. **Integridade de Dados**: Nenhum ticket é perdido, todos são eventualmente sincronizados

O sistema implementado resolve completamente os problemas identificados, mantendo alta disponibilidade enquanto garante consistência de dados com o HubSoft.