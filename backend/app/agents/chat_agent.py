"""
Pydantic AI Agent for Chat System
"""
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from backend.app.db.database import get_db
from backend.app.schemas.schemas import ChatResponse
from backend.app.services.privacy_filter import PrivacyFilter
from backend.app.models.models import Relatorio, RelatorioTermo, TermoTecnico


class QueryIntent(BaseModel):
    """Intent extracted from user query"""
    query_type: str = Field(description="Type of query: technology, company, statistics, general")
    focus: Optional[str] = Field(description="Specific focus: programming_language, framework, etc.")
    year: Optional[int] = Field(description="Year filter if mentioned")
    keywords: List[str] = Field(description="Technical keywords mentioned")


class DBQueryResult(BaseModel):
    """Result from database query"""
    data: List[Dict[str, Any]] = Field(description="Query results")
    total_count: int = Field(description="Total number of records")


# Initialize the agent with OpenAI model
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    from pydantic_ai.models.test import TestModel
    model = TestModel()
else:
    model = OpenAIModel('gpt-4o-mini', api_key=api_key)

agent = Agent(
    model,
    system_prompt="""
    You are a helpful assistant that answers questions about internship reports from Electrical Engineering students.
    You have access to a database with internship data and can query it to provide accurate information.

    Available data:
    - Internship reports with company info, activities, technologies used
    - Technical terms categorized by type (LINGUAGEM, FRAMEWORK, FERRAMENTA, etc.)
    - Report-term relationships showing which technologies were used in each report

    When answering:
    - Always be factual and base answers on the data
    - Respect privacy - never reveal personal information
    - Provide context and sources when possible
    - Use the available tools to query the database
    - Format responses clearly and helpfully
    """
)


async def get_top_technologies(db: Session, tipo: str, year: Optional[int] = None, limit: int = 10) -> DBQueryResult:
    """Get top technologies by type and optionally filtered by year"""
    # Map user-friendly types to database enum values
    type_mapping = {
        'linguagem': 'LINGUAGEM',
        'linguagens': 'LINGUAGEM',
        'programming': 'LINGUAGEM',
        'language': 'LINGUAGEM',
        'framework': 'FRAMEWORK',
        'frameworks': 'FRAMEWORK',
        'ferramenta': 'FERRAMENTA',
        'ferramentas': 'FERRAMENTA',
        'tool': 'FERRAMENTA',
        'tools': 'FERRAMENTA',
        'plataforma': 'PLATAFORMA',
        'plataformas': 'PLATAFORMA',
        'platform': 'PLATAFORMA',
        'platforms': 'PLATAFORMA',
        'banco_dados': 'BANCO_DADOS',
        'banco': 'BANCO_DADOS',
        'database': 'BANCO_DADOS'
    }

    db_tipo = type_mapping.get(tipo.lower(), tipo.upper())

    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = " AND ".join(filters) if filters else "1=1"

    sql = f"""
        SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
        FROM relatorio_termos rt
        JOIN termos_tecnicos tt ON tt.id = rt.termo_id
        JOIN relatorios r ON r.id = rt.relatorio_id
        WHERE tt.tipo = :tipo AND {where_clause}
        GROUP BY tt.termo_normalizado
        ORDER BY count DESC
        LIMIT :limit
    """

    params.update({'tipo': db_tipo, 'limit': limit})

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{'technology': row[0], 'count': row[1]} for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def get_top_companies(db: Session, year: Optional[int] = None, limit: int = 10) -> DBQueryResult:
    """Get companies with most interns, optionally filtered by year with name normalization"""
    filters = []
    params = {}

    if year:
        filters.append("ano = :year")
        params['year'] = year

    where_clause = " AND ".join(filters) if filters else "1=1"

    # Query with company name normalization using SQL CASE statements
    sql = f"""
        SELECT
            CASE
                WHEN empresa_razao_social ILIKE '%btg pactual%' THEN 'BANCO BTG PACTUAL S.A.'
                WHEN empresa_razao_social ILIKE '%btg%' THEN 'BANCO BTG PACTUAL S.A.'
                WHEN empresa_razao_social ILIKE '%cip%' THEN 'CIP - CENTRO DE INFORMAÇÃO E PROCESSAMENTO'
                WHEN empresa_razao_social ILIKE '%centro de informação%' THEN 'CIP - CENTRO DE INFORMAÇÃO E PROCESSAMENTO'
                WHEN empresa_razao_social ILIKE '%virtual cirurgia%' THEN 'VIRTUAL CIRURGIA'
                WHEN empresa_razao_social ILIKE '%virtual%' THEN 'VIRTUAL CIRURGIA'
                ELSE empresa_razao_social
            END as normalized_company,
            COUNT(*) as count
        FROM relatorios
        WHERE empresa_razao_social IS NOT NULL AND {where_clause}
        GROUP BY normalized_company
        ORDER BY count DESC
        LIMIT :limit
    """

    params['limit'] = limit

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{'company': row[0], 'count': row[1]} for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def search_reports_by_technology(db: Session, technology: str, year: Optional[int] = None, limit: int = 5) -> DBQueryResult:
    """Find reports that mention a specific technology"""
    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = " AND ".join(filters) if filters else "1=1"

    sql = f"""
        SELECT DISTINCT r.empresa_razao_social, r.ano, r.periodo, r.ano_academico
        FROM relatorios r
        JOIN relatorio_termos rt ON r.id = rt.relatorio_id
        JOIN termos_tecnicos tt ON tt.id = rt.termo_id
        WHERE tt.termo_normalizado ILIKE :tech AND {where_clause}
        ORDER BY r.ano DESC, r.empresa_razao_social
        LIMIT :limit
    """

    params.update({'tech': f'%{technology}%', 'limit': limit})

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{
        'company': row[0],
        'year': row[1],
        'period': row[2],
        'academic_year': row[3]
    } for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def get_total_reports_count(db: Session, year: Optional[int] = None) -> int:
    """Get total number of reports, optionally filtered by year"""
    if year:
        count = db.query(func.count(Relatorio.id)).filter(Relatorio.ano == year).scalar()
    else:
        count = db.query(func.count(Relatorio.id)).scalar()

    return count


async def process_chat_message(message: str, db: Session) -> ChatResponse:
    """Process a chat message using database queries directly"""
    try:
        # Simple keyword-based routing for now
        message_lower = message.lower()

        if 'linguagem' in message_lower or 'programação' in message_lower or 'language' in message_lower:
            # Get top programming languages
            result = await get_top_technologies(db, 'LINGUAGEM', limit=5)
            if result.data:
                response_text = "As linguagens de programação mais utilizadas são:\n"
                for i, item in enumerate(result.data[:5], 1):
                    response_text += f"{i}. {item['technology'].title()} ({item['count']} relatórios)\n"
                return ChatResponse(response=response_text, confidence=0.9)

        elif 'empresa' in message_lower or 'company' in message_lower:
            # Get top companies
            result = await get_top_companies(db, limit=5)
            if result.data:
                response_text = "As empresas com mais estagiários são:\n"
                for i, item in enumerate(result.data[:5], 1):
                    response_text += f"{i}. {item['company']} ({item['count']} estagiários)\n"
                return ChatResponse(response=response_text, confidence=0.9)

        elif 'framework' in message_lower:
            # Get top frameworks
            result = await get_top_technologies(db, 'FRAMEWORK', limit=5)
            if result.data:
                response_text = "Os frameworks mais utilizados são:\n"
                for i, item in enumerate(result.data[:5], 1):
                    response_text += f"{i}. {item['technology'].title()} ({item['count']} relatórios)\n"
                return ChatResponse(response=response_text, confidence=0.9)

        # Default fallback
        return ChatResponse(
            response="Desculpe, não entendi sua pergunta. Você pode perguntar sobre:\n"
                    "- Linguagens de programação mais usadas\n"
                    "- Empresas que oferecem mais estágios\n"
                    "- Frameworks mais populares\n"
                    "- Estatísticas gerais",
            confidence=0.3
        )

    except Exception as e:
        print(f"Error in process_chat_message: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(
            response="Desculpe, houve um erro ao processar sua pergunta. Tente novamente.",
            confidence=0.1
        )