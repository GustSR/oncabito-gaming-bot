# 🧪 Guia de Setup de Testes - Sentinela Bot

> **Última atualização:** 21 de Outubro de 2025

Este guia mostra como configurar e executar os testes do Sentinela Bot.

---

## 📋 Pré-requisitos

- Python 3.10+
- pip instalado
- Git

---

## 🚀 Setup Rápido

### 1. Instalar pip (se necessário)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3-pip
```

**CentOS/RHEL:**
```bash
sudo yum install python3-pip
```

**Verificar instalação:**
```bash
pip3 --version
# ou
python3 -m pip --version
```

### 2. Instalar dependências de teste

```bash
cd /caminho/do/projeto

# Instalar todas as dependências de teste
pip3 install -r requirements-test.txt

# OU instalar apenas o essencial
pip3 install pytest pytest-asyncio pytest-cov
```

### 3. Verificar instalação

```bash
pytest --version
# Deve mostrar: pytest 7.4.3 (ou superior)
```

---

## 🧪 Executando os Testes

### Executar todos os testes

```bash
# Modo básico
pytest tests/

# Modo verbose (detalhado)
pytest tests/ -v

# Modo quiet (apenas resumo)
pytest tests/ -q
```

### Executar testes específicos

```bash
# Apenas testes de locks
pytest tests/unit/locking/ -v

# Apenas testes de handlers
pytest tests/unit/handlers/ -v

# Apenas testes de entidades
pytest tests/unit/entities/ -v

# Um arquivo específico
pytest tests/unit/locking/test_distributed_lock.py -v

# Um teste específico
pytest tests/unit/locking/test_distributed_lock.py::TestDistributedLock::test_lock_acquisition_success -v
```

### Executar com cobertura

```bash
# Cobertura completa
pytest tests/ --cov=src/sentinela --cov-report=html --cov-report=term

# Apenas mostrar no terminal
pytest tests/ --cov=src/sentinela --cov-report=term

# Gerar relatório HTML
pytest tests/ --cov=src/sentinela --cov-report=html
# Abrir: htmlcov/index.html
```

### Executar testes por categoria

```bash
# Apenas testes críticos (se marcados)
pytest tests/ -m critical -v

# Apenas testes unitários
pytest tests/unit/ -v

# Apenas testes de integração (quando houver)
pytest tests/integration/ -v
```

---

## 📊 Cobertura de Testes

### Meta de cobertura

| Componente | Meta | Atual |
|------------|------|-------|
| Handlers | 90%+ | ⏳ Em progresso |
| Use Cases | 85%+ | ⏳ Em progresso |
| Entities | 95%+ | ⏳ Em progresso |
| Services | 85%+ | ⏳ Em progresso |
| **Total** | **80%+** | ⏳ **Em progresso** |

### Verificar cobertura atual

```bash
# Gerar relatório de cobertura
pytest tests/ --cov=src/sentinela --cov-report=term-missing

# Ver quais linhas não estão cobertas
pytest tests/ --cov=src/sentinela --cov-report=term-missing | grep -A 100 "TOTAL"
```

---

## 🐛 Debugging de Testes

### Modo debug com pdb

```bash
# Entra no debugger quando teste falha
pytest tests/ --pdb

# Para no primeiro erro
pytest tests/ -x --pdb
```

### Ver output de print()

```bash
# Mostrar prints durante execução
pytest tests/ -s

# Mostrar prints apenas em testes que falharam
pytest tests/ --tb=short
```

### Ver logs detalhados

```bash
# Logs de nível DEBUG
pytest tests/ --log-cli-level=DEBUG

# Logs de nível INFO
pytest tests/ --log-cli-level=INFO
```

---

## ⚡ Testes Rápidos (Durante Desenvolvimento)

### Executar apenas testes que falharam

```bash
# Primeira execução
pytest tests/

# Executar apenas os que falharam
pytest --lf

# Executar os que falharam primeiro, depois os outros
pytest --ff
```

### Executar testes em paralelo (mais rápido)

```bash
# Instalar plugin
pip3 install pytest-xdist

# Executar com 4 workers
pytest tests/ -n 4

# Usar todos os cores disponíveis
pytest tests/ -n auto
```

---

## 🔧 Configuração Avançada

### Arquivo pytest.ini (opcional)

Criar na raiz do projeto:

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    critical: marca teste como crítico
    slow: marca teste como lento
    integration: marca teste de integração

# Configuração de cobertura
[coverage:run]
source = src/sentinela
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

### Marcadores de testes

```python
import pytest

# Marcar teste como crítico
@pytest.mark.critical
async def test_critical_feature():
    pass

# Marcar teste como lento
@pytest.mark.slow
async def test_slow_feature():
    pass

# Executar apenas críticos
# pytest tests/ -m critical
```

---

## 🚨 Troubleshooting

### Erro: "No module named pytest"

```bash
# Solução
pip3 install pytest pytest-asyncio
```

### Erro: "ImportError: cannot import name 'X'"

```bash
# Certifique-se de estar na raiz do projeto
cd /caminho/do/projeto

# Verifique se __init__.py existem
find src/ -name __init__.py

# Execute com PYTHONPATH
PYTHONPATH=. pytest tests/
```

### Erro: "fixture 'X' not found"

```bash
# Verifique se conftest.py existe
ls tests/conftest.py

# Verifique imports no conftest.py
cat tests/conftest.py
```

### Testes muito lentos

```bash
# Use paralelização
pip3 install pytest-xdist
pytest tests/ -n auto

# Ou execute apenas os modificados recentemente
pytest tests/ --lf
```

---

## 📝 Checklist Antes de Commit

Antes de fazer commit, execute:

```bash
# 1. Executar todos os testes
pytest tests/ -v

# 2. Verificar cobertura
pytest tests/ --cov=src/sentinela --cov-report=term

# 3. Verificar formatação (se configurado)
black src/ tests/
flake8 src/ tests/

# 4. Verificar tipos (se configurado)
mypy src/
```

---

## 🔄 Integração com CI/CD

Os testes são executados automaticamente no GitHub Actions a cada:
- Push para qualquer branch
- Pull Request
- Merge para main

Ver: `.github/workflows/tests.yml`

---

## 📚 Recursos

- [Documentação Pytest](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testes no README](../tests/README.md)

---

## 🆘 Suporte

- **Issues:** GitHub Issues do projeto
- **Logs:** Execute com `-v` ou `--log-cli-level=DEBUG`
- **Documentação:** Pasta `docs/`

---

**Última atualização:** 21/10/2025
