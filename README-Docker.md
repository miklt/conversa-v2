# Conversa Estágios - Docker Setup

Este guia mostra como executar o Conversa Estágios usando Docker.

## Pré-requisitos

- Docker e Docker Compose instalados
- Arquivo `.env` configurado (copie de `.env.example`)

## Configuração

1. **Copie o arquivo de configuração:**
```bash
cp .env.example .env
```

2. **Configure as variáveis no arquivo `.env`:**
   - `GEMINI_API_KEY`: Sua chave da API do Google Gemini
   - `ANTHROPIC_API_KEY`: Sua chave da API do Claude (Anthropic)
   - `OPENAI_API_KEY`: Sua chave da API do OpenAI
   - `SMTP_*`: Configurações de email para magic links
   - `SECRET_KEY`: Chave secreta para JWT (mínimo 32 caracteres)

## Executando com Docker

### Desenvolvimento

Para desenvolvimento, continue usando os comandos locais:

```bash
# Backend
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
```

### Produção com Docker

1. **Inicie todos os serviços:**
```bash
docker-compose up -d
```

2. **Verifique se os serviços estão rodando:**
```bash
docker-compose ps
```

3. **Acesse a aplicação:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - Documentação da API: http://localhost:8000/docs

### Comandos Úteis

**Ver logs:**
```bash
# Todos os serviços
docker-compose logs -f

# Serviço específico
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

**Parar os serviços:**
```bash
docker-compose down
```

**Parar e remover volumes (CUIDADO - apaga dados do banco):**
```bash
docker-compose down -v
```

**Rebuild das imagens:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

**Executar comandos no backend:**
```bash
# Acessar shell do container
docker-compose exec backend bash

# Executar migrações
docker-compose exec backend python -m backend.migrate

# Executar scripts
docker-compose exec backend python scripts/populate_terms.py
```

## Estrutura dos Serviços

- **postgres**: Banco de dados PostgreSQL com extensão pgvector
- **backend**: API FastAPI com autenticação JWT e magic links
- **frontend**: Interface React servida pelo nginx

## Volumes

- `postgres_data`: Dados persistentes do PostgreSQL

## Portas

- **80**: Frontend (nginx)
- **8000**: Backend (FastAPI)
- **5432**: PostgreSQL

## Troubleshooting

1. **Backend não conecta no banco:**
   - Verifique se o PostgreSQL está rodando: `docker-compose logs postgres`
   - Aguarde o healthcheck: `docker-compose ps`

2. **Frontend não carrega:**
   - Verifique se o build foi bem-sucedido: `docker-compose logs frontend`
   - Verify se o nginx está configurado corretamente

3. **Emails não são enviados:**
   - Verifique as configurações SMTP no `.env`
   - Teste com um serviço de email válido

4. **Rebuild completo:**
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```