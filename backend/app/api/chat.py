"""
Chat API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Dict, Any, List
import logging
import re

from backend.app.db.database import get_db
from backend.app.schemas.schemas import ChatRequest, ChatResponse
from backend.app.services.privacy_filter import PrivacyFilter
from backend.app.services.vector_search import VectorSearchService
from backend.app.models.models import Relatorio, RelatorioTermo, TermoTecnico

logger = logging.getLogger(__name__)

router = APIRouter()


def extract_query_intent(message: str) -> Dict[str, Any]:
    """
    Extract intent and entities from user message
    """
    intent = {
        'type': 'general',
        'entities': {},
        'keywords': []
    }
    
    message_lower = message.lower()
    
    # Detect query type
    if any(word in message_lower for word in ['linguagem', 'language', 'programação']):
        intent['type'] = 'technology'
        intent['focus'] = 'programming_language'
    elif any(word in message_lower for word in ['empresa', 'company', 'companhia']):
        intent['type'] = 'company'
    elif any(word in message_lower for word in ['framework', 'biblioteca', 'library']):
        intent['type'] = 'technology'
        intent['focus'] = 'framework'
    elif any(word in message_lower for word in ['mais usado', 'mais popular', 'mais comum', 'top']):
        intent['type'] = 'statistics'
    elif any(word in message_lower for word in ['projeto', 'atividade', 'trabalho']):
        intent['type'] = 'activities'
    
    # Extract year
    year_match = re.search(r'\b(202[0-9])\b', message)
    if year_match:
        intent['entities']['year'] = int(year_match.group(1))
    
    # Extract common technical terms
    tech_keywords = ['python', 'java', 'javascript', 'react', 'backend', 'frontend', 
                     'aws', 'docker', 'sql', 'api', 'machine learning', 'ai']
    
    for keyword in tech_keywords:
        if keyword in message_lower:
            intent['keywords'].append(keyword)
    
    return intent


def generate_statistics_response(db: Session, intent: Dict[str, Any]) -> ChatResponse:
    """
    Generate response for statistics queries
    """
    filters = []
    params = {}
    
    if 'year' in intent['entities']:
        filters.append("r.ano = :year")
        params['year'] = intent['entities']['year']
    
    where_clause = " AND ".join(filters) if filters else "1=1"
    
    # Get top technologies
    if intent.get('focus') == 'programming_language':
        sql = f"""
            SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
            FROM relatorio_termos rt
            JOIN termos_tecnicos tt ON tt.id = rt.termo_id
            JOIN relatorios r ON r.id = rt.relatorio_id
            WHERE tt.tipo = 'LINGUAGEM' AND {where_clause}
            GROUP BY tt.termo_normalizado
            ORDER BY count DESC
            LIMIT 10
        """
    elif intent.get('focus') == 'framework':
        sql = f"""
            SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
            FROM relatorio_termos rt
            JOIN termos_tecnicos tt ON tt.id = rt.termo_id
            JOIN relatorios r ON r.id = rt.relatorio_id
            WHERE tt.tipo = 'FRAMEWORK' AND {where_clause}
            GROUP BY tt.termo_normalizado
            ORDER BY count DESC
            LIMIT 10
        """
    else:
        # General technology statistics
        sql = f"""
            SELECT tt.termo_normalizado, tt.tipo, COUNT(DISTINCT rt.relatorio_id) as count
            FROM relatorio_termos rt
            JOIN termos_tecnicos tt ON tt.id = rt.termo_id
            JOIN relatorios r ON r.id = rt.relatorio_id
            WHERE {where_clause}
            GROUP BY tt.termo_normalizado, tt.tipo
            ORDER BY count DESC
            LIMIT 15
        """
    
    result = db.execute(text(sql), params)
    rows = result.fetchall()
    
    if not rows:
        return ChatResponse(
            response="Não encontrei dados suficientes para responder sua pergunta.",
            confidence=0.3
        )
    
    # Format response
    year_str = f"em {intent['entities']['year']}" if 'year' in intent['entities'] else "no período analisado"
    
    if intent.get('focus') == 'programming_language':
        top_items = [f"{row[0].title()} ({row[1]} relatórios)" for row in rows[:5]]
        response = f"As linguagens de programação mais utilizadas {year_str} foram:\n"
        response += "\n".join([f"{i+1}. {item}" for i, item in enumerate(top_items)])
    elif intent.get('focus') == 'framework':
        top_items = [f"{row[0].title()} ({row[1]} relatórios)" for row in rows[:5]]
        response = f"Os frameworks mais utilizados {year_str} foram:\n"
        response += "\n".join([f"{i+1}. {item}" for i, item in enumerate(top_items)])
    else:
        # Group by type
        by_type = {}
        for term, tipo, count in rows:
            if tipo not in by_type:
                by_type[tipo] = []
            by_type[tipo].append((term, count))
        
        response = f"Principais tecnologias mencionadas {year_str}:\n\n"
        
        type_names = {
            'LINGUAGEM': 'Linguagens',
            'FRAMEWORK': 'Frameworks',
            'FERRAMENTA': 'Ferramentas',
            'PLATAFORMA': 'Plataformas',
            'BANCO_DADOS': 'Bancos de Dados'
        }
        
        for tipo, items in list(by_type.items())[:3]:
            if tipo in type_names:
                response += f"**{type_names[tipo]}:**\n"
                top_3 = items[:3]
                response += ", ".join([f"{term.title()}" for term, _ in top_3])
                response += "\n\n"
    
    # Add sources info
    if filters:
        total_reports = db.execute(text(f"SELECT COUNT(*) FROM relatorios r WHERE {where_clause}"), params).scalar()
    else:
        total_reports = db.query(func.count(Relatorio.id)).scalar()
    response += f"\n_Baseado em {total_reports} relatórios de estágio._"
    
    return ChatResponse(
        response=response,
        confidence=0.85,
        sources=[{"total_reports": total_reports}]
    )


def generate_company_response(db: Session, intent: Dict[str, Any]) -> ChatResponse:
    """
    Generate response for company-related queries
    """
    filters = []
    params = {}
    
    if 'year' in intent['entities']:
        filters.append("ano = :year")
        params['year'] = intent['entities']['year']
    
    where_clause = " AND ".join(filters) if filters else "1=1"
    
    # Get top companies
    sql = f"""
        SELECT empresa_razao_social, COUNT(*) as count
        FROM relatorios
        WHERE empresa_razao_social IS NOT NULL AND {where_clause}
        GROUP BY empresa_razao_social
        ORDER BY count DESC
        LIMIT 10
    """
    
    result = db.execute(text(sql), params)
    rows = result.fetchall()
    
    if not rows:
        return ChatResponse(
            response="Não encontrei informações sobre empresas para o período especificado.",
            confidence=0.3
        )
    
    year_str = f"em {intent['entities']['year']}" if 'year' in intent['entities'] else ""
    
    response = f"As empresas com mais estagiários {year_str} foram:\n\n"
    for i, (company, count) in enumerate(rows[:5], 1):
        plural = "estagiário" if count == 1 else "estagiários"
        response += f"{i}. **{company}** - {count} {plural}\n"
    
    return ChatResponse(
        response=response,
        confidence=0.9
    )


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Process a chat message and return a response
    """
    try:
        # Extract intent from message
        intent = extract_query_intent(request.message)
        logger.info(f"Detected intent: {intent}")
        
        # Route to appropriate handler based on intent
        if intent['type'] == 'statistics':
            response = generate_statistics_response(db, intent)
        elif intent['type'] == 'technology':
            response = generate_statistics_response(db, intent)
        elif intent['type'] == 'company':
            response = generate_company_response(db, intent)
        else:
            # Default response for unhandled intents
            response = ChatResponse(
                response="Desculpe, ainda estou aprendendo a responder esse tipo de pergunta. "
                        "Você pode perguntar sobre:\n"
                        "- Linguagens e tecnologias mais usadas\n"
                        "- Empresas que oferecem estágios\n"
                        "- Tipos de projetos desenvolvidos\n"
                        "- Estatísticas por ano ou período",
                confidence=0.2
            )
        
        # Apply privacy filter to response
        response.response = PrivacyFilter.filter_response_text(response.response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail="Error processing chat message")
