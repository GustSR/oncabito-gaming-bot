# 📋 Documentação da API HubSoft - Sistema de Atendimento

**Última atualização:** 25/09/2025
**Status:** Em construção - aguardando documentação completa

---

## 📖 **ÍNDICE**
- [Autenticação](#autenticacao)
- [Endpoints de Atendimento](#endpoints-atendimento)
- [Endpoints de Ordem de Serviço](#endpoints-ordem-servico)
- [Estruturas de Dados](#estruturas-dados)
- [Códigos de Erro](#codigos-erro)
- [Exemplos de Uso](#exemplos-uso)

---

## 🔐 **AUTENTICAÇÃO** {#autenticacao}

*Aguardando documentação...*

---

## 📞 **ENDPOINTS DE ATENDIMENTO** {#endpoints-atendimento}

### 🔍 **Consulta de Atendimentos (GET/POST)**

**Endpoint:** `/api/v1/integracao/atendimento/paginado/:quantidade`

#### **📋 Requisitos**
- ✅ **Access Token** necessário (obtido via OAuth)
- ✅ **Autenticação** via Bearer Token

#### **🎯 Método GET**
```http
GET /api/v1/integracao/atendimento/paginado/:quantidade?pagina=1&data_inicio=2022-08-01&data_fim=2022-08-31
```

#### **🎯 Método POST**
```http
POST /api/v1/integracao/atendimento/paginado/:quantidade
```

#### **📊 Parâmetros**

| Atributo | Descrição | Obrigatório | Valor Default |
|----------|-----------|-------------|---------------|
| `data_inicio` | Data de Cadastro Inicial (YYYY-MM-DD) | ✅ Sim | Nenhum |
| `data_fim` | Data de Cadastro Final (YYYY-MM-DD) | ✅ Sim | Nenhum |

**⚠️ Observações:**
- `data_fim` deve ser maior ou igual a `data_inicio`
- Formato DateTime: `YYYY-MM-DD`

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
```

#### **📝 Query Parameters**
| Parâmetro | Valor | Descrição |
|-----------|--------|-----------|
| `pagina` | `1` | Página que está sendo consultada |
| `data_inicio` | `2022-08-01` | Data de Início no formato YYYY-MM-DD |
| `data_fim` | `2022-08-31` | Data Final no formato YYYY-MM-DD |

#### **🛤️ Path Variables**
| Variável | Valor | Descrição |
|----------|--------|-----------|
| `quantidade` | `10` | Quantidade de Itens por Página |

#### **📋 Parâmetros Adicionais (POST)**

| Atributo | Descrição | Valor Default | Obrigatório |
|----------|-----------|---------------|-------------|
| `pagina` | Número da página (primeira página = 0) | Nenhum | ✅ Sim |
| `itens_por_pagina` | Total de itens por página (Min: 1, Max: 500) | Nenhum | ✅ Sim |
| `data_inicio` | Valor no formato DateTime (YYYY-MM-DD) | Nenhum | ❌ Opcional |
| `data_fim` | Valor no formato DateTime (YYYY-MM-DD) | Nenhum | ❌ Opcional |
| `tipo_atendimento` | IDs do Tipo de Atendimento (string) | Nenhum | ❌ Opcional |
| `status_atendimento` | IDs do Status Atendimento (string) | Nenhum | ❌ Opcional |
| `id_servico` | IDs dos Serviços (numeric) | Nenhum | ❌ Opcional |
| `relacoes` | Relações a incluir na resposta | Nenhum | ❌ Opcional |

#### **🔗 Relações Disponíveis**
```
cliente_servico,usuarios_responsaveis,atendimento_mensagem,checklists
```

#### **⚠️ Observações Importantes**
- 📊 **Volume de dados:** Esta requisição pode retornar um volume muito grande de dados
- ⚡ **Performance:** Use relações com cautela - mais relações = maior tempo de resposta
- 🔢 **Múltiplos valores:** `tipo_atendimento` e `status_atendimento` aceitam múltiplos valores separados por vírgula
  - Exemplo: `"132,28"` para múltiplos tipos de atendimento
- 📅 **Datas:** `data_fim` deve ser maior ou igual a `data_inicio`
- 📄 **Paginação:** A primeira página é `0` (não `1`)

#### **📝 Parâmetros Detalhados (POST)**

**Headers:**
```http
Authorization: Bearer {access_token}
```

**Body Parameters:**
```json
{
  "pagina": 0,
  "itens_por_pagina": 50,
  "data_inicio": "2022-08-01",
  "data_fim": "2022-08-31",
  "tipo_atendimento": "132,28",
  "status_atendimento": "1,2,3",
  "id_servico": 1234,
  "relacoes": "cliente_servico,usuarios_responsaveis"
}
```

#### **💡 Exemplos de Requisição**

**GET:**
```http
GET /api/v1/integracao/atendimento/paginado/10?pagina=1&data_inicio=2022-08-01&data_fim=2022-08-31
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

**POST:**
```http
POST /api/v1/integracao/atendimento/paginado/50
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "pagina": 0,
  "itens_por_pagina": 50,
  "data_inicio": "2022-08-01",
  "data_fim": "2022-08-31",
  "relacoes": "cliente_servico,usuarios_responsaveis"
}
```

#### **📤 Exemplo de Resposta**

**Resposta de Sucesso:**
```json
{
  "status": "success",
  "msg": "Dados consultados com sucesso",
  "paginacao": {
    "primeira_pagina": 0,
    "ultima_pagina": 38,
    "pagina_atual": 0,
    "total_registros": 39
  },
  "atendimentos": [
    {
      "id_atendimento": 5448,
      "id_atendimento_status": 23,
      "id_tipo_atendimento": 125,
      "id_cliente_servico": 17812,
      "id_usuario_responsavel": null,
      "id_usuario_abertura": 4903,
      "protocolo": "20221229180833379797",
      "data_cadastro": "2022-12-29 18:08:33",
      "data_fechamento": null,
      "rascunho": false,
      "status_fechamento": null,
      "descricao_fechamento": null,
      "id_motivo_fechamento_atendimento": null,
      "deleted_at": null,
      "avaliacao": null,
      "comentario_avaliacao": null,
      "ordem_servico_count": 0,
      "ordem_servico_fechada": 0,
      "ordem_servico_aberta": 0,
      "ingressado": false,
      "data_cadastro_br": "29/12/2022 18:08",
      "data_cadastro_timestamp": 1672348113000,
      "data_fechamento_br": null,
      "data_fechamento_timestamp": null,
      "minutos_em_aberto": 61486,
      "tempo_restante": "-1023h 46min",
      "percentual_tempo_restante": 0,
      "percentual_color_class": "white-fg md-red-bg",
      "status": {
        "id_atendimento_status": 23,
        "prefixo": "aguardando_analise",
        "descricao": "Aguardando Análise",
        "cor": "md-deep-orange-A700-bg",
        "abrir_ordem_servico": false,
        "display": "Aguardando Análise"
      },
      "tipo_atendimento": {
        "id_tipo_atendimento": 125,
        "descricao": "COMERCIAL",
        "checklists": []
      },
      "cliente_servico": {
        "id_cliente_servico": 17812,
        "id_cliente": 24930,
        "id_servico": 2735,
        "numero_plano": 6,
        "display": "(6) (MIGRACAO-TESTEMAP) COMBO 10 MEGA - RÁDIO",
        "endereco_numero_completo": "RUA PADRE PAULO, 308 - MAE CHIQUINHA, SANTO ANTÔNIO DO MONTE/MG | CEP: 35560-000",
        "endereco_instalacao": {
          "id_cliente_servico_endereco": 73553,
          "id_endereco_numero": 52635,
          "id_cliente_servico": 17812,
          "tipo": "instalacao",
          "endereco_numero": {
            "id_endereco_numero": 52635,
            "numero": "308",
            "complemento": null,
            "coordenadas": {
              "type": "Point",
              "coordinates": [-45.292858, -20.092926]
            },
            "ativo": true,
            "id_cidade": 7674,
            "bairro": "MAE CHIQUINHA",
            "referencia": null,
            "endereco": "RUA PADRE PAULO",
            "cep": "35560000",
            "atualizar_coords_auto": false,
            "id_condominio": null,
            "cidade": {
              "id_cidade": 7674,
              "id_estado": 65,
              "nome": "Santo Antônio do Monte",
              "estado": {
                "id_estado": 65,
                "sigla": "MG"
              }
            }
          }
        },
        "servico": {
          "id_servico": 2735,
          "descricao": "(Migracao-TesteMap) COMBO 10 MEGA - RÁDIO",
          "id_servico_grupo": 51,
          "servico_grupo": {
            "id_servico_grupo": 51,
            "descricao": "GRUPO DE TESTE",
            "data_cadastro": "2020-04-15 13:52:01",
            "ativo": true
          }
        },
        "cliente": {
          "id_cliente": 24930,
          "ativo": true,
          "codigo_cliente": 1864,
          "nome_razaosocial": "LAVYNIA",
          "display": "(1864) LAVYNIA"
        }
      },
      "usuarios_responsaveis": [],
      "atendimento_mensagem": [
        {
          "id_atendimento_mensagem": 376,
          "id_atendimento": 5448,
          "mensagem": "TESTE",
          "data_cadastro_br": "10/02/2023 10:55",
          "data_cadastro_timestamp": 1676037311000
        },
        {
          "id_atendimento_mensagem": 375,
          "id_atendimento": 5448,
          "mensagem": "TESTE",
          "data_cadastro_br": "10/02/2023 10:55",
          "data_cadastro_timestamp": 1676037311000
        }
      ]
    }
  ]
}
```

### 🔍 **Consulta de Todos os Atendimentos (GET)**

**Endpoint:** `/api/v1/integracao/atendimento/todos`

#### **📋 Descrição**
Consulta todos os atendimentos com paginação avançada e múltiplos filtros.

#### **🎯 Método**
```http
GET /api/v1/integracao/atendimento/todos
```

#### **📊 Query Parameters**

| Parâmetro | Descrição | Tipo | Obrigatório | Valor Default |
|-----------|-----------|------|-------------|---------------|
| `pagina` | Número da página (começando em 0) | Integer | ❌ Não | `0` |
| `itens_por_pagina` | Quantidade de itens por página | Integer | ❌ Não | `20` |
| `data_inicio` | Data de início (YYYY-MM-DD) | String | ❌ Não | Nenhum |
| `data_fim` | Data de fim (YYYY-MM-DD) | String | ❌ Não | Nenhum |
| `relacoes` | Relacionamentos a carregar | String | ❌ Não | Nenhum |

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
```

#### **💡 Exemplo de Requisição**

```http
GET /api/v1/integracao/atendimento/todos?pagina=0&itens_por_pagina=10&data_inicio=2022-12-01&data_fim=2022-12-31&relacoes=atendimento_mensagem,cliente_servico
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

#### **📤 Exemplo de Resposta**

**Resposta de Sucesso:**
```json
{
  "status": "success",
  "msg": "Dados consultados com sucesso",
  "paginacao": {
    "primeira_pagina": 0,
    "ultima_pagina": 38,
    "pagina_atual": 0,
    "total_registros": 39
  },
  "atendimentos": [
    {
      "id_atendimento": 5448,
      "id_atendimento_status": 23,
      "id_tipo_atendimento": 125,
      "id_cliente_servico": 17812,
      "id_usuario_responsavel": null,
      "id_usuario_abertura": 4903,
      "protocolo": "20221229180833379797",
      "data_cadastro": "2022-12-29 18:08:33",
      "data_fechamento": null,
      "rascunho": false,
      "status_fechamento": null,
      "descricao_fechamento": null,
      "id_motivo_fechamento_atendimento": null,
      "deleted_at": null,
      "avaliacao": null,
      "comentario_avaliacao": null,
      "ordem_servico_count": 0,
      "ordem_servico_fechada": 0,
      "ordem_servico_aberta": 0,
      "ingressado": false,
      "data_cadastro_br": "29/12/2022 18:08",
      "data_cadastro_timestamp": 1672348113000,
      "data_fechamento_br": null,
      "data_fechamento_timestamp": null,
      "minutos_em_aberto": 61486,
      "tempo_restante": "-1023h 46min",
      "percentual_tempo_restante": 0,
      "percentual_color_class": "white-fg md-red-bg",
      "status": {
        "id_atendimento_status": 23,
        "prefixo": "aguardando_analise",
        "descricao": "Aguardando Análise",
        "cor": "md-deep-orange-A700-bg",
        "abrir_ordem_servico": false,
        "display": "Aguardando Análise"
      },
      "tipo_atendimento": {
        "id_tipo_atendimento": 125,
        "descricao": "COMERCIAL",
        "checklists": []
      },
      "cliente_servico": {
        "id_cliente_servico": 17812,
        "id_cliente": 24930,
        "id_servico": 2735,
        "numero_plano": 6,
        "display": "(6) (MIGRACAO-TESTEMAP) COMBO 10 MEGA - RÁDIO",
        "endereco_numero_completo": "RUA PADRE PAULO, 308 - MAE CHIQUINHA, SANTO ANTÔNIO DO MONTE/MG | CEP: 35560-000",
        "endereco_instalacao": {
          "id_cliente_servico_endereco": 73553,
          "id_endereco_numero": 52635,
          "id_cliente_servico": 17812,
          "tipo": "instalacao",
          "endereco_numero": {
            "id_endereco_numero": 52635,
            "numero": "308",
            "complemento": null,
            "coordenadas": {
              "type": "Point",
              "coordinates": [-45.292858, -20.092926]
            },
            "ativo": true,
            "id_cidade": 7674,
            "bairro": "MAE CHIQUINHA",
            "referencia": null,
            "endereco": "RUA PADRE PAULO",
            "cep": "35560000",
            "atualizar_coords_auto": false,
            "id_condominio": null,
            "cidade": {
              "id_cidade": 7674,
              "id_estado": 65,
              "nome": "Santo Antônio do Monte",
              "estado": {
                "id_estado": 65,
                "sigla": "MG"
              }
            }
          }
        },
        "servico": {
          "id_servico": 2735,
          "descricao": "(Migracao-TesteMap) COMBO 10 MEGA - RÁDIO",
          "id_servico_grupo": 51,
          "servico_grupo": {
            "id_servico_grupo": 51,
            "descricao": "GRUPO DE TESTE",
            "data_cadastro": "2020-04-15 13:52:01",
            "ativo": true
          }
        },
        "cliente": {
          "id_cliente": 24930,
          "ativo": true,
          "codigo_cliente": 1864,
          "nome_razaosocial": "LAVYNIA",
          "display": "(1864) LAVYNIA"
        }
      },
      "usuarios_responsaveis": [],
      "atendimento_mensagem": [
        {
          "id_atendimento_mensagem": 376,
          "id_atendimento": 5448,
          "mensagem": "TESTE",
          "data_cadastro_br": "10/02/2023 10:55",
          "data_cadastro_timestamp": 1676037311000
        },
        {
          "id_atendimento_mensagem": 375,
          "id_atendimento": 5448,
          "mensagem": "TESTE",
          "data_cadastro_br": "10/02/2023 10:55",
          "data_cadastro_timestamp": 1676037311000
        }
      ]
    }
  ]
}
```

### ➕ **Criação de Atendimento (POST)**

**Endpoint:** `/api/v1/integracao/atendimento`

#### **📋 Descrição**
Permite adicionar atendimentos em aberto/fechados dos clientes e retorna resposta em formato JSON.

#### **🎯 Método**
```http
POST /api/v1/integracao/atendimento
```

#### **📊 Parâmetros Obrigatórios**

| Atributo | Descrição | Tipo | Obrigatório |
|----------|-----------|------|-------------|
| `id_cliente_servico` | Identificador do serviço do cliente | Integer | ✅ Sim |
| `descricao` | Descrição detalhada do atendimento | String | ✅ Sim |
| `nome` | Nome do solicitante | String | ✅ Sim |
| `telefone` | Telefone do solicitante (DDNNNNNNNNN) | String | ✅ Sim |

#### **📊 Parâmetros Opcionais**

| Atributo | Descrição | Tipo | Obrigatório |
|----------|-----------|------|-------------|
| `id_tipo_atendimento` | Identificador do tipo de atendimento | Integer | ❌ Não |
| `id_atendimento_status` | Identificador do Status do Atendimento | Integer | ❌ Não |
| `id_usuario_responsavel` | Identificador do Usuário Responsável | Integer | ❌ Não |
| `email` | Email do solicitante (user@dominio.com) | String | ❌ Não |
| `id_origem_contato` | Identificador da Origem do Contato | Integer | ❌ Não |
| `id_disponibilidade` | Identificador da Disponibilidade | String | ❌ Não |
| `abrir_os` | Indica se deve abrir Ordem de Serviço | Boolean | ❌ Não |
| `parametros` | Parâmetros Dinâmicos (Array) | Array | ❌ Não |
| `parametros_ordem_servico` | Parâmetros Dinâmicos da O.S. (Array) | Array | ❌ Não |
| `parametros_fechamento` | Parâmetros Dinâmicos de fechamento (Array) | Array | ❌ Não |

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

#### **📝 Valores e Formatos**

| Campo | Formato | Valor Default | Exemplo |
|-------|---------|---------------|---------|
| `id_cliente_servico` | Integer | - | `1234` |
| `telefone` | `(DDNNNNNNNNN)` | - | `"11987654321"` |
| `email` | `user@dominio.com` | - | `"cliente@email.com"` |
| `abrir_os` | `true/false` | `false` | `true` |
| `id_disponibilidade` | String (IDs separados por vírgula) | - | `"1,2"` |
| `id_usuario_responsavel` | Integer (IDs separados por vírgula) | - | `"1,2"` |

#### **🔄 Parâmetros Dinâmicos**

**`parametros_ordem_servico` (Array):**
- `id_tipo_ordem_servico` (Integer)
- `status` (String)
- `ids_tecnicos` (String)
- `id_disponibilidade` (String)

**`parametros_fechamento` (Array):**
- `id_motivo_fechamento_atendimento` (Integer)
- `descricao_fechamento` (String)

#### **⚠️ Observações Importantes**

1. **🎯 Tipo Padrão:** Se `id_tipo_atendimento` não for enviado → tipo padrão **SAC**

2. **📊 Status Padrão:** Se `id_atendimento_status` não for enviado:
   - Com `abrir_os`: status **pendente**
   - Sem `abrir_os`: status **aguardando_analise**
   - 📋 Para obter IDs: `GET configuracao/status_atendimento`

3. **📦 Parâmetros Dinâmicos:** Permite armazenar informações extras do sistema (IDs de conversa, datas, dados de Omnichannel, etc.)

4. **🔧 OS Padrão:** Se `id_tipo_ordem_servico` não enviado → tipo **ABERTURA VIA API**

5. **⏳ Status OS Padrão:** Se `status` não enviado → **Aguardando Agendamento**

6. **👤 Técnico Padrão:** Se `ids_tecnicos` não enviado → técnico **SAC (Atendimento)**

7. **📅 Múltiplas Disponibilidades:** Use vírgulas: `"1,2,3"`
   - 📋 Para obter IDs: `GET /api/v1/integracao/configuracao/disponibilidade`

8. **👥 Múltiplos Responsáveis:** Use vírgulas: `"1,2,3"`

9. **🔒 Fechamento Automático:** Se parâmetros de fechamento não enviados:
   - **Motivo:** "Fechado Automático Atendimento"
   - **Descrição:** "Atendimento finalizado via API"

#### **💡 Exemplo de Requisição**

**Atendimento Simples:**
```json
POST /api/v1/integracao/atendimento
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "id_cliente_servico": 1234,
  "descricao": "Cliente reportando problema de conectividade com ping alto em jogos",
  "nome": "João Silva",
  "telefone": "11987654321",
  "email": "joao.silva@email.com",
  "id_tipo_atendimento": 132,
  "parametros": [
    {
      "jogo_afetado": "Valorant",
      "ping_atual": "80ms",
      "ping_normal": "20ms",
      "origem_bot": "telegram"
    }
  ]
}
```

**Atendimento com Ordem de Serviço:**
```json
{
  "id_cliente_servico": 1234,
  "descricao": "Problema de conectividade requer visita técnica",
  "nome": "João Silva",
  "telefone": "11987654321",
  "abrir_os": true,
  "id_disponibilidade": "1,2",
  "parametros_ordem_servico": [
    {
      "id_tipo_ordem_servico": 15,
      "status": "aguardando_agendamento",
      "ids_tecnicos": "5,10"
    }
  ]
}
```

#### **📤 Exemplo de Resposta**

**Resposta de Sucesso:**
```json
{
  "status": "success",
  "msg": "Atendimento aberto com sucesso. Anote o protocolo: 201811161058216. Foi aberto também uma ordem de serviço e encaminhada ao sertor responsável",
  "atendimento": {
    "id_atendimento": 300,
    "protocolo": "201811161058216",
    "descricao_abertura": "Estou sem acesso a internet desde segunda-feira. | ATENDIMENTO ABERTO VIA API",
    "descricao_fechamento": null,
    "tipo_atendimento": "SAC",
    "usuario_abertura": "IP Telecom",
    "usuario_responsavel": "IP Telecom",
    "usuario_fechamento": null,
    "data_cadastro": "16/11/2018",
    "data_fechamento": null,
    "setor_responsavel": null,
    "status_fechamento": null,
    "motivo_fechamento": null,
    "status": "Aguardando Análise",
    "cliente": {
      "codigo_cliente": 1204,
      "nome_razaosocial": "BIANCA COUTO",
      "cpf_cnpj": "86214941081"
    },
    "ordens_servico": [
      {
        "id_ordem_servico": 340,
        "numero_ordem_servico": "320",
        "data_cadastro": "16/11/2018 10:58:21",
        "tipo": "ABERTURA VIA API",
        "data_inicio_programado": "16/11/2018 11:58:21",
        "data_termino_programado": "16/11/2018 12:58:21",
        "data_inicio_executado": null,
        "data_termino_executado": null,
        "descricao_abertura": "Estou sem acesso a internet desde segunda-feira. | ATENDIMENTO ABERTO VIA API",
        "descricao_servico": "Estou sem acesso a internet desde segunda-feira. | ATENDIMENTO ABERTO VIA API",
        "descricao_fechamento": null,
        "usuario_abertura": "IP Telecom",
        "usuario_fechamento": null,
        "status": "aguardando_agendamento",
        "status_fechamento": null,
        "cliente": {
          "codigo_cliente": 1204,
          "nome_razaosocial": "BIANCA COUTO",
          "cpf_cnpj": "86214941081"
        },
        "servico": {
          "numero_plano": 9,
          "nome": "NEXT-NV_1MBPS",
          "valor": 69.9,
          "status": "Serviço Habilitado",
          "status_prefixo": "servico_habilitado"
        }
      }
    ]
  }
}
```

### ✏️ **Edição/Fechamento de Atendimento (PUT)**

**Endpoint:** `/api/v1/integracao/atendimento/:id_atendimento`

#### **📋 Descrição**
Permite editar e fechar atendimentos em aberto dos clientes, incluindo suas ordens de serviço associadas.

#### **🎯 Método**
```http
PUT /api/v1/integracao/atendimento/:id_atendimento
```

#### **📊 Parâmetros**

| Atributo | Descrição | Tipo | Obrigatório | Valor Default |
|----------|-----------|------|-------------|---------------|
| `fechar_atendimento` | Indica se deve fechar o atendimento e suas OS | Boolean | ✅ Sim | `false` |
| `descricao` | Descrição de abertura do atendimento | String | ❌ Não | Nenhum |
| `parametros_fechamento` | Parâmetros Dinâmicos de fechamento | Object | ❌ Não | `[]` |
| `parametros` | Informações da integração (JSON) | Object | ❌ Não | Nenhum |
| `id_atendimento_status` | Novo status de atendimento | Integer | ❌ Não | Nenhum |
| `id_tipo_atendimento` | Novo tipo de atendimento | Integer | ❌ Não | Nenhum |

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

#### **🛤️ Path Variables**
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `id_atendimento` | ID do Atendimento a ser editado | `123` |

#### **🔄 Parâmetros de Fechamento**

**`parametros_fechamento` (Object):**
- `id_motivo_fechamento` (Integer) - ID do motivo de fechamento
- `descricao_fechamento` (String) - Descrição do fechamento
- `status_fechamento` (String) - Status final do fechamento

#### **⚠️ Regras Importantes**

1. **🚫 Status + Fechamento:** Não é possível alterar status E fechar simultaneamente
   - Para alterar apenas status: `fechar_atendimento: false`
   - Para finalizar: não incluir `id_atendimento_status`

2. **🚫 Tipo + Fechamento:** Não é possível alterar tipo E fechar simultaneamente
   - Para alterar apenas tipo: `fechar_atendimento: false`
   - Para finalizar: não incluir `id_tipo_atendimento`

3. **🔒 Fechamento Completo:** Ao fechar, todas as ordens de serviço associadas também são fechadas

#### **💡 Exemplos de Requisição**

**Fechamento Completo com Parâmetros:**
```json
PUT /api/v1/integracao/atendimento/123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "parametros": {
    "origem_bot": "telegram",
    "protocolo_interno": "ATD000045",
    "categoria_problema": "conectividade",
    "jogo_afetado": "Valorant",
    "resolucao": "Otimização de rota realizada",
    "satisfacao_cliente": 5
  },
  "parametros_fechamento": {
    "id_motivo_fechamento": 108,
    "descricao_fechamento": "Problema de conectividade resolvido via otimização de QoS",
    "status_fechamento": "concluido"
  },
  "fechar_atendimento": true
}
```

**Atualização de Status (sem fechar):**
```json
PUT /api/v1/integracao/atendimento/123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "id_atendimento_status": 3,
  "descricao": "Atendimento em análise pela equipe técnica",
  "fechar_atendimento": false,
  "parametros": {
    "atualizado_por": "bot_telegram",
    "analise_tecnica": "em_andamento"
  }
}
```

**Atualização de Tipo (sem fechar):**
```json
PUT /api/v1/integracao/atendimento/123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "id_tipo_atendimento": 150,
  "fechar_atendimento": false,
  "parametros": {
    "reclassificado_para": "suporte_tecnico_especializado",
    "motivo_reclassificacao": "problema_complexo"
  }
}
```

**Exemplo Original da Documentação:**
```json
PUT /api/v1/integracao/atendimento/123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "parametros": {
    "url_ligacao": "https://www.meusite.com.br/ligacao/3",
    "software": "PBX ABCDE",
    "outro_parametro": 123456
  },
  "parametros_fechamento": {
    "id_motivo_fechamento": 108,
    "descricao_fechamento": "Finalizado",
    "status_fechamento": "concluido"
  },
  "fechar_atendimento": true
}
```

#### **📤 Exemplo de Resposta**

**Resposta de Sucesso (Fechamento):**
```json
{
  "status": "success",
  "msg": "Atendimento atualizado com sucesso",
  "atendimento": {
    "id_atendimento": 1114,
    "protocolo": "202003051452007",
    "id_cliente_servico": 13677,
    "id_tipo_atendimento": 44,
    "id_usuario_abertura": 56,
    "id_usuario_fechamento": 1,
    "descricao_abertura": "INSTALAÇÃO NOVA",
    "descricao_fechamento": "Fechamento automático.",
    "data_cadastro": "2020-03-05 14:52:00",
    "data_fechamento": "2020-03-11 09:56:10",
    "ip_cadastro": null,
    "id_usuario_responsavel": 22,
    "id_setor_responsavel": null,
    "destino": "usuario",
    "status_fechamento": "concluido",
    "id_motivo_fechamento_atendimento": 5,
    "id_atendimento_status": 24,
    "resultado_diagnostico": null,
    "nome_contato": "TESTE APRESENT",
    "telefone_contato": "3734151100",
    "email_contato": null,
    "rascunho": false,
    "deleted_at": null,
    "id_origem_contato": null,
    "avaliacao": null,
    "comentario_avaliacao": null,
    "push_notification_enviado": false,
    "data_cadastro_br": "05/03/2020 14:52",
    "data_cadastro_timestamp": 1583430720000,
    "data_fechamento_br": "11/03/2020 09:56",
    "data_fechamento_timestamp": 1583931370000,
    "minutos_em_aberto": 8344,
    "tempo_restante": "-138h 4min",
    "percentual_tempo_restante": 0,
    "percentual_color_class": "white-fg md-red-bg"
  }
}
```

### 💬 **Adicionar Mensagem ao Atendimento (POST)**

**Endpoint:** `/api/v1/integracao/atendimento/adicionar_mensagem/:id_atendimento`

#### **📋 Descrição**
Permite adicionar mensagens a atendimentos abertos dos clientes e retorna resposta em formato JSON.

#### **🎯 Método**
```http
POST /api/v1/integracao/atendimento/adicionar_mensagem/:id_atendimento
```

#### **📊 Parâmetros**

| Atributo | Descrição | Tipo | Obrigatório | Valor Default |
|----------|-----------|------|-------------|---------------|
| `mensagem` | Mensagem que será adicionada | String | ✅ Sim | Nenhum |

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

#### **🛤️ Path Variables**
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `id_atendimento` | ID do Atendimento | `123` |

#### **💡 Exemplos de Requisição**

**Mensagem Simples:**
```json
POST /api/v1/integracao/atendimento/adicionar_mensagem/123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "mensagem": "TESTE ADICIONAR API MENSAGEM2"
}
```

**Mensagem do Bot Telegram:**
```json
POST /api/v1/integracao/atendimento/adicionar_mensagem/456
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "mensagem": "Bot Telegram: Cliente reportou melhoria no ping após otimização. Ping atual: 25ms (anterior: 85ms). Status: Resolvido."
}
```

**Mensagem de Update Status:**
```json
POST /api/v1/integracao/atendimento/adicionar_mensagem/789
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "mensagem": "Sistema: Atendimento escalado para equipe técnica especializada. Motivo: Problema complexo de conectividade requer análise avançada de rede."
}
```

### 📎 **Adicionar Anexos ao Atendimento (POST)**

**Endpoint:** `/api/v1/integracao/atendimento/adicionar_anexo/:id_atendimento`

#### **📋 Descrição**
Permite adicionar anexos (arquivos) aos atendimentos dos clientes e retorna resposta em formato JSON.

#### **🎯 Método**
```http
POST /api/v1/integracao/atendimento/adicionar_anexo/:id_atendimento
```

#### **📊 Parâmetros**

| Atributo | Descrição | Tipo | Obrigatório | Valor Default |
|----------|-----------|------|-------------|---------------|
| `files` | Arquivo(s) que será(ão) adicionado(s) | File | ✅ Sim | Nenhum |

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

#### **🛤️ Path Variables**
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `id_atendimento` | ID do Atendimento | `123` |

#### **📁 Formato do Body**
```
Content-Type: multipart/form-data

files[0]: [arquivo1.jpg]
files[1]: [arquivo2.pdf]
files[2]: [screenshot.png]
```

#### **💡 Exemplos de Requisição**

**Anexo Único (cURL):**
```bash
curl -X POST "/api/v1/integracao/atendimento/adicionar_anexo/123" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Content-Type: multipart/form-data" \
  -F "files[0]=@/path/to/screenshot_problema.png"
```

**Múltiplos Anexos (cURL):**
```bash
curl -X POST "/api/v1/integracao/atendimento/adicionar_anexo/456" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Content-Type: multipart/form-data" \
  -F "files[0]=@/path/to/speedtest_result.png" \
  -F "files[1]=@/path/to/network_config.txt" \
  -F "files[2]=@/path/to/traceroute_log.txt"
```

**JavaScript (FormData):**
```javascript
const formData = new FormData();
formData.append('files[0]', file1); // arquivo do input file
formData.append('files[1]', file2); // segundo arquivo

fetch('/api/v1/integracao/atendimento/adicionar_anexo/123', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token
    // Não definir Content-Type - o navegador define automaticamente
  },
  body: formData
});
```

**Python (requests):**
```python
import requests

files = {
    'files[0]': open('screenshot.png', 'rb'),
    'files[1]': open('config.txt', 'rb')
}

headers = {
    'Authorization': 'Bearer ' + access_token
}

response = requests.post(
    'https://api.hubsoft.com.br/api/v1/integracao/atendimento/adicionar_anexo/123',
    headers=headers,
    files=files
)
```

#### **📋 Tipos de Arquivo Comuns para Gaming Support**
- **Screenshots:** `.png`, `.jpg`, `.jpeg` - Capturas de tela do problema
- **Logs:** `.txt`, `.log` - Logs de conexão, ping, traceroute
- **Configurações:** `.cfg`, `.ini`, `.xml` - Arquivos de configuração
- **Documentos:** `.pdf`, `.doc` - Relatórios técnicos
- **Compactados:** `.zip`, `.rar` - Múltiplos arquivos agrupados

#### **📤 Exemplo de Resposta**

**Resposta de Sucesso:**
```json
{
  "status": "success",
  "msg": "Anexo Adicionado com sucesso",
  "atendimento": {
    "id_atendimento": 35051,
    "protocolo": "20250813164713274745"
  }
}
```

#### **⚠️ Observações**
- 📁 **Múltiplos arquivos:** Use indexação `files[0]`, `files[1]`, etc.
- 📊 **Content-Type:** Deve ser `multipart/form-data`
- 🔒 **Autenticação:** Bearer token obrigatório
- 📏 **Limites:** Verifique limites de tamanho com administrador HubSoft
- ✅ **Resposta:** Retorna ID e protocolo oficial do atendimento

### 🔍 **Consultar Atendimentos por Cliente (GET)**

**Endpoint:** `/api/v1/integracao/cliente/atendimento`

#### **📋 Descrição**
Permite consultar atendimentos em aberto/fechados dos clientes com filtros avançados e retorna resposta em formato JSON.

#### **🎯 Método**
```http
GET /api/v1/integracao/cliente/atendimento
```

#### **📊 Parâmetros Obrigatórios**

| Atributo | Descrição | Tipo | Obrigatório |
|----------|-----------|------|-------------|
| `busca` | Tipo de busca que deseja fazer no cliente | String | ✅ Sim |
| `termo_busca` | Termo utilizado para fazer a busca | String | ✅ Sim |

#### **📊 Parâmetros Opcionais**

| Atributo | Descrição | Tipo | Valor Default |
|----------|-----------|------|---------------|
| `limit` | Limite de resultados (Min: 1, Max: 50) | Integer | `20` |
| `apenas_pendente` | Trazer apenas atendimentos pendentes (abertos) | String | `sim` |
| `order_by` | Campo utilizado para ordenação | String | `data_cadastro` |
| `order_type` | Tipo de ordenação | String | `asc` |
| `data_inicio` | Data de início (YYYY-MM-DD) | String | Nenhum |
| `data_fim` | Data de fim (YYYY-MM-DD) | String | Nenhum |
| `relacoes` | Relacionamentos a carregar | String | Nenhum |

#### **🔧 Headers**
```http
Authorization: Bearer {access_token}
```

#### **📝 Valores Aceitos**

| Campo | Valores Possíveis | Exemplo |
|-------|------------------|---------|
| `busca` | `codigo_cliente`, `cpf_cnpj`, `id_cliente_servico`, `protocolo` | `cpf_cnpj` |
| `apenas_pendente` | `sim`, `nao` | `sim` |
| `order_by` | `data_cadastro`, `data_fechamento` | `data_cadastro` |
| `order_type` | `asc`, `desc` | `desc` |
| `relacoes` | `atendimento_mensagem`, `ordem_servico_mensagem`, `checklists` | `atendimento_mensagem` |

#### **💡 Exemplos de Requisição**

**Busca por CPF (atendimentos pendentes):**
```http
GET /api/v1/integracao/cliente/atendimento?busca=cpf_cnpj&termo_busca=12345678901&apenas_pendente=sim&limit=10
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

**Busca por Protocolo com Mensagens:**
```http
GET /api/v1/integracao/cliente/atendimento?busca=protocolo&termo_busca=ATD000045&relacoes=atendimento_mensagem
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

**Busca por Cliente com Filtro de Data:**
```http
GET /api/v1/integracao/cliente/atendimento?busca=codigo_cliente&termo_busca=1234&data_inicio=2025-09-01&data_fim=2025-09-30&order_by=data_cadastro&order_type=desc&limit=25
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

**Busca por Serviço do Cliente (todos os atendimentos):**
```http
GET /api/v1/integracao/cliente/atendimento?busca=id_cliente_servico&termo_busca=5678&apenas_pendente=nao&relacoes=atendimento_mensagem,checklists&limit=50
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

#### **🎮 Casos de Uso para Gaming Support**

**Verificar atendimentos de um cliente antes de abrir novo:**
```http
GET /api/v1/integracao/cliente/atendimento?busca=cpf_cnpj&termo_busca=12345678901&apenas_pendente=sim&limit=5
```

**Buscar histórico completo para análise:**
```http
GET /api/v1/integracao/cliente/atendimento?busca=cpf_cnpj&termo_busca=12345678901&apenas_pendente=nao&data_inicio=2025-01-01&order_by=data_cadastro&order_type=desc&relacoes=atendimento_mensagem
```

**Localizar atendimento específico por protocolo interno:**
```http
GET /api/v1/integracao/cliente/atendimento?busca=protocolo&termo_busca=ATD000045&relacoes=atendimento_mensagem,checklists
```

#### **📤 Exemplo de Resposta**

**Resposta de Sucesso:**
```json
{
  "status": "suscess",
  "msg": "Dados consultados com sucesso",
  "atendimentos": [
    {
      "id_atendimento": 110,
      "protocolo": "201806191505251",
      "descricao_abertura": "VERIFICAR CONEXÃO",
      "descricao_fechamento": null,
      "tipo_atendimento": "TÉCNICO - QUEDAS DE CONEXÃO",
      "usuario_abertura": "Bianca Couto",
      "usuario_responsavel": "Bianca Couto",
      "usuario_fechamento": null,
      "data_cadastro": "19/06/2018",
      "data_fechamento": null,
      "setor_responsavel": null,
      "status_fechamento": null,
      "motivo_fechamento": null,
      "status": "Pendente",
      "cliente": {
        "codigo_cliente": 1204,
        "nome_razaosocial": "BIANCA COUTO",
        "cpf_cnpj": "86214941081"
      },
      "servico": {
        "id_cliente_servico": "123",
        "numero_plano": 0,
        "nome": "5MB-WIRELLES-TESTE",
        "valor": 199.9,
        "status": "Cancelado",
        "status_prefixo": "cancelado"
      },
      "ordens_servico": [
        {
          "id_ordem_servico": 131,
          "numero_ordem_servico": "125",
          "data_cadastro": "19/06/2018 15:05:25",
          "tipo": "SUPORTE",
          "data_inicio_programado": "19/06/2018 14:02:00",
          "data_termino_programado": "19/06/2018 15:02:00",
          "data_inicio_executado": "19/06/2018 14:02:00",
          "data_termino_executado": "19/06/2018 15:02:00",
          "descricao_abertura": "VERIFICAR CONEXÃO",
          "descricao_servico": "VERIFICAR CONEXÃO",
          "descricao_fechamento": "asdfasdfadsf",
          "usuario_abertura": "Bianca Couto",
          "usuario_fechamento": "Bianca Couto",
          "status": "finalizado",
          "status_fechamento": "concluido",
          "cliente": {
            "codigo_cliente": 1204,
            "nome_razaosocial": "BIANCA COUTO",
            "cpf_cnpj": "86214941081"
          },
          "servico": {
            "id_cliente_servico": "123",
            "numero_plano": 0,
            "nome": "5MB-WIRELLES-TESTE",
            "valor": 199.9,
            "status": "Cancelado",
            "status_prefixo": "cancelado"
          }
        }
      ]
    },
    {
      "id_atendimento": 285,
      "protocolo": "201811061724214",
      "descricao_abertura": "Abertura de atendimento através da API | ATENDIMENTO ABERTO VIA CENTRAL DO ASSINANTE",
      "descricao_fechamento": null,
      "tipo_atendimento": "SAC",
      "usuario_abertura": "Master",
      "usuario_responsavel": "Master",
      "usuario_fechamento": null,
      "data_cadastro": "06/11/2018",
      "data_fechamento": null,
      "setor_responsavel": null,
      "status_fechamento": null,
      "motivo_fechamento": null,
      "status": "Aguardando Análise",
      "cliente": {
        "codigo_cliente": 1204,
        "nome_razaosocial": "BIANCA COUTO",
        "cpf_cnpj": "86214941081"
      },
      "ordens_servico": []
    },
    {
      "id_atendimento": 300,
      "protocolo": "201811161058216",
      "descricao_abertura": "Estou sem acesso a internet desde segunda-feira. | ATENDIMENTO ABERTO VIA API",
      "descricao_fechamento": null,
      "tipo_atendimento": "SAC",
      "usuario_abertura": "IP Telecom",
      "usuario_responsavel": "IP Telecom",
      "usuario_fechamento": null,
      "data_cadastro": "16/11/2018",
      "data_fechamento": null,
      "setor_responsavel": null,
      "status_fechamento": null,
      "motivo_fechamento": null,
      "status": "Aguardando Análise",
      "cliente": {
        "codigo_cliente": 1204,
        "nome_razaosocial": "BIANCA COUTO",
        "cpf_cnpj": "86214941081"
      },
      "servico": {
        "id_cliente_servico": "12345",
        "numero_plano": 9,
        "nome": "NEXT-NV_1MBPS",
        "valor": 69.9,
        "status": "Serviço Habilitado",
        "status_prefixo": "servico_habilitado"
      },
      "ordens_servico": [
        {
          "id_ordem_servico": 340,
          "numero_ordem_servico": "320",
          "data_cadastro": "16/11/2018 10:58:21",
          "tipo": "ABERTURA VIA API",
          "data_inicio_programado": "16/11/2018 11:58:21",
          "data_termino_programado": "16/11/2018 12:58:21",
          "data_inicio_executado": null,
          "data_termino_executado": null,
          "descricao_abertura": "Estou sem acesso a internet desde segunda-feira. | ATENDIMENTO ABERTO VIA API",
          "descricao_servico": "Estou sem acesso a internet desde segunda-feira. | ATENDIMENTO ABERTO VIA API",
          "descricao_fechamento": null,
          "usuario_abertura": "IP Telecom",
          "usuario_fechamento": null,
          "status": "aguardando_agendamento",
          "status_fechamento": null,
          "cliente": {
            "codigo_cliente": 1204,
            "nome_razaosocial": "BIANCA COUTO",
            "cpf_cnpj": "86214941081"
          },
          "servico": {
            "id_cliente_servico": "12345",
            "numero_plano": 9,
            "nome": "NEXT-NV_1MBPS",
            "valor": 69.9,
            "status": "Serviço Habilitado",
            "status_prefixo": "servico_habilitado"
          }
        }
      ]
    }
  ]
}
```

#### **📊 Estrutura da Resposta**
- **`status`:** Status da operação (`"suscess"` ou `"error"`)
- **`msg`:** Mensagem descritiva do resultado
- **`atendimentos`:** Array com os atendimentos encontrados

#### **🎯 Campos do Atendimento**
- **`id_atendimento`:** ID numérico interno
- **`protocolo`:** Protocolo oficial único (ex: `"201806191505251"`)
- **`status`:** Status atual (`"Pendente"`, `"Aguardando Análise"`, etc.)
- **`tipo_atendimento`:** Categoria do atendimento
- **`cliente`:** Dados completos do cliente
- **`servico`:** Informações do serviço/plano
- **`ordens_servico`:** Array com ordens de serviço relacionadas

#### **⚠️ Observações**
- 📊 **Limite máximo:** 50 resultados por requisição
- 📅 **Datas:** Usa data de cadastro como base para filtros
- 🔗 **Relações:** Use vírgulas para múltiplos relacionamentos
- 🔍 **Busca flexível:** Aceita diferentes tipos de identificadores
- ⏰ **Ordenação:** Por data de cadastro ou fechamento
- ✅ **Protocolo oficial:** Campo `protocolo` contém ID único do atendimento

---

## 🔧 **ENDPOINTS DE ORDEM DE SERVIÇO** {#endpoints-ordem-servico}

*Aguardando documentação...*

---

## 📊 **ESTRUTURAS DE DADOS** {#estruturas-dados}

*Aguardando documentação...*

---

## ⚠️ **CÓDIGOS DE ERRO** {#codigos-erro}

*Aguardando documentação...*

---

## 💡 **EXEMPLOS DE USO** {#exemplos-uso}

*Aguardando documentação...*

---

> **📝 Nota:** Este documento será atualizado conforme a documentação da API HubSoft for fornecida.