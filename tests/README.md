# 🧪 Testes - OnCabo Gaming Bot

Este diretório contém todos os testes do projeto OnCabo Gaming Bot.

**Última atualização:** 04 de Novembro de 2025
**Status:** Testes básicos implementados - Expansão em andamento
**Cobertura atual:** Testes para inconsistências críticas resolvidas

## 📁 Estrutura

```
tests/
├── conftest.py                                      # Fixtures globais do pytest
├── unit/                                            # Testes unitários
│   ├── handlers/                                    # Testes de handlers
│   │   ├── test_user_verification.py               # ✅ Verificação de usuário (TASK-002)
│   │   ├── test_callback_idempotency.py            # ✅ Idempotência de callbacks (Inconsist. #3)
│   │   └── test_permission_error_handling.py       # ✅ Erros de permissão (Inconsist. #9)
│   ├── locking/                                     # Testes de locks
│   │   └── test_distributed_lock.py                # ✅ Race conditions (Inconsist. #1)
│   ├── entities/                                    # Testes de entidades
│   │   └── test_cpf_verification_context.py        # ✅ Persistência de contexto (Inconsist. #2)
│   └── use_cases/                                   # Testes de Use Cases (TODO)
├── integration/                                     # Testes de integração (TODO)
└── fixtures/                                        # Dados de teste (TODO)
```

## 🚀 Executando os Testes

### Instalar dependências de teste

```bash
# Instalar todas as dependências de teste
pip install -r requirements-test.txt

# OU instalar apenas o básico
pip install pytest pytest-asyncio pytest-cov
```

### Executar todos os testes

```bash
pytest
```

### Executar testes com coverage

```bash
pytest --cov=src/sentinela --cov-report=html --cov-report=term
```

### Executar apenas testes críticos

```bash
pytest -m critical
```

### Executar apenas testes unitários

```bash
pytest tests/unit/
```

### Executar apenas testes de integração

```bash
pytest tests/integration/
```

### Executar testes em modo verbose

```bash
pytest -v
```

### Executar testes e parar no primeiro erro

```bash
pytest -x
```

## 📊 Coverage

Após executar testes com coverage, abra o relatório HTML:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Meta de Coverage

- **Alvo geral:** 80%+
- **Handlers críticos:** 90%+
- **Use Cases:** 85%+
- **Value Objects:** 95%+

## 🎯 Testes Críticos

### ✅ test_user_verification.py

Testa a correção do **BUG TASK-002**: usuários com CPF `COMPLETED` mas status `INACTIVE` não devem ter acesso.

**Cenário crítico:**
```python
# Usuário com CPF verificado mas plano cancelado
user.cpf_verification.status = "COMPLETED"  # ✅
user.status = "INACTIVE"                     # ❌

# Deve retornar False (não permitir acesso)
assert _check_user_verified(user_id) == False
```

Este teste garante que o bug não volte após refatorações.

## 🧩 Fixtures Disponíveis

Fixtures definidas em `conftest.py`:

| Fixture | Descrição |
|---------|-----------|
| `event_loop` | Event loop para testes async |
| `mock_container` | DI Container mockado |
| `mock_telegram_update` | Update do Telegram mockado |
| `mock_telegram_context` | Context do bot mockado |
| `mock_user_repository` | Repositório de usuários mockado |
| `mock_cpf_repository` | Repositório de CPF mockado |
| `mock_cpf_use_case` | Use case de CPF mockado |
| `mock_hubsoft_use_case` | Use case HubSoft mockado |
| `mock_user_entity` | Entidade User (ACTIVE) |
| `mock_inactive_user_entity` | Entidade User (INACTIVE) |

### Exemplo de uso

```python
@pytest.mark.asyncio
async def test_my_feature(mock_telegram_update, mock_telegram_context):
    """Teste usando fixtures mockadas."""
    handler = MyHandler()
    await handler.handle_message(mock_telegram_update, mock_telegram_context)

    mock_telegram_update.message.reply_text.assert_called_once()
```

## 📝 Markers

Markers personalizados disponíveis:

- `@pytest.mark.asyncio` - Testes assíncronos
- `@pytest.mark.unit` - Testes unitários
- `@pytest.mark.integration` - Testes de integração
- `@pytest.mark.critical` - Testes críticos
- `@pytest.mark.slow` - Testes lentos

### Exemplo

```python
@pytest.mark.critical
@pytest.mark.asyncio
async def test_critical_feature():
    """Teste crítico que não pode falhar."""
    pass
```

## 🔧 Boas Práticas

### 1. Testes devem ser independentes

```python
# ❌ Ruim: testes dependentes
def test_create_user():
    global user_id
    user_id = create_user()

def test_get_user():
    user = get_user(user_id)  # Depende do teste anterior!

# ✅ Bom: cada teste é independente
def test_create_user(mock_user_repository):
    user_id = create_user()
    assert user_id is not None

def test_get_user(mock_user_repository):
    mock_user_repository.find.return_value = mock_user
    user = get_user(123)
    assert user is not None
```

### 2. Use nomes descritivos

```python
# ❌ Ruim
def test_1():
    pass

# ✅ Bom
def test_active_user_should_have_access():
    """Usuário ACTIVE deve ter acesso às funcionalidades."""
    pass
```

### 3. AAA Pattern (Arrange, Act, Assert)

```python
async def test_user_verification():
    # Arrange - Prepara dados de teste
    user = create_test_user(status="ACTIVE")

    # Act - Executa a ação sendo testada
    result = await verify_user(user.id)

    # Assert - Verifica o resultado
    assert result is True
```

### 4. Um assert por teste (quando possível)

```python
# ❌ Ruim: múltiplos asserts não relacionados
def test_user():
    assert user.name == "Test"
    assert user.email == "test@test.com"
    assert user.is_active is True

# ✅ Bom: cada teste verifica um comportamento
def test_user_name():
    assert user.name == "Test"

def test_user_email():
    assert user.email == "test@test.com"

def test_user_is_active():
    assert user.is_active is True
```

## 🐛 Debugging Testes

### Executar com pdb (Python debugger)

```bash
pytest --pdb
```

### Ver output de print()

```bash
pytest -s
```

### Ver logs detalhados

```bash
pytest --log-cli-level=DEBUG
```

## 📚 Referências

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)

---

**Última atualização:** 04/11/2025
**Projeto:** OnCabo Gaming Bot
**Branch:** `main`
