# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a conversational system that allows users to query and analyze internship reports from the Electrical Engineering (Computer Emphasis) program at USP. Users can ask questions about projects, companies, and internships while the system restricts access to personal information.

**Key Features:**
- Natural language queries about internship data
- Aggregated insights (most used programming languages, common project types, etc.)
- Privacy-preserving responses (no personal data disclosure)
- Vector-based semantic search for relevant information retrieval

## Current State

✅ **Completed:**
- PDF to JSON extraction pipeline (ETL scripts)
- 74 internship reports imported and structured in PostgreSQL
- Database with pgvector extension for semantic search
- 755 technical term relationships extracted and normalized
- FastAPI backend with working endpoints:
  - Chat interface for natural language queries
  - Report search with term-based filtering
  - Statistics and aggregations
- Privacy filters implemented to protect personal data
- Vector embeddings generated and stored (ready for semantic search)

🚧 **To Be Developed:**
- Frontend chat interface (React/Vite)
- Enhanced query processing with LLM integration
- Real-time chat session management

## Important Data Conventions

### Courses
Only two possible courses:
- `Engenharia de Computação` (quadrimestral system)
- `Engenharia Elétrica` (semestral system)

### Academic Periods
- **Semestral**: `1S` (1st semester) or `2S` (2nd semester)
- **Quadrimestral**: `1Q`, `2Q`, or `3Q` (1st, 2nd, or 3rd quarter)

### Academic Years
Possible values: `2°`, `3°`, `4°`, `5°` (2nd through 5th year)

### Folder Structure Convention
JSON files are organized in folders with naming pattern:
```
{ano}-{periodo}-{ano_academico}roAno-{ordinal_estagio}
```
Example: `2025-2Q-3roAno-1` means:
- `ano`: 2025 (calendar year)
- `periodo`: 2Q (2nd quarter)
- `ano_academico`: 3° (3rd academic year)
- `ordinal_estagio`: 1 (first internship)

## Development Plan & Checklist

### Phase 1: Database Setup ✅

- [x] Install PostgreSQL and pgvector extension
- [x] Create database schema:
  - [x] `relatorios` table (main reports table)
  - [x] `relatorio_embeddings` table (vector embeddings)
  - [x] `termos_tecnicos` table (normalized technical terms)
  - [x] `relatorio_termos` table (many-to-many relationship)
- [x] Write database migration scripts
- [x] Create database connection utilities
- [x] Test database setup with integration tests

### Phase 2: Data Ingestion & Processing ✅

- [x] Create script to import existing JSON files into database
- [x] Extract metadata (year from dates, course type)
- [x] Generate embeddings for report sections:
  - [x] `sobre_empresa`
  - [x] `atividades_realizadas`
  - [x] `conclusao`
- [x] Populate `termos_tecnicos` table with normalized terms
- [x] Create term extraction and mapping logic
- [x] Test data ingestion pipeline with integration tests

### Phase 3: Backend API Development ✅

- [x] Set up FastAPI project structure
- [x] Create database models with SQLAlchemy
- [x] Implement core endpoints:
  - [x] `POST /api/v1/chat` - Process user queries
  - [x] `POST /api/v1/reports/search` - Term-based search
  - [x] `GET /api/v1/reports/{id}` - Get specific report (filtered)
  - [x] `POST /api/v1/stats` - Get statistics by metric
  - [x] `GET /api/v1/stats/summary` - Summary statistics
- [x] Implement privacy filters (remove personal data)
- [x] Create query processing pipeline:
  - [x] Parse user intent
  - [x] Generate relevant database queries
  - [x] Format responses with context
- [x] Test all API endpoints

### Phase 4: Frontend Development ⏳

- [ ] Initialize React + Vite project
- [ ] Create chat UI components:
  - [ ] Message input
  - [ ] Message history
  - [ ] Typing indicators
- [ ] Implement API client for backend communication
- [ ] Add response formatting and markdown support
- [ ] Create loading and error states

### Phase 5: Testing & Refinement ⏳

- [ ] Create test dataset with known queries/answers
- [ ] Implement integration tests
- [ ] Test privacy filters thoroughly
- [ ] Optimize embedding generation and search
- [ ] Fine-tune response generation

## Database Schema

### Main Tables

```sql
-- Reports table
CREATE TABLE relatorios (
    id SERIAL PRIMARY KEY,
    json_completo JSONB NOT NULL,
    ano INTEGER NOT NULL, -- Calendar year (2024, 2025, etc)
    periodo VARCHAR(2) NOT NULL, -- 1S, 2S, 1Q, 2Q, 3Q
    ano_academico VARCHAR(2) NOT NULL, -- 2°, 3°, 4°, 5°
    ordinal_estagio INTEGER CHECK (ordinal_estagio BETWEEN 1 AND 5),
    curso VARCHAR(30) CHECK (curso IN ('Engenharia de Computação', 'Engenharia Elétrica')),
    empresa_razao_social VARCHAR(255),
    folder_origin VARCHAR(100), -- Original folder name for tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings table
CREATE TABLE relatorio_embeddings (
    id SERIAL PRIMARY KEY,
    relatorio_id INTEGER REFERENCES relatorios(id),
    secao VARCHAR(50), -- 'sobre_empresa', 'atividades', 'conclusao'
    conteudo TEXT,
    embedding vector(1536), -- Assuming OpenAI embeddings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Technical terms normalization
CREATE TABLE termos_tecnicos (
    id SERIAL PRIMARY KEY,
    termo VARCHAR(100),
    tipo VARCHAR(50), -- 'linguagem', 'framework', 'ferramenta', etc.
    termo_normalizado VARCHAR(100)
);

-- Many-to-many relationship
CREATE TABLE relatorio_termos (
    relatorio_id INTEGER REFERENCES relatorios(id),
    termo_id INTEGER REFERENCES termos_tecnicos(id),
    frequencia INTEGER DEFAULT 1,
    PRIMARY KEY (relatorio_id, termo_id)
);
```

## Common Development Commands

### Environment Setup

```bash
# Activate virtual environment
source /home/m/pcs/conversa-estagios/backend/env/bin/activate

# Install current dependencies
pip install -r requirements.txt

# Install additional dependencies for the full system
pip install fastapi uvicorn sqlalchemy psycopg2-binary pgvector openai pydantic
```

### Database Operations

```bash
# Start PostgreSQL (if using Docker)
docker run --name conversa-postgres -e POSTGRES_PASSWORD=senha -p 5432:5432 -d postgres:15

# Install pgvector extension
docker exec -it conversa-postgres psql -U postgres -c "CREATE EXTENSION vector;"

# Run migrations (when available)
python backend/migrate.py
```

### Backend Development

```bash
# Start FastAPI development server
cd backend && python -m uvicorn main:app --reload --port 8000

# Access API documentation
# http://localhost:8000/docs - Swagger UI
# http://localhost:8000/redoc - ReDoc

# Test API endpoints
# Chat endpoint
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual a linguagem mais usada em 2025?"}'

# Statistics endpoint  
curl -X POST http://localhost:8000/api/v1/stats/ \
  -H "Content-Type: application/json" \
  -d '{"metric": "top_technologies", "filters": {"year": 2025}}'

# Run tests
pytest backend/tests/
```

### Frontend Development

```bash
# Initialize Vite project (first time only)
npm create vite@latest frontend -- --template react-ts

# Install dependencies
cd frontend && npm install

# Start development server
npm run dev
```

## Key Implementation Details

### Query Processing Flow

1. **User Query** → Parse intent and extract key terms
2. **Vector Search** → Find relevant report sections using embeddings
3. **Filter & Aggregate** → Apply privacy filters and aggregate data
4. **Response Generation** → Format natural language response with context

### Privacy Implementation

```python
# Example privacy filter
def filter_personal_data(report_data):
    filtered = report_data.copy()
    if 'estagiario' in filtered:
        filtered['estagiario'] = {
            'curso': report_data['estagiario'].get('curso'),
            # Remove: nome_completo, nusp, telefone, email
        }
    if 'supervisor' in filtered:
        del filtered['supervisor']  # Remove all supervisor data
    return filtered
```

### Example Queries & Expected Behavior

- **"Qual a linguagem mais usada em 2025?"**
  - Search embeddings for technology mentions
  - Aggregate by normalized terms
  - Return ranked list

- **"Quais empresas oferecem estágios em backend?"**
  - Search for "backend" in activities
  - Group by company
  - Return company list without personal data

## Current Data Statistics

### Database Content (as of December 2024):
- **74 internship reports** from 2025
- **35 different companies** (BTG Pactual leading with 33 reports)
- **755 technical term relationships** extracted
- **134 normalized technical terms** in the database
- **Top technologies mentioned:**
  - API (35 reports)
  - AWS (31 reports)
  - Python (30 reports)
  - Backend (27 reports)
  - SQL (26 reports)

### Embeddings Status:
- **3 vector embeddings** stored and ready for similarity search
- Model used: OpenAI text-embedding-3-small
- Dimension: 1536
- To generate more embeddings: `python scripts/generate_embeddings.py`

## API Usage Examples

### Chat Queries
```bash
# Ask about programming languages
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Quais as linguagens de programação mais usadas?"}'

# Ask about companies
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Quais empresas oferecem mais estágios?"}'
```

### Search Reports
```bash
# Search for Python backend positions
curl -X POST http://localhost:8000/api/v1/reports/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python backend", "limit": 5}'
```

### Get Statistics
```bash
# Top technologies
curl -X POST http://localhost:8000/api/v1/stats/ \
  -H "Content-Type: application/json" \
  -d '{"metric": "programming_languages", "filters": {"year": 2025}}'

# Summary statistics
curl http://localhost:8000/api/v1/stats/summary
```

## Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Database
DATABASE_URL=postgresql://conversa_user:conversa_senha_2024@localhost:5432/conversa_estagios

# Application
FASTAPI_ENV=development
CORS_ORIGINS=["http://localhost:5173"]
DEBUG=true
```

## Project Structure (Current)

```
conversa-estagios-v2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   └── services/
│   ├── tests/
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── App.tsx
│   └── package.json
├── scripts/
│   ├── import_json_to_db.py
│   ├── generate_embeddings.py
│   └── populate_terms.py
└── docker-compose.yml
```
