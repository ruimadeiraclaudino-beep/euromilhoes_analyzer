# EuroMilhoes Analyzer

[![CI](https://github.com/ruimadeiraclaudino-beep/euromilhoes_analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/ruimadeiraclaudino-beep/euromilhoes_analyzer/actions/workflows/ci.yml)
[![Docker](https://github.com/ruimadeiraclaudino-beep/euromilhoes_analyzer/actions/workflows/docker.yml/badge.svg)](https://github.com/ruimadeiraclaudino-beep/euromilhoes_analyzer/actions/workflows/docker.yml)
[![codecov](https://codecov.io/gh/ruimadeiraclaudino-beep/euromilhoes_analyzer/branch/main/graph/badge.svg)](https://codecov.io/gh/ruimadeiraclaudino-beep/euromilhoes_analyzer)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 4.2](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Aplicacao Django para analise estatistica dos resultados do EuroMilhoes.

## Aviso Importante

Cada sorteio do EuroMilhoes e um **evento independente**. Os numeros nao tem "memoria" - um numero que saiu muitas vezes nao tem maior nem menor probabilidade de sair no proximo sorteio. Esta aplicacao e para **analise exploratoria, fins educacionais e entretenimento**.

## Funcionalidades

### Analise Estatistica
- **Dashboard** com resumo das estatisticas
- **Analise de frequencia** de numeros e estrelas
- **Numeros quentes/frios** - os mais e menos frequentes
- **Numeros atrasados** - ha mais tempo sem sair
- **Analise de distribuicao** - pares/impares, baixos/altos, somas
- **Historico completo** de sorteios

### Analise de Padroes (v2.0)
- **Numeros consecutivos** - detecao e estatisticas
- **Distribuicao por dezenas** - analise 1-10, 11-20, etc.
- **Terminacoes** - frequencia do ultimo digito
- **Sequencias** - pares e trios mais comuns
- **Tendencias de soma** - evolucao ao longo do tempo

### Previsoes ML (v2.0) - Experimental
- **Modelo de scoring** baseado em multiplos fatores
- **Estrategias**: frequencia, atraso, tendencia, equilibrada
- **Rankings** de numeros e estrelas com scores
- **Analise de precisao** historica

### Graficos Avancados (v2.0)
- **Heatmaps de frequencia** - grid 10x5 para numeros
- **Heatmap de atraso** - dias sem sair por numero
- **Tendencias temporais** - evolucao de somas
- **Pares vs Impares** - grafico temporal
- **Distribuicao de somas** - histograma
- **Evolucao de frequencia** - comparar multiplos numeros
- **Frequencia por ano** - top 10 numeros

### Gerador de Apostas
- **5 estrategias** de geracao
- **Multiplas apostas** de uma vez
- **Historico** de apostas geradas

### Interface
- **Modo Escuro** (v2.0) - toggle na navbar com persistencia
- **Design responsivo** - Bootstrap 5
- **Graficos interativos** - Chart.js

## Instalacao

### Opcao 1: Docker (Recomendado)

```bash
# Setup completo com um comando
make init

# Ou passo a passo:
docker-compose up -d web
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py importar_sorteios --fonte csv --ficheiro dados_exemplo.csv --atualizar-stats
```

Acede a: http://localhost:8001

**Comandos Docker uteis:**
```bash
make help          # Ver todos os comandos
make up            # Iniciar (SQLite)
make up-mysql      # Iniciar com MySQL
make down          # Parar
make logs          # Ver logs
make shell         # Entrar no container
make import        # Importar dados exemplo
make stats         # Atualizar estatisticas
make superuser     # Criar admin
```

### Opcao 2: Instalacao Local

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar base de dados

Por defeito, usa SQLite. Para MySQL, edita `settings.py`:

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

### 4. Executar migracoes

```bash
python manage.py migrate
```

### 5. Criar superutilizador (opcional)

```bash
python manage.py createsuperuser
```

## Importar Dados

### Opcao 1: Ficheiro CSV

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

### Opcao 2: Insercao manual

```bash
python manage.py importar_sorteios --fonte manual
```

Formato: `AAAA-MM-DD n1 n2 n3 n4 n5 e1 e2`

Exemplo: `2024-01-02 5 12 23 34 45 3 8`

### Opcao 3: Datasets prontos

Podes encontrar dados historicos em:
- [Kaggle - EuroMillions](https://www.kaggle.com/search?q=euromillions)
- [Euro-Millions.com](https://www.euro-millions.com/results-history)

## Atualizar Estatisticas

Apos importar novos sorteios:

```bash
python manage.py atualizar_estatisticas
```

## Executar

```bash
python manage.py runserver
```

Acede a: http://127.0.0.1:8000

## Paginas Disponiveis

| Pagina | URL | Descricao |
|--------|-----|-----------|
| Dashboard | `/` | Resumo geral das estatisticas |
| Historico | `/sorteios/` | Lista de todos os sorteios |
| Numeros | `/estatisticas/numeros/` | Estatisticas detalhadas dos numeros |
| Estrelas | `/estatisticas/estrelas/` | Estatisticas das estrelas |
| Distribuicao | `/analise/` | Analise de distribuicao |
| Padroes | `/padroes/` | Analise de padroes (v2.0) |
| Graficos | `/graficos/` | Graficos avancados (v2.0) |
| Previsao ML | `/previsao/` | Previsoes experimentais (v2.0) |
| Gerador | `/gerador/` | Gerador de apostas |

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
    ├── services.py        # Logica de analise e padroes
    ├── ml.py              # Previsoes ML (v2.0)
    ├── serializers.py     # Serializadores DRF
    ├── api.py             # ViewSets da API REST
    ├── auth.py            # Autenticacao
    ├── admin.py           # Admin Django
    ├── urls.py            # URLs da app
    ├── management/
    │   └── commands/
    │       ├── importar_sorteios.py
    │       └── atualizar_estatisticas.py
    ├── templates/
    │   └── sorteios/
    │       ├── base.html              # Template base com modo escuro
    │       ├── dashboard.html
    │       ├── analise_padroes.html   # Padroes (v2.0)
    │       ├── graficos_avancados.html # Graficos (v2.0)
    │       ├── previsao_ml.html       # ML (v2.0)
    │       └── ...
    └── tests/
        ├── test_models.py
        ├── test_api_sorteios.py
        ├── test_api_estatisticas.py
        ├── test_api_apostas.py
        ├── test_auth.py
        └── test_padroes_ml.py         # Testes v2.0
```

## API REST

A aplicacao disponibiliza uma API REST completa com autenticacao por token.

### Endpoints Publicos (GET)

| Endpoint | Descricao |
|----------|-----------|
| `/api/` | Lista todos os endpoints |
| `/api/sorteios/` | Lista sorteios (paginado) |
| `/api/sorteios/{id}/` | Detalhe de um sorteio |
| `/api/sorteios/ultimo/` | Ultimo sorteio |
| `/api/estatisticas/` | Estatisticas gerais |
| `/api/estatisticas/numeros/` | Estatisticas de numeros |
| `/api/estatisticas/numeros/quentes/` | Top numeros quentes |
| `/api/estatisticas/estrelas/` | Estatisticas de estrelas |

### Endpoints de Padroes e ML (v2.0)

| Endpoint | Descricao |
|----------|-----------|
| `/api/padroes/` | Analise completa de padroes |
| `/api/ml/previsao/` | Previsao ML (query: `estrategia`) |
| `/api/ml/ranking/` | Ranking de numeros e estrelas |
| `/api/ml/precisao/` | Analise de precisao historica |

### Endpoints de Graficos (v2.0)

| Endpoint | Descricao |
|----------|-----------|
| `/api/graficos/evolucao/` | Evolucao de frequencia (query: `numero`) |
| `/api/graficos/heatmap-mensal/` | Heatmap mensal |
| `/api/graficos/correlacao/` | Matriz de correlacao |

### Endpoints Autenticados (POST)

| Endpoint | Descricao |
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

# Obter previsao ML
curl http://localhost:8001/api/ml/previsao/?estrategia=equilibrada

# Analise de padroes
curl http://localhost:8001/api/padroes/
```

## Estrategias de Geracao

| Estrategia | Descricao |
|------------|-----------|
| `frequencia` | Favorece numeros mais frequentes |
| `frios` | Favorece numeros menos frequentes |
| `equilibrada` | Equilibra pares/impares, baixos/altos |
| `aleatorio` | Selecao completamente aleatoria |
| `mista` | Combina quentes, frios e atrasados |

## Testes

A aplicacao inclui **92 testes** automatizados com cobertura de codigo.

```bash
# Executar testes
make test

# Testes com cobertura
make coverage

# Relatorio HTML
make coverage-html
```

### Estrutura de Testes

```
sorteios/tests/
├── test_models.py           # Testes de modelos
├── test_api_sorteios.py     # Testes API sorteios
├── test_api_estatisticas.py # Testes API estatisticas
├── test_api_apostas.py      # Testes API apostas
├── test_auth.py             # Testes autenticacao
└── test_padroes_ml.py       # Testes padroes, ML e graficos (v2.0)
```

## CI/CD

O projeto usa GitHub Actions para integracao continua:

- **CI**: Testes, linting e verificacao de seguranca em cada push/PR
- **Docker**: Build automatico de imagens Docker
- **Release**: Criacao automatica de releases com changelog

### Workflows

| Workflow | Trigger | Descricao |
|----------|---------|-----------|
| `ci.yml` | push, PR | Testes, coverage, linting |
| `docker.yml` | push main, tags | Build e push de imagens |
| `release.yml` | tags v* | Criacao de releases |

### Docker Image

```bash
docker pull ghcr.io/ruimadeiraclaudino-beep/euromilhoes_analyzer:latest
```

## Tecnologias

- **Backend**: Django 4.2+, Django REST Framework
- **Frontend**: Bootstrap 5, Chart.js
- **BD**: SQLite (dev) / MySQL (prod)
- **Analise**: NumPy, Pandas, SciPy
- **Testes**: Django Test, Coverage (92 testes)
- **CI/CD**: GitHub Actions, Docker

## Changelog

### v2.0.0 (2025)
- Analise de padroes (consecutivos, dezenas, terminacoes, sequencias)
- Previsoes ML experimentais com multiplas estrategias
- Modo escuro com toggle e persistencia
- Graficos avancados (heatmaps, tendencias, evolucao)
- 24 novos testes (total: 92)
- Novos endpoints API

### v1.0.0 (2024)
- Release inicial
- Dashboard com estatisticas
- API REST com autenticacao
- Gerador de apostas
- CI/CD com GitHub Actions
- 68 testes automatizados

## Proximos Passos Sugeridos

1. Adicionar web scraping automatico para novos sorteios
2. Implementar notificacoes de novos resultados
3. Criar modo de comparacao de estrategias
4. Exportar apostas para PDF
5. App mobile (React Native / Flutter)

---

**Joga com responsabilidade!**
