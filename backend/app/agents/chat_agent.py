"""
Pydantic AI Agent for Chat System
"""
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import re
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


class AdvancedQueryIntent(BaseModel):
    """Advanced intent analysis for complex queries"""
    main_topic: str = Field(description="Main topic: technology, company, statistics, activities, general")
    technology_type: Optional[str] = Field(description="Type of technology: LINGUAGEM, FRAMEWORK, FERRAMENTA, etc.")
    company_filter: Optional[str] = Field(description="Specific company mentioned in query")
    year_filter: Optional[int] = Field(description="Year filter if mentioned")
    limit: int = Field(default=10, description="Number of results to return")
    query_description: str = Field(description="Natural language description of what the user wants")
    order_by_usage: str = Field(default="desc", description="Order by usage: 'desc' for most used, 'asc' for least used")
    specific_technology: Optional[str] = Field(description="Specific technology mentioned for reverse search")


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
    # Set the API key as environment variable for OpenAI
    os.environ['OPENAI_API_KEY'] = api_key
    model = OpenAIModel('gpt-4o-mini')

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

# Agent for intent analysis
intent_agent = Agent(
    model,
    system_prompt="""
    Você é um especialista em análise de consultas sobre dados de estágio de estudantes de Engenharia Elétrica da USP.
    Sua tarefa é extrair a intenção de perguntas dos usuários e mapeá-las para consultas no banco de dados.

    TIPOS DE TECNOLOGIA DISPONÍVEIS:
    - LINGUAGEM: Linguagens de programação (Python, Java, JavaScript, C++, Go, R, SQL, etc.)
    - FRAMEWORK: Frameworks (React, Angular, Django, Flask, Spring, etc.)
    - FERRAMENTA: Ferramentas (Git, Docker, VS Code, Jenkins, etc.)
    - PLATAFORMA: Plataformas (AWS, Azure, Linux, Windows, etc.)
    - BANCO_DADOS: Bancos de dados (PostgreSQL, MySQL, MongoDB, etc.)

    EMPRESAS COMUNS NO BANCO:
    - BTG Pactual (várias grafias: "BTG", "btg pactual", "banco btg")
    - CIP (Centro de Informação e Processamento)
    - Virtual Cirurgia
    - Everify Opus Software
    - Amazon
    - E muitas outras

    TIPOS DE CONSULTA PRINCIPAIS:
    1. "technology" + company_filter: "Quais linguagens são usadas na BTG?"
    2. "technology" + technology_type: "Quais são as linguagens mais usadas?"
    3. "reverse_technology": "Quais empresas usam Python?"
    4. "company": "Quais empresas têm mais estagiários?"
    5. "activities": "O que fazem os estagiários na CIP?"
    6. "statistics": "Quantos relatórios temos?"

    DETECÇÃO DE REVERSE_TECHNOLOGY:
    Uma consulta é "reverse_technology" quando:
    - Menciona uma tecnologia específica (Java, Python, React, etc.)
    - E pergunta sobre empresas que a utilizam
    - Palavras-chave: "empresas que usam", "onde se usa", "quais empresas trabalham com"

    REGRAS IMPORTANTES:
    1. Para tecnologias curtas (R, Go, C), use apenas se aparecem como palavras isoladas
    2. Diferencie entre consultas diretas e reverse:
       - "Linguagens na BTG" → technology + company_filter
       - "Empresas que usam Python" → reverse_technology
    3. Detecte plurais: linguagem/linguagens, framework/frameworks
    4. Para "tecnologias" genérico, use technology_type=None

    RESPONDA SEMPRE EM JSON com os campos exatos:
    {
        "main_topic": "technology|reverse_technology|company|activities|statistics|general",
        "technology_type": "LINGUAGEM|FRAMEWORK|FERRAMENTA|PLATAFORMA|BANCO_DADOS|null",
        "company_filter": "nome_da_empresa|null",
        "year_filter": "ano|null",
        "limit": 10,
        "query_description": "descrição_clara_da_consulta",
        "order_by_usage": "desc|asc",
        "specific_technology": "tecnologia_mencionada|null"
    }
    """
)


async def get_top_technologies(db: Session, tipo: str, year: Optional[int] = None, limit: int = 10, order_by_usage: str = "desc") -> DBQueryResult:
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

    db_tipo = type_mapping.get(tipo.lower() if tipo else '', tipo.upper() if tipo else 'LINGUAGEM')

    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = " AND ".join(filters) if filters else "1=1"

    # Determine order direction
    order_direction = "DESC" if order_by_usage == "desc" else "ASC"

    sql = f"""
        SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
        FROM relatorio_termos rt
        JOIN termos_tecnicos tt ON tt.id = rt.termo_id
        JOIN relatorios r ON r.id = rt.relatorio_id
        WHERE tt.tipo = :tipo AND {where_clause}
        GROUP BY tt.termo_normalizado
        ORDER BY count {order_direction}
        LIMIT :limit
    """

    params.update({'tipo': db_tipo, 'limit': limit})

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{'technology': row[0], 'count': row[1]} for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def get_top_companies(db: Session, year: Optional[int] = None, limit: int = 10, order_by_usage: str = "desc") -> DBQueryResult:
    """Get companies with most/least interns, optionally filtered by year with name normalization"""
    filters = []
    params = {}

    if year:
        filters.append("ano = :year")
        params['year'] = year

    where_clause = " AND ".join(filters) if filters else "1=1"

    # Determine order direction
    order_direction = "DESC" if order_by_usage == "desc" else "ASC"

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
        ORDER BY count {order_direction}
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


async def get_activities_by_company(
    db: Session,
    company_name: str,
    year: Optional[int] = None,
    limit: int = 50
) -> DBQueryResult:
    """Busca atividades realizadas em uma empresa específica usando embeddings"""
    # Normalize company name for matching
    company_patterns = {
        'btg': ['%btg pactual%', '%btg%'],
        'cip': ['%cip%', '%centro de informação%'],
        'virtual': ['%virtual cirurgia%', '%virtual%']
    }

    company_conditions = []
    for key, patterns in company_patterns.items():
        if key.lower() in company_name.lower():
            company_conditions.extend(patterns)
            break
    else:
        # If no specific pattern, use the company name directly
        company_conditions = [f'%{company_name}%']

    # Build WHERE clause for company matching
    company_where_parts = []
    for pattern in company_conditions:
        company_where_parts.append(f"r.empresa_razao_social ILIKE '{pattern}'")

    company_where = " OR ".join(company_where_parts)

    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = f" AND ({company_where})"
    if filters:
        where_clause += " AND " + " AND ".join(filters)

    sql = f"""
        SELECT re.conteudo, r.ano, r.periodo, r.ano_academico, r.curso
        FROM relatorio_embeddings re
        JOIN relatorios r ON re.relatorio_id = r.id
        WHERE re.secao = 'atividades_realizadas'{where_clause}
        ORDER BY r.ano DESC, r.periodo DESC
        LIMIT :limit
    """

    params['limit'] = limit

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{
        'content': row[0],
        'year': row[1],
        'period': row[2],
        'academic_year': row[3],
        'course': row[4]
    } for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def analyze_query_intent(message: str) -> AdvancedQueryIntent:
    """Analyze user query intent using the LLM-based intent agent with fallback"""
    try:
        # For now, we'll use a hybrid approach: LLM + keyword validation
        # This ensures reliability while leveraging LLM capabilities
        
        # First, use the keyword-based fallback as a baseline
        baseline_intent = await analyze_query_intent_fallback(message)
        
        # Try to enhance with LLM analysis
        try:
            result = await intent_agent.run(f"""
            Analise esta consulta sobre estágios e corrija/melhore esta análise inicial:
            
            CONSULTA: "{message}"
            
            ANÁLISE INICIAL:
            - main_topic: {baseline_intent.main_topic}
            - technology_type: {baseline_intent.technology_type}
            - company_filter: {baseline_intent.company_filter}
            - specific_technology: {baseline_intent.specific_technology}
            
            Retorne apenas um JSON válido com os campos corrigidos/melhorados:
            {{
                "main_topic": "valor",
                "technology_type": "valor",
                "company_filter": "valor", 
                "year_filter": "valor",
                "limit": 10,
                "query_description": "valor",
                "order_by_usage": "desc",
                "specific_technology": "valor"
            }}
            """)
            
            # Parse the JSON response
            import json
            response_text = str(result.data) if hasattr(result, 'data') else str(result)
            
            # Try to extract and parse JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                
                # Create enhanced intent with LLM improvements
                enhanced_intent = AdvancedQueryIntent(
                    main_topic=parsed_data.get('main_topic', baseline_intent.main_topic),
                    technology_type=parsed_data.get('technology_type') if parsed_data.get('technology_type') != 'null' else baseline_intent.technology_type,
                    company_filter=parsed_data.get('company_filter') if parsed_data.get('company_filter') != 'null' else baseline_intent.company_filter,
                    year_filter=parsed_data.get('year_filter') if parsed_data.get('year_filter') != 'null' else baseline_intent.year_filter,
                    limit=parsed_data.get('limit', 10),
                    query_description=parsed_data.get('query_description', message),
                    order_by_usage=parsed_data.get('order_by_usage', 'desc'),
                    specific_technology=parsed_data.get('specific_technology') if parsed_data.get('specific_technology') != 'null' else baseline_intent.specific_technology
                )
                
                return enhanced_intent
                
        except Exception as llm_error:
            pass
            
        # Return the reliable baseline intent
        return baseline_intent
            
    except Exception as e:
        print(f"❌ Error in intent analysis: {e}")
        # Final fallback - create a basic intent with all required fields
        return AdvancedQueryIntent(
            main_topic="general",
            technology_type=None,
            company_filter=None,
            year_filter=None,
            limit=10,
            query_description=message,
            order_by_usage="desc",
            specific_technology=None
        )


async def analyze_query_intent_fallback(message: str) -> AdvancedQueryIntent:
    """Analyze user query intent using enhanced keyword-based analysis"""
    # Enhanced keyword-based parsing
    message_lower = message.lower()

    # Extract main topic
    main_topic = "general"
    if any(word in message_lower for word in ['framework', 'frameworks', 'linguagem', 'linguagens', 'tecnologia', 'tecnologias', 'ferramenta', 'ferramentas', 'plataforma', 'plataformas', 'banco', 'bancos']):
        main_topic = "technology"
    elif any(word in message_lower for word in ['empresa', 'empresas', 'company']):
        main_topic = "company"
    elif any(word in message_lower for word in ['estatistica', 'total', 'quantos', 'quantas']):
        main_topic = "statistics"
    elif any(word in message_lower for word in ['atividade', 'atividades', 'faz', 'trabalha', 'responsabilidades', 'funcoes']):
        main_topic = "activities"

    # Extract technology type
    technology_type = None
    if any(word in message_lower for word in ['framework', 'frameworks']):
        technology_type = "FRAMEWORK"
    elif any(word in message_lower for word in ['linguagem', 'linguagens', 'programação', 'language']):
        technology_type = "LINGUAGEM"
    elif any(word in message_lower for word in ['ferramenta', 'ferramentas', 'tool', 'tools']):
        technology_type = "FERRAMENTA"
    elif any(word in message_lower for word in ['plataforma', 'plataformas', 'platform']):
        technology_type = "PLATAFORMA"
    elif any(word in message_lower for word in ['banco', 'bancos', 'database', 'dados']):
        technology_type = "BANCO_DADOS"

    # Extract specific technology mentioned (for reverse search)
    specific_technology = None
    technology_keywords = {
        'java': 'Java',
        'javascript': 'JavaScript',
        'js': 'JavaScript',
        'python': 'Python',
        'csharp': 'C#',
        'c#': 'C#',
        'cpp': 'C++',
        'c++': 'C++',
        'go': 'Go',
        'golang': 'Go',
        'rust': 'Rust',
        'kotlin': 'Kotlin',
        'swift': 'Swift',
        'php': 'PHP',
        'ruby': 'Ruby',
        'r': 'R',
        'sql': 'SQL',
        'matlab': 'MATLAB',
        'scala': 'Scala',
        'react': 'React',
        'angular': 'Angular',
        'vue': 'Vue',
        'django': 'Django',
        'flask': 'Flask',
        'fastapi': 'FastAPI',
        'spring': 'Spring',
        'dotnet': 'dotnet',
        '.net': '.NET',
        'nodejs': 'Node.js',
        'node': 'Node.js',
        'git': 'Git',
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'aws': 'AWS',
        'azure': 'Azure',
        'gcp': 'GCP',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
        'mongodb': 'MongoDB'
    }

    # Look for technology mentions in the query - prioritize longer, more specific terms
    # Sort technology keys by length (longest first) to avoid substring matches
    sorted_tech_keys = sorted(technology_keywords.keys(), key=len, reverse=True)

    for tech_key in sorted_tech_keys:
        # For very short terms (1-2 characters), use word boundaries to avoid false positives
        if len(tech_key) <= 2:
            pattern = r'\b' + re.escape(tech_key) + r'\b'
            if re.search(pattern, message_lower):
                specific_technology = technology_keywords[tech_key]
                break
        else:
            # For longer terms, simple substring match is sufficient
            if tech_key in message_lower:
                specific_technology = technology_keywords[tech_key]
                break

    # Extract company filter - improved detection
    company_filter = None

    # First check for known companies
    if any(word in message_lower for word in ['btg', 'pactual']):
        company_filter = "BTG"
    elif 'cip' in message_lower or 'centro de informação' in message_lower:
        company_filter = "CIP"
    elif 'virtual' in message_lower:
        company_filter = "Virtual Cirurgia"
    else:
        # Try to extract any company name from the query
        # Look for patterns like "na TEB", "no Itaú", "na empresa X"

        # Pattern 1: "na/no [Company Name]" - improved to capture full names with accents
        company_match = re.search(r'\b(?:na|no|em)\s+([A-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]+(?:[A-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]*)*)', message, re.IGNORECASE | re.UNICODE)
        if company_match:
            company_name = company_match.group(1).strip()
            # Clean up the company name - remove extra spaces
            company_name = re.sub(r'\s+', ' ', company_name)
            # Avoid common words that might be mistaken for companies
            common_words = ['empresa', 'empresas', 'sistema', 'projeto', 'trabalho', 'estagio', 'estágio', 'atividades', 'linguagem', 'framework', 'sao']
            # Also avoid technology names that might be mistaken for companies
            tech_names = set(technology_keywords.values())
            if (company_name.lower() not in common_words and
                company_name not in tech_names and
                len(company_name) > 2):
                company_filter = company_name

        # Pattern 2: Look for company names in the sentence (but avoid technology names)
        if not company_filter:
            # Find sequences of capitalized words
            words = re.findall(r'\b[A-Z][a-zA-Z]+\b', message)
            for i, word in enumerate(words):
                # Skip common words
                if word.lower() in ['qual', 'quais', 'como', 'onde', 'quando', 'por', 'que', 'na', 'no', 'em', 'do', 'da', 'dos', 'das', 'um', 'uma', 'uns', 'umas', 'sao', 'atividade', 'atividades']:
                    continue
                # Skip technology names
                if word in technology_keywords.values():
                    continue
                # If we find a capitalized word that's not at the beginning and not a common preposition
                if i > 0 and len(word) > 2:
                    company_filter = word
                    break

    # Extract year filter
    year_filter = None
    year_match = re.search(r'\b(20\d{2})\b', message_lower)
    if year_match:
        year_filter = int(year_match.group(1))

    # Extract order by usage (most/least used)
    order_by_usage = "desc"  # default to most used
    if 'menos' in message_lower:
        order_by_usage = "asc"

    # Special case: if we have both technology type and company, it's a specific query
    if technology_type and company_filter:
        main_topic = "technology"

    # Special case: if we have a specific technology mentioned and the query is about companies/enterprises
    # This indicates a reverse search (technology -> companies)
    if (specific_technology and
        any(word in message_lower for word in ['empresa', 'empresas', 'company', 'companies', 'trabalha', 'usa', 'usam', 'utiliza', 'utilizam'])):
        main_topic = "reverse_technology"

    return AdvancedQueryIntent(
        main_topic=main_topic,
        technology_type=technology_type,
        company_filter=company_filter,
        year_filter=year_filter,
        limit=10,
        query_description=message,
        order_by_usage=order_by_usage,
        specific_technology=specific_technology
    )


async def search_general(db: Session, query_description: str, limit: int = 10) -> DBQueryResult:
    """General search based on query description"""
    # This is a fallback - could be enhanced with more sophisticated search
    return await get_top_companies(db, limit=limit)


async def get_total_reports_count(db: Session, year: Optional[int] = None) -> int:
    """Get total number of reports, optionally filtered by year"""
    if year:
        count = db.query(func.count(Relatorio.id)).filter(Relatorio.ano == year).scalar()
    else:
        count = db.query(func.count(Relatorio.id)).scalar()

    return count


async def get_technologies_from_activities_content(db: Session, activities_content: List[str], company_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca tecnologias reais do banco de dados baseadas no conteúdo das atividades com busca aprimorada"""
    try:
        # Get all technologies from the database
        technologies_query = db.query(TermoTecnico).all()

        # Create a mapping of technology names to their data
        tech_mapping = {}
        for tech in technologies_query:
            termo_lower = tech.termo.lower().strip()
            if termo_lower not in tech_mapping:
                tech_mapping[termo_lower] = tech

        # Count occurrences in the activities content using word boundaries
        tech_counts = {}
        all_content = " ".join(activities_content).lower()

        # Special handling for single-character terms that are prone to false positives
        problematic_terms = {'r', 'go', 'ai', 'ml', 'js', 'ts', 'c#'}

        for tech_name, tech_obj in tech_mapping.items():
            tech_name_lower = tech_name.lower().strip()

            # Skip problematic single-letter terms unless they appear as standalone words
            if tech_name_lower in problematic_terms and len(tech_name_lower) <= 2:
                # For these terms, require word boundaries and check context
                pattern = r'\b' + re.escape(tech_name_lower) + r'\b'
                matches = re.findall(pattern, all_content, re.IGNORECASE)
                count = len(matches)

                # Additional validation for very short terms
                if count > 0 and len(tech_name_lower) == 1:
                    # For single letters, be very strict - only count if it's clearly a programming language reference
                    context_patterns = [
                        r'\blinguagem\s+' + re.escape(tech_name_lower) + r'\b',
                        r'\bprogramação\s+em\s+' + re.escape(tech_name_lower) + r'\b',
                        r'\bdesenvolvimento\s+em\s+' + re.escape(tech_name_lower) + r'\b',
                        r'\bcódigo\s+' + re.escape(tech_name_lower) + r'\b',
                        r'\bscript\s+' + re.escape(tech_name_lower) + r'\b'
                    ]
                    valid_context = any(re.search(pattern, all_content, re.IGNORECASE) for pattern in context_patterns)
                    if not valid_context:
                        count = 0
            else:
                # For longer terms, use word boundaries to avoid substring matches
                if len(tech_name_lower) > 2:
                    pattern = r'\b' + re.escape(tech_name_lower) + r'\b'
                    matches = re.findall(pattern, all_content, re.IGNORECASE)
                    count = len(matches)
                else:
                    # For 2-3 letter terms, be more careful
                    pattern = r'\b' + re.escape(tech_name_lower) + r'\b'
                    matches = re.findall(pattern, all_content, re.IGNORECASE)
                    count = len(matches)

                    # Additional check: ensure it's not part of a larger word
                    if count > 0:
                        # Check if this term appears in contexts that suggest it's a technology
                        tech_contexts = [
                            'desenvolvimento', 'programação', 'linguagem', 'tecnologia',
                            'framework', 'biblioteca', 'ferramenta', 'plataforma',
                            'banco', 'dados', 'sistema', 'aplicação', 'projeto'
                        ]
                        has_tech_context = any(context in all_content for context in tech_contexts)
                        if not has_tech_context:
                            count = max(0, count - 2)  # Reduce count if no tech context

            if count > 0:
                tech_counts[tech_obj.termo] = {
                    'technology': tech_obj.termo,
                    'category': tech_obj.tipo.value if hasattr(tech_obj.tipo, 'value') else str(tech_obj.tipo),
                    'count': count,
                    'normalized': tech_obj.termo_normalizado
                }

        # Sort by count and return top technologies
        sorted_techs = sorted(tech_counts.values(), key=lambda x: x['count'], reverse=True)

        # Filter out technologies with very low counts that might be false positives
        filtered_techs = []
        for tech in sorted_techs:
            # For very short terms, require higher confidence
            if len(tech['technology'].strip()) <= 2 and tech['count'] < 2:
                continue
            # For longer terms, accept lower counts
            elif len(tech['technology'].strip()) > 2 and tech['count'] < 1:
                continue
            filtered_techs.append(tech)

        return filtered_techs[:15]  # Limit to top 15 to avoid noise

    except Exception as e:
        print(f"Error getting technologies from database: {e}")
        import traceback
        traceback.print_exc()
        return []


async def perform_llm_analysis(prompt: str) -> str:
    """Realiza análise usando LLM (placeholder para futura implementação)"""
    try:
        # For now, return a basic analysis
        # TODO: Integrate with actual LLM service
        return "Análise realizada baseada nos padrões identificados no conteúdo das atividades."

    except Exception as e:
        print(f"Error in LLM analysis: {e}")
        return "Análise não disponível no momento."


async def analyze_activities_patterns(db: Session, activities_content: List[str], company_name: Optional[str] = None) -> Dict[str, Any]:
    """Analisa padrões nas atividades usando dados do banco e LLM"""
    if not activities_content:
        return {"error": "No activities content to analyze"}

    try:
        # Primeiro, buscar tecnologias reais do banco de dados
        technologies_data = await get_technologies_from_activities_content(db, activities_content, company_name)

        # Aggregate content (limit to avoid token limits)
        aggregated_content = "\n\n".join(activities_content[:15])  # Limit to 15 activities

        # Use LLM for sophisticated analysis
        analysis_prompt = f"""
        Analise estas atividades de estágio e identifique os padrões principais:

        ATIVIDADES:
        {aggregated_content}

        TECNOLOGIAS ENCONTRADAS NO BANCO:
        {', '.join([f"{tech['technology']} ({tech['count']} ocorrências)" for tech in technologies_data[:10]])}

        IDENTIFIQUE:
        1. Principais tipos de atividades (desenvolvimento, análise, manutenção, testes, documentação, etc.)
        2. Padrões de responsabilidade dos estagiários
        3. Nível de complexidade das tarefas
        4. Habilidades técnicas mais demandadas

        Seja específico e baseie sua análise nos dados fornecidos. Foque nos padrões mais relevantes.
        """

        # Use the intent agent for analysis
        try:
            # For now, we'll create a structured analysis based on the data
            # TODO: Replace with actual LLM call when available
            llm_analysis = await perform_llm_analysis(analysis_prompt)
        except Exception as e:
            print(f"LLM analysis failed, using fallback: {e}")
            llm_analysis = "Análise baseada nos dados dos relatórios de estágio."

        # Extract activity types from content
        all_content = " ".join(activities_content).lower()
        activities_types = []

        # More comprehensive activity type detection
        activity_patterns = {
            'Desenvolvimento': ['desenvolvimento', 'development', 'programação', 'coding', 'implementação', 'criação'],
            'Manutenção': ['manutenção', 'maintenance', 'correção', 'bug', 'fix', 'atualização'],
            'Testes': ['teste', 'test', 'testing', 'qa', 'qualidade', 'validação'],
            'Análise': ['análise', 'analysis', 'analisar', 'estudo', 'pesquisa', 'investigação'],
            'Documentação': ['documentação', 'documentation', 'docs', 'manual', 'especificação'],
            'Suporte': ['suporte', 'support', 'ajuda', 'assistência', 'técnico'],
            'Integração': ['integração', 'integration', 'api', 'serviço', 'conexão'],
            'Otimização': ['otimização', 'optimization', 'performance', 'melhoria', 'refatoração']
        }

        for activity_type, keywords in activity_patterns.items():
            if any(keyword in all_content for keyword in keywords):
                activities_types.append(activity_type)

        # Get top technologies
        top_technologies = [tech['technology'] for tech in technologies_data[:8]]

        # Create comprehensive analysis
        analysis_parts = []
        if activities_types:
            analysis_parts.append(f"Atividades envolvem principalmente {', '.join(activities_types[:3])}")
        if top_technologies:
            analysis_parts.append(f"Tecnologias principais: {', '.join(top_technologies[:5])}")

        comprehensive_analysis = ". ".join(analysis_parts) if analysis_parts else "Análise das atividades realizada com base nos dados disponíveis."

        return {
            "total_activities": len(activities_content),
            "technologies_found": top_technologies,
            "activity_types": activities_types,
            "analysis": comprehensive_analysis,
            "llm_insights": llm_analysis,
            "technology_details": technologies_data[:10]  # Include detailed tech data
        }

    except Exception as e:
        print(f"Error analyzing activities: {e}")
        return {
            "error": f"Failed to analyze activities: {str(e)}",
            "total_activities": len(activities_content)
        }


async def execute_complex_query(db: Session, intent: AdvancedQueryIntent) -> DBQueryResult:
    """Execute complex database query based on analyzed intent"""
    try:
        if intent.main_topic == "technology" and intent.technology_type and intent.company_filter:
            # Query: "What frameworks are used at BTG?"
            return await get_technologies_by_company_and_type(
                db, intent.company_filter, intent.technology_type, intent.year_filter, intent.limit, intent.order_by_usage
            )

        elif intent.main_topic == "technology" and intent.company_filter and not intent.technology_type:
            # Query: "What technologies are used at BTG?" (general technologies at a company)
            return await get_all_technologies_by_company(
                db, intent.company_filter, intent.year_filter, intent.limit, intent.order_by_usage
            )

        elif intent.main_topic == "technology" and intent.technology_type:
            # Query: "What are the most used frameworks?"
            return await get_top_technologies(
                db, intent.technology_type, intent.year_filter, intent.limit, intent.order_by_usage
            )

        elif intent.main_topic == "reverse_technology" and intent.specific_technology:
            # Query: "Which companies use Java?"
            return await get_companies_by_technology(
                db, intent.specific_technology, intent.year_filter, intent.limit, intent.order_by_usage
            )

        elif intent.main_topic == "company":
            # Query: "Which companies have the most/least interns?"
            return await get_top_companies(db, intent.year_filter, intent.limit, intent.order_by_usage)

        elif intent.main_topic == "activities" and intent.company_filter:
            # Query: "What activities are performed at BTG?"
            return await get_activities_by_company(
                db, intent.company_filter, intent.year_filter, intent.limit
            )

        elif intent.main_topic == "activities":
            # Query: "What are typical intern activities?"
            # Get activities from top companies
            top_companies_result = await get_top_companies(db, intent.year_filter, 3)  # Get top 3 companies
            if top_companies_result.data:
                # Get activities from the top company
                top_company = top_companies_result.data[0]['company']
                # Extract company name for filtering
                if 'BTG' in top_company.upper():
                    company_filter = 'BTG'
                elif 'CIP' in top_company.upper():
                    company_filter = 'CIP'
                elif 'VIRTUAL' in top_company.upper():
                    company_filter = 'Virtual'
                else:
                    company_filter = top_company.split()[0]  # First word as filter

                return await get_activities_by_company(
                    db, company_filter, intent.year_filter, intent.limit
                )
            else:
                return DBQueryResult(data=[], total_count=0)

        elif intent.main_topic == "statistics":
            # General statistics
            total = await get_total_reports_count(db, intent.year_filter)
            return DBQueryResult(
                data=[{"statistic": "total_reports", "value": total}],
                total_count=1
            )

        else:
            # Fallback to general search
            return await search_general(db, intent.query_description, intent.limit)

    except Exception as e:
        print(f"Error executing complex query: {e}")
        return DBQueryResult(data=[], total_count=0)


async def get_all_technologies_by_company(
    db: Session,
    company_name: str,
    year: Optional[int] = None,
    limit: int = 10,
    order_by_usage: str = "desc"
) -> DBQueryResult:
    """Get all technologies used at a specific company (not filtered by type)"""
    # Normalize company name for matching
    company_patterns = {
        'btg': ['%btg pactual%', '%btg%'],
        'cip': ['%cip%', '%centro de informação%'],
        'virtual': ['%virtual cirurgia%', '%virtual%']
    }

    company_conditions = []
    for key, patterns in company_patterns.items():
        if key.lower() in company_name.lower():
            company_conditions.extend(patterns)
            break
    else:
        # If no specific pattern, use the company name directly
        company_conditions = [f'%{company_name}%']

    # Build WHERE clause for company matching
    company_where_parts = []
    for pattern in company_conditions:
        company_where_parts.append(f"r.empresa_razao_social ILIKE '{pattern}'")

    company_where = " OR ".join(company_where_parts)

    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = f" AND ({company_where})"
    if filters:
        where_clause += " AND " + " AND ".join(filters)

    # Determine order direction
    order_direction = "DESC" if order_by_usage == "desc" else "ASC"

    sql = f"""
        SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
        FROM relatorio_termos rt
        JOIN termos_tecnicos tt ON tt.id = rt.termo_id
        JOIN relatorios r ON r.id = rt.relatorio_id
        WHERE 1=1{where_clause}
        GROUP BY tt.termo_normalizado
        ORDER BY count {order_direction}
        LIMIT :limit
    """

    params.update({'limit': limit})

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{'technology': row[0], 'count': row[1]} for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def get_technologies_by_company_and_type(
    db: Session,
    company_name: str,
    technology_type: str,
    year: Optional[int] = None,
    limit: int = 10,
    order_by_usage: str = "desc"
) -> DBQueryResult:
    """Get technologies of specific type used at a specific company"""
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

    db_tipo = type_mapping.get(technology_type.lower() if technology_type else '', technology_type.upper() if technology_type else 'LINGUAGEM')

    # Normalize company name for matching
    company_patterns = {
        'btg': ['%btg pactual%', '%btg%'],
        'cip': ['%cip%', '%centro de informação%'],
        'virtual': ['%virtual cirurgia%', '%virtual%']
    }

    company_conditions = []
    for key, patterns in company_patterns.items():
        if key.lower() in company_name.lower():
            company_conditions.extend(patterns)
            break
    else:
        # If no specific pattern, use the company name directly
        company_conditions = [f'%{company_name}%']

    # Build WHERE clause for company matching
    company_where_parts = []
    for pattern in company_conditions:
        company_where_parts.append(f"r.empresa_razao_social ILIKE '{pattern}'")

    company_where = " OR ".join(company_where_parts)

    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = f" AND ({company_where})"
    if filters:
        where_clause += " AND " + " AND ".join(filters)

    # Determine order direction
    order_direction = "DESC" if order_by_usage == "desc" else "ASC"

    sql = f"""
        SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
        FROM relatorio_termos rt
        JOIN termos_tecnicos tt ON tt.id = rt.termo_id
        JOIN relatorios r ON r.id = rt.relatorio_id
        WHERE tt.tipo = :tipo{where_clause}
        GROUP BY tt.termo_normalizado
        ORDER BY count {order_direction}
        LIMIT :limit
    """

    params.update({'tipo': db_tipo, 'limit': limit})

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{'technology': row[0], 'count': row[1]} for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def get_companies_by_technology(
    db: Session,
    technology: str,
    year: Optional[int] = None,
    limit: int = 10,
    order_by_usage: str = "desc"
) -> DBQueryResult:
    """Get companies that use a specific technology, ordered by usage frequency"""
    filters = []
    params = {}

    if year:
        filters.append("r.ano = :year")
        params['year'] = year

    where_clause = " AND ".join(filters) if filters else "1=1"

    # Determine order direction
    order_direction = "DESC" if order_by_usage == "desc" else "ASC"

    # Query with company name normalization using SQL CASE statements
    sql = f"""
        SELECT
            CASE
                WHEN r.empresa_razao_social ILIKE '%btg pactual%' THEN 'BANCO BTG PACTUAL S.A.'
                WHEN r.empresa_razao_social ILIKE '%btg%' THEN 'BANCO BTG PACTUAL S.A.'
                WHEN r.empresa_razao_social ILIKE '%cip%' THEN 'CIP - CENTRO DE INFORMAÇÃO E PROCESSAMENTO'
                WHEN r.empresa_razao_social ILIKE '%centro de informação%' THEN 'CIP - CENTRO DE INFORMAÇÃO E PROCESSAMENTO'
                WHEN r.empresa_razao_social ILIKE '%virtual cirurgia%' THEN 'VIRTUAL CIRURGIA'
                WHEN r.empresa_razao_social ILIKE '%virtual%' THEN 'VIRTUAL CIRURGIA'
                ELSE r.empresa_razao_social
            END as normalized_company,
            COUNT(DISTINCT rt.relatorio_id) as report_count
        FROM relatorio_termos rt
        JOIN termos_tecnicos tt ON tt.id = rt.termo_id
        JOIN relatorios r ON r.id = rt.relatorio_id
        WHERE tt.termo_normalizado ILIKE :tech AND {where_clause}
        GROUP BY normalized_company
        ORDER BY report_count {order_direction}
        LIMIT :limit
    """

    params.update({'tech': f'%{technology}%', 'limit': limit})

    result = db.execute(text(sql), params)
    rows = result.fetchall()

    data = [{'company': row[0], 'count': row[1]} for row in rows]

    return DBQueryResult(data=data, total_count=len(data))


async def validate_response_adequacy(intent: AdvancedQueryIntent, response: str) -> bool:
    """Validate if the response is adequate to the original query"""
    query_lower = intent.query_description.lower()
    response_lower = response.lower()

    # Check for "menos" queries
    if 'menos' in query_lower:
        if intent.main_topic == "company":
            # For company queries with "menos", response should contain "menos estagiários"
            if "menos estagiários" not in response_lower:
                return False
        elif intent.main_topic == "technology":
            # For technology queries with "menos", response should contain "menos utilizad"
            if "menos utilizad" not in response_lower:
                return False

    # Check for activities queries
    if intent.main_topic == "activities":
        if "atividades" not in response_lower and "estagiários" not in response_lower:
            return False

    # Check for year filters
    if intent.year_filter:
        if str(intent.year_filter) not in response:
            return False

    # Check for company filters
    if intent.company_filter:
        company_display = intent.company_filter.title()
        if 'btg' in intent.company_filter.lower():
            company_display = 'BTG Pactual'
        if company_display.lower() not in response_lower:
            return False

    return True


async def process_chat_message(message: str, db: Session) -> ChatResponse:
    """Process a chat message using LLM-based intent analysis"""
    try:
        # Analyze query intent using LLM
        intent = await analyze_query_intent(message)

        # Execute appropriate query based on intent
        result = await execute_complex_query(db, intent)

        # Format response based on intent and results
        if not result.data:
            return ChatResponse(
                response="Desculpe, não encontrei dados para essa consulta. Tente reformular sua pergunta.",
                confidence=0.2
            )

        # Format response based on query type
        response = None
        if intent.main_topic == "technology" and intent.company_filter:
            # Response for "frameworks used at BTG" type queries
            tech_type_name = {
                'FRAMEWORK': 'frameworks',
                'LINGUAGEM': 'linguagens de programação',
                'FERRAMENTA': 'ferramentas',
                'PLATAFORMA': 'plataformas',
                'BANCO_DADOS': 'bancos de dados'
            }.get(intent.technology_type, intent.technology_type.lower() if intent.technology_type else 'tecnologias')

            company_display = intent.company_filter.title()
            if 'btg' in intent.company_filter.lower():
                company_display = 'BTG Pactual'

            # Determine if it's most or least used
            usage_text = "mais utilizados" if intent.order_by_usage == "desc" else "menos utilizados"

            response_text = f"Os {tech_type_name} {usage_text} na {company_display} são:\n"
            for i, item in enumerate(result.data[:intent.limit], 1):
                response_text += f"{i}. {item['technology'].title()} ({item['count']} relatórios)\n"

            return ChatResponse(response=response_text, confidence=0.95)

        elif intent.main_topic == "technology":
            # Response for general technology queries
            tech_type_name = {
                'FRAMEWORK': 'frameworks',
                'LINGUAGEM': 'linguagens de programação',
                'FERRAMENTA': 'ferramentas',
                'PLATAFORMA': 'plataformas',
                'BANCO_DADOS': 'bancos de dados'
            }.get(intent.technology_type, intent.technology_type.lower() if intent.technology_type else 'tecnologias')

            # Determine if it's most or least used
            usage_text = "mais utilizadas" if intent.order_by_usage == "desc" else "menos utilizadas"

            response_text = f"As {tech_type_name} {usage_text} são:\n"
            for i, item in enumerate(result.data[:intent.limit], 1):
                response_text += f"{i}. {item['technology'].title()} ({item['count']} relatórios)\n"

            return ChatResponse(response=response_text, confidence=0.9)

        elif intent.main_topic == "company":
            # Response for company queries
            usage_text = "mais" if intent.order_by_usage == "desc" else "menos"
            response_text = f"As empresas com {usage_text} estagiários são:\n"
            for i, item in enumerate(result.data[:intent.limit], 1):
                response_text += f"{i}. {item['company']} ({item['count']} estagiários)\n"

            return ChatResponse(response=response_text, confidence=0.9)

        elif intent.main_topic == "activities":
            # Response for activities queries
            if not result.data:
                company_name = intent.company_filter or "geral"
                return ChatResponse(
                    response=f"Desculpe, não encontrei atividades para {company_name}.",
                    confidence=0.3
                )

            # Aggregate activities content
            activities_content = [item['content'] for item in result.data if item['content'].strip()]

            if not activities_content:
                return ChatResponse(
                    response=f"Encontrei {result.total_count} relatórios, mas nenhum conteúdo de atividades detalhado.",
                    confidence=0.4
                )

            # Analyze patterns (basic for now)
            analysis = await analyze_activities_patterns(db, activities_content, intent.company_filter)

            # Handle company display
            if intent.company_filter:
                company_display = intent.company_filter.title()
                if 'btg' in intent.company_filter.lower():
                    company_display = 'BTG Pactual'
                elif 'cip' in intent.company_filter.lower():
                    company_display = 'CIP'
                title = f"📋 **Atividades de Estagiários na {company_display}**"
            else:
                title = f"📋 **Atividades Típicas de Estagiários**"

            response_text = f"{title}\n\n"
            response_text += f"Analisando {result.total_count} relatórios de estágio:\n\n"

            # Show sample activities
            response_text += "🔧 **Exemplos de Atividades:**\n"
            for i, activity in enumerate(activities_content[:5], 1):  # Show first 5
                # Truncate long activities
                short_activity = activity[:200] + "..." if len(activity) > 200 else activity
                response_text += f"{i}. {short_activity}\n"

            if len(activities_content) > 5:
                response_text += f"\n... e mais {len(activities_content) - 5} atividades\n"

            response_text += f"\n📊 **Análise:** {analysis.get('analysis', 'Análise das atividades realizada')}"

            # Add technologies if found
            if analysis.get('technologies_found'):
                response_text += f"\n🛠️ **Tecnologias Identificadas:** {', '.join(analysis['technologies_found'])}\n"

            # Add activity types if found
            if analysis.get('activity_types'):
                response_text += f"\n📋 **Tipos de Atividades:** {', '.join(analysis['activity_types'])}"

            return ChatResponse(response=response_text, confidence=0.85)

        elif intent.main_topic == "reverse_technology":
            # Response for reverse technology queries (companies that use a specific technology)
            if not result.data:
                tech_name = intent.specific_technology or "tecnologia especificada"
                return ChatResponse(
                    response=f"Desculpe, não encontrei empresas que utilizam {tech_name}.",
                    confidence=0.3
                )

            tech_name = intent.specific_technology or "tecnologia"
            usage_text = "mais" if intent.order_by_usage == "desc" else "menos"

            response_text = f"🏢 **Empresas que utilizam {tech_name}**\n\n"
            response_text += f"As empresas com {usage_text} relatórios mencionando {tech_name} são:\n\n"

            for i, item in enumerate(result.data[:intent.limit], 1):
                company_name = item['company']
                count = item['count']
                response_text += f"{i}. {company_name} ({count} relatório{'s' if count > 1 else ''})\n"

            if result.total_count > intent.limit:
                response_text += f"\n... e mais {result.total_count - intent.limit} empresas"

            return ChatResponse(response=response_text, confidence=0.9)

        # Default fallback
        response = ChatResponse(
            response="Desculpe, não entendi sua pergunta completamente. Você pode estruturar sua pergunta da seguinte forma:\n"
                    "- Que|Qual <linguagens|frameworks|plataformas> são usadas em <geral|empresa específica>? \n"
                    "- Que|Qual <empresa específica> usa <linguagens|frameworks|plataformas> ?\n"
                    "- Qual <Empresa|linguagem|frameworks|plataformas> é a mais popular?\n",
            confidence=0.3
        )

        # Validate response adequacy
        if hasattr(response, 'response') and not await validate_response_adequacy(intent, response.response):
            print(f"Warning: Response may not be adequate to query. Intent: {intent}")
            # Could add corrective logic here in the future

        return response

    except Exception as e:
        print(f"Error in process_chat_message: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(
            response="Desculpe, houve um erro ao processar sua pergunta. Tente novamente.",
            confidence=0.1
        )