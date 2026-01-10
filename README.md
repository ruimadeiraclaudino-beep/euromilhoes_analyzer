# EuroMilhões Analyzer 🎱⭐

[![CI](https://github.com/rmadeira/euromilhoes_analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/rmadeira/euromilhoes_analyzer/actions/workflows/ci.yml)
[![Docker](https://github.com/rmadeira/euromilhoes_analyzer/actions/workflows/docker.yml/badge.svg)](https://github.com/rmadeira/euromilhoes_analyzer/actions/workflows/docker.yml)
[![codecov](https://codecov.io/gh/rmadeira/euromilhoes_analyzer/branch/main/graph/badge.svg)](https://codecov.io/gh/rmadeira/euromilhoes_analyzer)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 4.2](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Aplicação Django para análise estatística dos resultados do EuroMilhões.

## ⚠️ Aviso Importante

Cada sorteio do EuroMilhões é um **evento independente**. Os números não têm "memória" — um número que saiu muitas vezes não tem maior nem menor probabilidade de sair no próximo sorteio. Esta aplicação é para **análise exploratória, fins educacionais e entretenimento**.

## Funcionalidades

- 📊 **Dashboard** com resumo das estatísticas
- 📈 **Análise de frequência** de números e estrelas
- 🔥 **Números quentes/frios** - os mais e menos frequentes
- ⏰ **Números atrasados** - há mais tempo sem sair
- 📉 **Análise de distribuição** - pares/ímpares, baixos/altos, somas
- 🎲 **Gerador de apostas** com múltiplas estratégias
- 📅 **Histórico completo** de sorteios

## Instalação

### Opção 1: Docker (Recomendado) 🐳

```bash
# Setup completo com um comando
make init

# Ou passo a passo:
docker-compose up -d web
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py importar_sorteios --fonte csv --ficheiro dados_exemplo.csv --atualizar-stats
```

Acede a: http://localhost:8001

**Comandos Docker úteis:**
```bash
make help          # Ver todos os comandos
make up            # Iniciar (SQLite)
make up-mysql      # Iniciar com MySQL
make down          # Parar
make logs          # Ver logs
make shell         # Entrar no container
make import        # Importar dados exemplo
make stats         # Atualizar estatísticas
make superuser     # Criar admin
```

### Opção 2: Instalação Local

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar base de dados

Por defeito, usa SQLite. Para MySQL (como no InvestTracker), edita `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'euromilhoes_db',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 4. Executar migrações

```bash
python manage.py migrate
```

### 5. Criar superutilizador (opcional)

```bash
python manage.py createsuperuser
```

## Importar Dados

### Opção 1: Ficheiro CSV

Prepara um ficheiro CSV com o seguinte formato:

```csv
data,n1,n2,n3,n4,n5,e1,e2,jackpot,vencedor
2024-01-02,5,12,23,34,45,3,8,130000000,0
2024-01-05,7,15,28,39,48,2,11,17000000,1
```

Importar:

```bash
python manage.py importar_sorteios --fonte csv --ficheiro dados.csv --atualizar-stats
```

### Opção 2: Inserção manual

```bash
python manage.py importar_sorteios --fonte manual
```

Formato: `AAAA-MM-DD n1 n2 n3 n4 n5 e1 e2`

Exemplo: `2024-01-02 5 12 23 34 45 3 8`

### Opção 3: Datasets prontos

Podes encontrar dados históricos em:
- [Kaggle - EuroMillions](https://www.kaggle.com/search?q=euromillions)
- [Euro-Millions.com](https://www.euro-millions.com/results-history)

## Atualizar Estatísticas

Após importar novos sorteios:

```bash
python manage.py atualizar_estatisticas
```

## Executar

```bash
python manage.py runserver
```

Acede a: http://127.0.0.1:8000

## Estrutura do Projeto

```
euromilhoes_analyzer/
├── manage.py
├── requirements.txt
├── euromilhoes_analyzer/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── sorteios/
    ├── models.py          # Modelos de dados
    ├── views.py           # Views e API
    ├── services.py        # Lógica de análise
    ├── admin.py           # Admin Django
    ├── urls.py            # URLs da app
    ├── management/
    │   └── commands/
    │       ├── importar_sorteios.py
    │       └── atualizar_estatisticas.py
    └── templates/
        └── sorteios/
            ├── base.html
            ├── dashboard.html
            └── ...
```

## API REST

A aplicação disponibiliza uma API REST completa com autenticação por token.

### Endpoints Públicos (GET)

| Endpoint | Descrição |
|----------|-----------|
| `/api/` | Lista todos os endpoints |
| `/api/sorteios/` | Lista sorteios (paginado) |
| `/api/sorteios/{id}/` | Detalhe de um sorteio |
| `/api/sorteios/ultimo/` | Último sorteio |
| `/api/estatisticas/` | Estatísticas gerais |
| `/api/estatisticas/numeros/` | Estatísticas de números |
| `/api/estatisticas/numeros/quentes/` | Top números quentes |
| `/api/estatisticas/estrelas/` | Estatísticas de estrelas |

### Endpoints Autenticados (POST)

| Endpoint | Descrição |
|----------|-----------|
| `/api/apostas/gerar/` | Gerar nova aposta |
| `/api/verificar/` | Verificar aposta |
| `/api/auth/login/` | Login (obter token) |
| `/api/auth/register/` | Registar utilizador |
| `/api/auth/logout/` | Logout |

### Exemplo de Uso

```bash
# Login
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Gerar aposta (com token)
curl -X POST http://localhost:8001/api/apostas/gerar/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{"estrategia": "mista"}'
```

## Estratégias de Geração

| Estratégia | Descrição |
|------------|-----------|
| `frequencia` | Favorece números mais frequentes |
| `frios` | Favorece números menos frequentes |
| `equilibrada` | Equilibra pares/ímpares, baixos/altos |
| `aleatorio` | Seleção completamente aleatória |
| `mista` | Combina quentes, frios e atrasados |

## Testes

A aplicação inclui 68 testes automatizados com cobertura de código.

```bash
# Executar testes
make test

# Testes com cobertura
make coverage

# Relatório HTML
make coverage-html
```

### Estrutura de Testes

```
sorteios/tests/
├── test_models.py          # Testes de modelos
├── test_api_sorteios.py    # Testes API sorteios
├── test_api_estatisticas.py # Testes API estatísticas
├── test_api_apostas.py     # Testes API apostas
└── test_auth.py            # Testes autenticação
```

## CI/CD

O projeto usa GitHub Actions para integração contínua:

- **CI**: Testes, linting e verificação de segurança em cada push/PR
- **Docker**: Build automático de imagens Docker
- **Release**: Criação automática de releases com changelog

### Workflows

| Workflow | Trigger | Descrição |
|----------|---------|-----------|
| `ci.yml` | push, PR | Testes, coverage, linting |
| `docker.yml` | push main, tags | Build e push de imagens |
| `release.yml` | tags v* | Criação de releases |

## Tecnologias

- **Backend**: Django 4.2+, Django REST Framework
- **Frontend**: Bootstrap 5, Chart.js
- **BD**: SQLite (dev) / MySQL (prod)
- **Análise**: NumPy, Pandas, SciPy
- **Testes**: Django Test, Coverage
- **CI/CD**: GitHub Actions, Docker

## Próximos Passos Sugeridos

1. Adicionar web scraping automático para novos sorteios
2. Implementar notificações de novos resultados
3. Adicionar mais visualizações (heatmaps, tendências)
4. Criar modo de comparação de estratégias
5. Exportar apostas para PDF

---

**Joga com responsabilidade!** 🍀
