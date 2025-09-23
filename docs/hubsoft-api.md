# API HubSoft - Consulta de Clientes

## Visão Geral

A API de integração do HubSoft permite consultar dados de clientes e seus serviços através de endpoints REST. Esta documentação cobre especificamente o endpoint de consulta de clientes.

## Endpoint Principal

### GET - Consultar Clientes

```
GET /api/v1/integracao/cliente
```

Consulta dados dos clientes e retorna um JSON como resposta.

## Headers

| Header | Valor | Obrigatório |
|--------|-------|-------------|
| Authorization | Bearer {token} | Sim |

## Parâmetros

### Parâmetros Obrigatórios

| Parâmetro | Descrição | Valores Aceitos |
|-----------|-----------|-----------------|
| `busca` | Tipo de busca que deseja fazer no cliente | `nome_razaosocial`, `nome_fantasia`, `cpf_cnpj`, `codigo_cliente`, `telefone`, `login_radius`, `ipv4`, `mac`, `id_cliente_servico`, `uuid_cliente`, `uuid_cliente_servico`, `id_prospecto`, `id_externo`, `referencia_alias`, `id_porta_atendimento`, `id_caixa_optica`, `observacoes_autenticacao`, `id_servico` |
| `termo_busca` | Termo utilizado para fazer a busca | Campo livre (Qualquer valor será aceito) |

### Parâmetros Opcionais

| Parâmetro | Descrição | Valores Aceitos | Valor Padrão |
|-----------|-----------|-----------------|--------------|
| `inativo` | Buscar clientes com cadastro inativo | `sim`, `nao`, `todos` | `nao` |
| `limit` | Limite de resultados | 1 a 100 | 5 |
| `cancelado` | Incluir serviços cancelados | `sim`, `nao` | `nao` |
| `ultima_conexao` | Incluir dados da última conexão | `sim`, `nao` | `nao` |
| `incluir_alarmes` | Incluir alarmes de conexão do serviço | `sim`, `nao` | `nao` |
| `incluir_contrato` | Incluir contratos do serviço | `sim`, `nao` | `nao` |
| `incluir_stfc` | Incluir dados STFC vinculados ao serviço | `sim`, `nao` | `nao` |
| `incluir_mvno` | Incluir dados MVNO vinculados ao serviço | `sim`, `nao` | `nao` |
| `incluir_anexos` | Incluir anexos vinculados ao cliente | `sim`, `nao` | `nao` |
| `incluir_desbloqueios` | Incluir desbloqueios em confiança | `sim`, `nao` | `nao` |
| `order_by` | Campo para ordenação | `data_cadastro`, `data_fechamento` | `data_cadastro` |
| `order_type` | Tipo de ordenação | `asc`, `desc` | `asc` |

### Parâmetros de Filtro Avançados

| Parâmetro | Descrição | Valores Aceitos |
|-----------|-----------|-----------------|
| `servico_status` | Filtrar clientes por status do plano | `agendado_para_instalacao`, `aguardando_assinatura_contrato`, `aguardando_configuracao`, `aguardando_instalacao`, `aguardando_liberacao_ti`, `aguardando_migracao`, `cancelado`, `franquia_excedida`, `inativo`, `servico_habilitado`, `suspenso_debito`, `suspenso_parcialmente`, `suspenso_pedido_cliente` |
| `cancelado_mas_possui_fatura_em_aberto_desde` | Filtrar cancelados com faturas em aberto | Formato DateTime (YYYY-MM-DD) |

### Parâmetros de Paginação

| Parâmetro | Descrição | Valores Aceitos | Valor Padrão |
|-----------|-----------|-----------------|--------------|
| `pagina` | Número da página da consulta | Valor numérico ≥ 1 | 1 (se > 1000 registros) |
| `itens_por_pagina` | Quantidade de registros por página | 1 a 500 | 200 (se > 1000 registros) |

## Exemplos de Uso

### Buscar por CPF
```
GET /api/v1/integracao/cliente?busca=cpf_cnpj&termo_busca=12345678901&limit=10
```

### Buscar clientes com serviços ativos
```
GET /api/v1/integracao/cliente?busca=nome_razaosocial&termo_busca=João&servico_status=servico_habilitado
```

### Buscar com dados de última conexão
```
GET /api/v1/integracao/cliente?busca=login_radius&termo_busca=usuario123&ultima_conexao=sim
```

### Múltiplos status de serviço
```
GET /api/v1/integracao/cliente?busca=cpf_cnpj&termo_busca=12345678901&servico_status=servico_habilitado,suspenso_debito
```

## Notas Importantes

### 🔍 Última Conexão
Para obter dados da última autenticação, é necessário enviar `ultima_conexao=sim`. Esta informação utiliza como base o extrato de conexão do RADIUS e pode não ser 100% confiável caso existam problemas na rede do provedor.

### 🗺️ Coordenadas Geográficas
Para que o HubSoft retorne dados de coordenadas do endereço, é necessário configurar as credenciais de integração com o Google Maps API. O sistema verifica apenas endereços de instalação para atualização de coordenadas.

### 🚨 Sistema de Alertas
O provedor pode cadastrar alertas que serão retornados pelos atributos `alerta` e `alerta_mensagens`. Estes alertas podem ser utilizados para:
- Envio de mensagens automáticas via BOT
- Áudios customizados no PBX
- Exibição diferenciada no mapa
- Outras integrações criativas

### 📊 Filtro por Faturas em Aberto
O parâmetro `cancelado_mas_possui_fatura_em_aberto_desde`:
- Filtra apenas serviços cancelados com faturas em aberto
- Requer que `cancelado=sim` seja definido
- Data deve estar no formato YYYY-MM-DD

### 📄 Paginação Automática
Quando um cliente possui mais de 1000 serviços, o sistema aplica paginação automaticamente para evitar lentidão. Use os parâmetros `pagina` e `itens_por_pagina` para navegar entre as páginas.

## Códigos de Resposta

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso - Retorna dados dos clientes |
| 401 | Não autorizado - Token inválido |
| 400 | Parâmetros inválidos |
| 500 | Erro interno do servidor |

## Estrutura de Resposta

A API retorna um array JSON contendo os dados dos clientes encontrados. Cada cliente pode conter informações como:
- Dados pessoais (nome, CPF/CNPJ, telefone, etc.)
- Serviços contratados
- Status dos serviços
- Dados de conexão (se solicitado)
- Contratos (se solicitado)
- Alarmes (se solicitado)
- Anexos (se solicitado)