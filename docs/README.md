# 📚 Documentação - OnCabo Gaming Bot

Bem-vindo à documentação do **OnCabo Gaming Bot** - Sistema completo de gerenciamento de comunidade gaming com integração ERP.

> **Última atualização:** 04 de Novembro de 2025
> **Status:** Documentação completa e atualizada ✅

---

## 📖 Índice

### 🚀 Início Rápido
- [Quick Start](./guides/QUICK_START.md) - Guia rápido de início
- [Deploy em Produção](./guides/DEPLOYMENT.md) - Como fazer deploy
- [Deploy Local](./DEPLOY_PRODUCAO_LOCAL.md) - Deploy com git clone + build local

### 🏗️ Arquitetura
- [Visão Geral da Arquitetura](./architecture/OVERVIEW.md) - Clean Architecture + DDD
- [Estrutura do Projeto](./architecture/PROJECT_STRUCTURE.md) - Organização de diretórios
- [Decisões Arquiteturais](./architecture/ARCHITECTURAL_DECISIONS.md) - ADRs do projeto
- [Sistema de Administradores](./architecture/ADMIN_SYSTEM.md) - Sincronização e proteções automáticas

### 🔌 API & Integrações
- [Documentação API HubSoft - Guia de Uso](./api/Documentação%20API%20Hubsoft%20-%20Guia%20de%20Uso.md) - Índice da documentação HubSoft
- [HubSoft API (Focado)](./api/HUBSOFT_API_DOCUMENTATION.md) - Endpoints de Atendimento
- [HubSoft API (Completo)](./api/hubsoft_api_documentation.md) - 175 endpoints completos
- [Collection Postman](./api/hubsoft_collection.json) - Collection para testes

### 📊 Análises & Processos
- [Inconsistências Lógicas](./processes/INCONSISTENCIAS_LOGICA_INTERACOES.md) - Lista de inconsistências identificadas
- [Resoluções de Inconsistências](./processes/INCONSISTENCIAS_RESOLUCOES.md) - Rastreamento de correções (7/19 resolvidas)
- [Mapeamento Completo de Mensagens](./analysis/MAPEAMENTO_COMPLETO_MENSAGENS_INTERACOES.md) - Todas as mensagens do bot
- [Diagramas de Fluxos](./analysis/DIAGRAMAS_FLUXOS_BOT.md) - Diagramas ASCII dos fluxos

### 🔄 Migração
- [Relatório Final de Migração](./migration/FINAL_REPORT.md) - Histórico da migração para Clean Architecture
- [Sumário de Limpeza](./migration/CLEANUP_SUMMARY.md) - Resumo do processo de limpeza

### 📦 Histórico & Arquivo
- [Documentos Arquivados](./archive/) - Análises antigas e documentos históricos
- [Comparação Antes/Depois](./migration/COMPARISON.md) - Mudanças na arquitetura

## 🎯 Para Desenvolvedores

Se você é desenvolvedor e vai trabalhar no projeto:

1. **Arquitetura**: Leia [Visão Geral da Arquitetura](./architecture/OVERVIEW.md)
2. **Estrutura**: Entenda a [Estrutura do Projeto](./architecture/PROJECT_STRUCTURE.md)
3. **Desenvolvimento**: Use `./dev.sh` - veja [Scripts README](../scripts/README.md)
4. **Testes**: Configure ambiente com [Testing Setup](./guides/TESTING_SETUP.md)
5. **Deploy**: Entenda [GitHub Registry Deploy](./guides/GITHUB_REGISTRY_DEPLOY.md)

## 🚀 Para Administradores

Se você vai fazer deploy ou administrar o bot:

1. **Deploy Inicial**: Siga [Deployment Guide](./guides/DEPLOYMENT.md)
2. **Cron Jobs**: Configure com [Deployment README](../deployment/README.md)
3. **Administradores**: Entenda [Sistema de Admins](./architecture/ADMIN_SYSTEM.md)
4. **Manutenção**: Veja ferramentas em [Scripts README](../scripts/README.md)
5. **Monitoramento**: Confira comandos no [README Principal](../README.md)

## 🎮 Para Usuários Finais

Se você é usuário da comunidade gaming:

1. **Comandos**: Veja comandos disponíveis no [README Principal](../README.md)
2. **Comportamento**: Entenda como bot responde em [Mapeamento de Respostas](./MAPEAMENTO_RESPOSTAS_BOT.md)
3. **Suporte**: Use `/suporte` no tópico correto do grupo

## 📊 Status do Projeto

- ✅ **Arquitetura:** Clean Architecture + DDD completa
- ✅ **Migração:** 100% concluída
- ✅ **Automação:** 4 cron jobs configurados (auto-update, checkup, integrity, export)
- ✅ **Administradores:** Sincronização automática a cada 30 min
- ✅ **Documentação:** Completa e atualizada
- 🔄 **Testes:** Em desenvolvimento
- 🚀 **Produção:** Estável e rodando

## ⚙️ Automação Implementada

### Cron Jobs Ativos
- **Auto-Update**: Deploy automático (cada 10 min, 00:00-05:00)
- **Daily Checkup**: Verificações completas (cada 30 min, 6:00-23:59)
  - Sincroniza administradores
  - Detecta CPFs duplicados
  - Verifica contratos cancelados
  - Remove usuários não-verificados
- **Integrity Check**: Verifica saúde do banco (diário às 6:00)
- **Data Export**: Backup incremental JSON (diário às 6:30)

Detalhes: [Deployment README](../deployment/README.md) | [Scripts README](../scripts/README.md)

## 🛡️ Sistema de Proteção

### Administradores
- Detecção automática via Telegram API
- Sincronização a cada 30 minutos
- Proteção contra remoções automáticas
- Histórico mantido no banco de dados

Detalhes: [Admin System](./architecture/ADMIN_SYSTEM.md)

## 🔗 Links Úteis

- [Repositório GitHub](https://github.com/GustSR/oncabito-gaming-bot)
- [Issues](https://github.com/GustSR/oncabito-gaming-bot/issues)
- [GitHub Container Registry](https://github.com/GustSR/oncabito-gaming-bot/pkgs/container/oncabito-gaming-bot)

## 📄 Licença

Este projeto é propriedade da **OnCabo Gaming Community**.

---

**Última atualização:** 04/11/2025
