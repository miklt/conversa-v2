"""
Multi-agent query processing system for complex questions
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import logging
from abc import ABC, abstractmethod
import json

from backend.app.models.models import Relatorio, TermoTecnico, RelatorioTermo
from backend.app.services.privacy_filter import PrivacyFilter

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all query agents"""
    
    @abstractmethod
    def process(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a query and return results"""
        pass


class CompanyTechnologyAgent(BaseAgent):
    """Agent for finding companies that use specific technologies"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find companies that work with specific technologies
        Example: "Quais empresas trabalham com C#?"
        """
        # Extract technology from context (should be done by Intent Analyzer)
        technology = context.get('technology')
        if not technology:
            return {"error": "Technology not specified"}
        
        # Find normalized term
        sql = """
            SELECT DISTINCT r.empresa_razao_social,
                   COUNT(DISTINCT r.id) as report_count,
                   STRING_AGG(DISTINCT CAST(r.ano AS TEXT), ', ') as years,
                   STRING_AGG(DISTINCT CAST(r.periodo AS TEXT), ', ') as periods
            FROM relatorios r
            JOIN relatorio_termos rt ON r.id = rt.relatorio_id
            JOIN termos_tecnicos tt ON tt.id = rt.termo_id
            WHERE LOWER(tt.termo_normalizado) = LOWER(:tech)
               OR LOWER(tt.termo) = LOWER(:tech)
            GROUP BY r.empresa_razao_social
            ORDER BY report_count DESC
        """
        
        result = self.db.execute(text(sql), {"tech": technology})
        companies = []
        for row in result:
            companies.append({
                "company": row[0],
                "count": row[1],
                "years": row[2],
                "periods": row[3]
            })
        
        return {
            "companies": companies,
            "technology": technology,
            "total": len(companies)
        }


class MethodologyAgent(BaseAgent):
    """Agent for finding companies that use specific methodologies"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find companies using specific methodologies
        Example: "Que empresas usam métodos ágeis?"
        """
        # Map common terms to normalized ones
        methodology_map = {
            "ágeis": ["agile", "scrum", "kanban"],
            "agile": ["agile", "scrum", "kanban"],
            "scrum": ["scrum"],
            "kanban": ["kanban"],
            "devops": ["devops", "cicd"]
        }
        
        # Extract methodology type
        methodology = context.get('methodology', 'agile')
        terms = methodology_map.get(methodology.lower(), [methodology.lower()])
        
        sql = """
            SELECT DISTINCT r.empresa_razao_social,
                   COUNT(DISTINCT r.id) as report_count,
                   STRING_AGG(DISTINCT tt.termo_normalizado, ', ') as methods_used
            FROM relatorios r
            JOIN relatorio_termos rt ON r.id = rt.relatorio_id
            JOIN termos_tecnicos tt ON tt.id = rt.termo_id
            WHERE LOWER(tt.termo_normalizado) = ANY(:terms)
               AND tt.tipo = 'TECNICA'
            GROUP BY r.empresa_razao_social
            ORDER BY report_count DESC
        """
        
        result = self.db.execute(text(sql), {"terms": terms})
        companies = []
        for row in result:
            companies.append({
                "company": row[0],
                "count": row[1],
                "methods": row[2]
            })
        
        return {
            "companies": companies,
            "methodology": methodology,
            "search_terms": terms,
            "total": len(companies)
        }


class LearningOutcomesAgent(BaseAgent):
    """Agent for analyzing learning outcomes"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze common learnings from internships
        Example: "Qual é o aprendizado mais comum dos alunos no primeiro estágio?"
        """
        ordinal_estagio = context.get('ordinal_estagio', 1)
        
        # Get all reports for the specified internship order
        reports = self.db.query(Relatorio).filter_by(
            ordinal_estagio=ordinal_estagio
        ).all()
        
        learnings = []
        technologies_learned = []
        soft_skills = []
        
        for report in reports:
            json_data = report.json_completo
            
            # Extract learnings from activities
            for activity in json_data.get('atividades_realizadas', []):
                if activity.get('aprendizados'):
                    learning_text = activity['aprendizados']
                    learnings.append(learning_text)
                    
                    # Extract technologies mentioned
                    tech_terms = self._extract_technologies(learning_text)
                    technologies_learned.extend(tech_terms)
                    
                    # Extract soft skills
                    soft_terms = self._extract_soft_skills(learning_text)
                    soft_skills.extend(soft_terms)
        
        # Count frequencies
        tech_freq = self._count_frequencies(technologies_learned)
        soft_freq = self._count_frequencies(soft_skills)
        
        return {
            "ordinal_estagio": ordinal_estagio,
            "total_reports": len(reports),
            "total_learnings": len(learnings),
            "top_technologies": dict(list(tech_freq.items())[:10]),
            "top_soft_skills": dict(list(soft_freq.items())[:10]),
            "sample_learnings": learnings[:5]  # Sample for LLM summarization
        }
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology mentions from text"""
        text_lower = text.lower()
        technologies = []
        
        # Get all technical terms
        terms = self.db.query(TermoTecnico).filter(
            TermoTecnico.tipo.in_(['LINGUAGEM', 'FRAMEWORK', 'FERRAMENTA'])
        ).all()
        
        for term in terms:
            if term.termo.lower() in text_lower:
                technologies.append(term.termo_normalizado)
        
        return technologies
    
    def _extract_soft_skills(self, text: str) -> List[str]:
        """Extract soft skills from text"""
        soft_skills_keywords = [
            'comunicação', 'trabalho em equipe', 'liderança', 'organização',
            'proatividade', 'resolução de problemas', 'adaptabilidade',
            'aprendizado contínuo', 'gestão de tempo', 'colaboração',
            'pensamento crítico', 'criatividade', 'responsabilidade'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in soft_skills_keywords:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _count_frequencies(self, items: List[str]) -> Dict[str, int]:
        """Count frequency of items"""
        from collections import Counter
        return dict(Counter(items).most_common())


class CompanyRequirementsAgent(BaseAgent):
    """Agent for analyzing what to study for specific companies"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze requirements for a specific company
        Example: "O que devo estudar para me candidatar ao Banco BTG?"
        """
        company_name = context.get('company', 'BTG')
        
        # Get all reports from the company
        reports = self.db.query(Relatorio).filter(
            Relatorio.empresa_razao_social.ilike(f"%{company_name}%")
        ).all()
        
        if not reports:
            return {"error": f"No reports found for company: {company_name}"}
        
        # Get technologies used
        sql = """
            SELECT tt.termo_normalizado, tt.tipo,
                   COUNT(DISTINCT r.id) as frequency
            FROM relatorios r
            JOIN relatorio_termos rt ON r.id = rt.relatorio_id
            JOIN termos_tecnicos tt ON tt.id = rt.termo_id
            WHERE r.empresa_razao_social ILIKE :company
            GROUP BY tt.termo_normalizado, tt.tipo
            ORDER BY frequency DESC
            LIMIT 20
        """
        
        tech_result = self.db.execute(text(sql), {"company": f"%{company_name}%"})
        technologies = {}
        for row in tech_result:
            tech_type = row[1]
            if tech_type not in technologies:
                technologies[tech_type] = []
            technologies[tech_type].append({
                "name": row[0],
                "frequency": row[2]
            })
        
        # Analyze activities and roles
        roles = []
        activities = []
        skills_mentioned = []
        
        for report in reports:
            json_data = report.json_completo
            
            for activity in json_data.get('atividades_realizadas', []):
                if activity.get('papel_exercido'):
                    roles.append(activity['papel_exercido'])
                if activity.get('descricao'):
                    activities.append(activity['descricao'])
                if activity.get('aprendizados'):
                    skills_mentioned.append(activity['aprendizados'])
        
        # Count role frequencies
        role_freq = self._count_frequencies(roles)
        
        return {
            "company": company_name,
            "total_reports": len(reports),
            "technologies": technologies,
            "common_roles": dict(list(role_freq.items())[:5]),
            "sample_activities": activities[:5],
            "skills_to_study": self._extract_key_skills(technologies, skills_mentioned)
        }
    
    def _count_frequencies(self, items: List[str]) -> Dict[str, int]:
        """Count frequency of items"""
        from collections import Counter
        return dict(Counter(items).most_common())
    
    def _extract_key_skills(self, technologies: Dict, skills_mentioned: List[str]) -> List[str]:
        """Extract key skills to study based on data"""
        key_skills = []
        
        # Add top languages
        if 'LINGUAGEM' in technologies:
            for tech in technologies['LINGUAGEM'][:3]:
                key_skills.append(tech['name'])
        
        # Add top frameworks
        if 'FRAMEWORK' in technologies:
            for tech in technologies['FRAMEWORK'][:2]:
                key_skills.append(tech['name'])
        
        # Add top tools
        if 'FERRAMENTA' in technologies:
            for tech in technologies['FERRAMENTA'][:2]:
                key_skills.append(tech['name'])
        
        return key_skills


class QueryOrchestrator:
    """Orchestrates multiple agents to answer complex queries"""
    
    def __init__(self, db: Session):
        self.db = db
        self.agents = {
            'company_technology': CompanyTechnologyAgent(db),
            'methodology': MethodologyAgent(db),
            'learning_outcomes': LearningOutcomesAgent(db),
            'company_requirements': CompanyRequirementsAgent(db)
        }
    
    def process_query(self, query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a query using the appropriate agent(s)
        """
        query_type = intent.get('type')
        
        # Route to appropriate agent
        if query_type == 'company_technology':
            agent = self.agents['company_technology']
        elif query_type == 'methodology':
            agent = self.agents['methodology']
        elif query_type == 'learning_analysis':
            agent = self.agents['learning_outcomes']
        elif query_type == 'company_requirements':
            agent = self.agents['company_requirements']
        else:
            return {"error": "Query type not supported"}
        
        # Process with selected agent
        result = agent.process(query, intent)
        
        # Apply privacy filter
        if 'sample_learnings' in result:
            result['sample_learnings'] = [
                PrivacyFilter.filter_string(text) 
                for text in result['sample_learnings']
            ]
        
        return result
