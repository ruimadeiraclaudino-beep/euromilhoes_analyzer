# Makefile para EuroMilhões Analyzer
# Uso: make <comando>

.PHONY: help build up down logs shell migrate import stats superuser clean

# Cores para output
GREEN := \033[0;32m
NC := \033[0m

help: ## Mostra esta ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

# === Docker Básico (SQLite) ===

build: ## Constrói a imagem Docker
	docker-compose build

up: ## Inicia os containers (SQLite)
	docker-compose up -d web
	@echo "$(GREEN)Aplicação disponível em: http://localhost:8001$(NC)"

down: ## Para os containers
	docker-compose down

logs: ## Mostra logs da aplicação
	docker-compose logs -f web

shell: ## Abre shell no container
	docker-compose exec web bash

# === Docker com MySQL ===

up-mysql: ## Inicia com MySQL
	docker-compose --profile mysql up -d
	@echo "$(GREEN)Aplicação disponível em: http://localhost:8001$(NC)"
	@echo "$(GREEN)MySQL disponível na porta: 3307$(NC)"

down-mysql: ## Para containers MySQL
	docker-compose --profile mysql down

logs-mysql: ## Logs do MySQL
	docker-compose --profile mysql logs -f

# === Comandos Django ===

migrate: ## Executa migrações
	docker-compose exec web python manage.py migrate

import: ## Importa dados de exemplo
	docker-compose exec web python manage.py importar_sorteios --fonte csv --ficheiro dados_exemplo.csv --atualizar-stats

stats: ## Atualiza estatísticas
	docker-compose exec web python manage.py atualizar_estatisticas

superuser: ## Cria superutilizador
	docker-compose exec web python manage.py createsuperuser

# === Testes ===

test: ## Executa todos os testes
	docker-compose exec web python manage.py test sorteios.tests -v2

test-fast: ## Executa testes (modo rápido)
	docker-compose exec web python manage.py test sorteios.tests

coverage: ## Executa testes com cobertura
	docker-compose exec web coverage run --source=sorteios manage.py test sorteios.tests
	docker-compose exec web coverage report
	@echo "$(GREEN)Para relatório HTML: make coverage-html$(NC)"

coverage-html: coverage ## Gera relatório HTML de cobertura
	docker-compose exec web coverage html
	@echo "$(GREEN)Relatório disponível em: htmlcov/index.html$(NC)"

# === Manutenção ===

clean: ## Remove containers, volumes e imagens
	docker-compose down -v --rmi local
	@echo "$(GREEN)Limpeza concluída!$(NC)"

restart: down up ## Reinicia a aplicação

# === Setup Inicial ===

init: build up migrate import ## Setup completo (build, up, migrate, import)
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)Setup concluído!$(NC)"
	@echo "$(GREEN)Acede a: http://localhost:8001$(NC)"
	@echo "$(GREEN)========================================$(NC)"
