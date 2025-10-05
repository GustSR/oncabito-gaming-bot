# Documentação API Hubsoft - Guia de Uso

## 📋 Sobre Este Pacote

Este pacote contém a documentação completa e estruturada de todos os endpoints da API Hubsoft, extraída diretamente da documentação oficial em https://docs.hubsoft.com.br/

## 📊 Estatísticas

- **Total de Endpoints:** 175
- **Total de Categorias:** 46
- **Métodos HTTP:** GET, POST, PUT, DELETE
- **Formato:** JSON
- **Autenticação:** OAuth 2.0

## 📁 Arquivos Incluídos

### 1. `hubsoft_api_documentation.md` (8.1 MB)
**Documentação completa e detalhada** de todos os 175 endpoints organizados por categoria.

**Conteúdo:**
- Método HTTP de cada endpoint
- URL completa do endpoint
- Descrição detalhada
- Parâmetros obrigatórios e opcionais
- Headers necessários
- Exemplos de corpo de requisição JSON
- Exemplos de resposta JSON com diferentes cenários

### 2. `hubsoft_collection.json` (23.110 linhas)
**Coleção original do Postman** que pode ser importada diretamente no Postman para testar os endpoints.

### 3. `endpoints_processed.json`
**Dados estruturados em JSON** para uso programático, facilitando integração e automação.

## 🔐 Credenciais Necessárias

Para utilizar a API Hubsoft, você precisa dos seguintes dados:

| Campo | Descrição |
|-------|-----------|
| `url` | URL base da sua API (ex: https://api.seudominio.com.br) |
| `client_id` | ID do cliente (criado pelo administrador) |
| `client_secret` | Chave secreta do cliente |
| `username` | Nome de usuário para autenticação |
| `password` | Senha do usuário |

## 🚀 Exemplo de Uso

### 1. Autenticação (Obter Token)

```bash
POST /oauth/token
Content-Type: application/json

{
  "client_id": "seu_client_id",
  "client_secret": "seu_client_secret",
  "username": "seu_usuario",
  "password": "sua_senha",
  "grant_type": "password"
}
```

**Resposta:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 31536000
}
```

### 2. Usando o Token em Requisições

```bash
GET /api/v1/integracao/cliente/:id
Authorization: Bearer {access_token}
```

## 📚 Principais Categorias

### Autenticação (1 endpoint)
- oAuth - Obtenção do token de acesso

### Clientes (4 endpoints)
- Consultar, adicionar, editar e excluir clientes

### Atendimento (9 endpoints)
- Gestão completa de atendimentos e tickets

### Financeiro (6 endpoints)
- Cobranças, faturas e pagamentos

### Ordem de Serviço (14 endpoints)
- Gerenciamento completo de OS

### Estoque (8 endpoints)
- Controle de produtos, entradas e saídas

### Nota Fiscal (7 endpoints)
- NFE (55), NFSE, NFCOM e Telecom (21/22)

### Rede (4 endpoints)
- Gestão de infraestrutura de rede

### Configuração (14 endpoints)
- Configurações gerais do sistema

### Outras Categorias
Alerta, Ações, CPE, Caixas Ópticas, Cliente Serviço, Cobrança Avulsa, Contrato, CRM, Documentação de Senhas, Entrada, Evento de Faturamento, Fatura, Fornecedor, Local de Estoque, Movimentações de Estoque, PBX, Pacote, Patrimônio, Porta Atendimento, Produto, Produtos Vínculados, Projetos, Prospectos, Renegociação, Retorno Estoque, Saída, Serviços, Tarefas, Transferência, Viabilidade e Outros.

## 📖 Paginação

A API utiliza paginação para endpoints que retornam grandes volumes de dados:

- **Primeira página:** 0 (zero)
- **Parâmetro:** `?page=N`
- **Resposta inclui:** `primeira_pagina`, `ultima_pagina`, `pagina_atual`, `total_registros`

**Exemplo:**
```
GET /api/v1/integracao/cliente/paginado/10?page=0
```

## ✅ Estrutura de Resposta Padrão

```json
{
  "status": "success",
  "msg": "Mensagem descritiva da operação",
  "dados": {
    // Dados retornados
  }
}
```

## ⚠️ Observações Importantes

- Nem todos os endpoints suportam operações CRUD completas
- Alguns endpoints estão disponíveis apenas para consulta (GET)
- A autenticação OAuth é obrigatória para todos os endpoints (exceto o de autenticação)
- Todas as respostas seguem o padrão REST com códigos HTTP apropriados
- Todos os dados são trocados em formato JSON

## 🔗 Links Úteis

- **Documentação Oficial:** https://docs.hubsoft.com.br/
- **Site Hubsoft:** https://hubsoft.com.br/

## 📝 Como Usar Este Pacote

1. **Para leitura humana:** Abra o arquivo `hubsoft_api_documentation.md` em qualquer editor Markdown ou visualizador
2. **Para testes no Postman:** Importe o arquivo `hubsoft_collection.json` no Postman
3. **Para integração programática:** Use o arquivo `endpoints_processed.json` para acessar os dados estruturados

---

**Documentação extraída em:** 05 de Outubro de 2025  
**Versão da API:** Latest  
**Fonte:** https://docs.hubsoft.com.br/
