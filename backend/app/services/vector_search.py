"""
Vector search service for semantic search using embeddings
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from backend.app.models.models import Relatorio, RelatorioEmbedding
from backend.app.services.privacy_filter import PrivacyFilter

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for vector-based semantic search"""
    
    @staticmethod
    def search_similar_reports(
        db: Session,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = None,
        filters: Dict[str, Any] = None
    ) -> List[Tuple[Relatorio, float]]:
        """
        Search for reports similar to the query embedding
        
        Args:
            db: Database session
            query_embedding: Query vector (1536 dimensions)
            limit: Maximum number of results
            threshold: Optional similarity threshold
            filters: Optional filters (year, course, etc.)
        
        Returns:
            List of (Report, similarity_score) tuples
        """
        try:
            # Build the base query
            query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Base SQL with vector similarity
            sql = """
                SELECT DISTINCT r.*, 
                       MIN(e.embedding <-> CAST(:query_vector AS vector)) as distance
                FROM relatorios r
                JOIN relatorio_embeddings e ON r.id = e.relatorio_id
                WHERE e.embedding IS NOT NULL
            """
            
            params = {"query_vector": query_vector_str}
            
            # Add filters if provided
            conditions = []
            if filters:
                if 'year' in filters:
                    conditions.append("r.ano = :year")
                    params['year'] = filters['year']
                
                if 'course' in filters:
                    conditions.append("r.curso = :course")
                    params['course'] = filters['course']
                
                if 'period' in filters:
                    conditions.append("r.periodo = :period")
                    params['period'] = filters['period']
                
                if 'company' in filters:
                    conditions.append("r.empresa_razao_social ILIKE :company")
                    params['company'] = f"%{filters['company']}%"
            
            if conditions:
                sql += " AND " + " AND ".join(conditions)
            
            # Group by all columns in relatorios table
            sql += """
                GROUP BY r.id
                ORDER BY distance
                LIMIT :limit
            """
            
            params['limit'] = limit
            
            # Execute query
            result = db.execute(text(sql), params)
            
            # Convert results to Report objects with scores
            reports_with_scores = []
            for row in result:
                # Reconstruct the Report object
                report = db.query(Relatorio).filter_by(id=row[0]).first()
                if report:
                    # Convert distance to similarity score (inverse)
                    # Lower distance = higher similarity
                    distance = row[-1]  # Last column is distance
                    similarity = 1.0 / (1.0 + distance)  # Simple conversion
                    
                    # Apply threshold if specified
                    if threshold is None or similarity >= threshold:
                        reports_with_scores.append((report, similarity))
            
            return reports_with_scores
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    @staticmethod
    def get_report_context(
        db: Session,
        report_ids: List[int],
        section: Optional[str] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get context from specific reports
        
        Args:
            db: Database session
            report_ids: List of report IDs
            section: Optional specific section to retrieve
        
        Returns:
            Dictionary mapping report_id to context data
        """
        context = {}
        
        for report_id in report_ids:
            report = db.query(Relatorio).filter_by(id=report_id).first()
            if not report:
                continue
            
            report_context = {
                'company': report.empresa_razao_social,
                'year': report.ano,
                'period': report.periodo.value if report.periodo else None,
                'course': report.curso.value if report.curso else None,
            }
            
            # Get specific sections if requested
            if section:
                if section in report.json_completo:
                    # Apply privacy filter
                    filtered_content = PrivacyFilter.filter_string(
                        str(report.json_completo.get(section, ''))
                    )
                    report_context[section] = filtered_content
            else:
                # Get main sections with privacy filtering
                json_data = report.json_completo
                
                if 'sobre_empresa' in json_data:
                    report_context['sobre_empresa'] = PrivacyFilter.filter_string(
                        json_data['sobre_empresa']
                    )[:500]  # Limit length
                
                if 'conclusao' in json_data:
                    report_context['conclusao'] = PrivacyFilter.filter_string(
                        json_data['conclusao']
                    )[:500]
            
            context[report_id] = report_context
        
        return context
    
    @staticmethod
    def find_reports_by_terms(
        db: Session,
        terms: List[str],
        limit: int = 20
    ) -> List[Relatorio]:
        """
        Find reports that contain specific technical terms
        
        Args:
            db: Database session
            terms: List of technical terms to search for
            limit: Maximum number of results
        
        Returns:
            List of reports containing the terms
        """
        try:
            # Build query to find reports with these terms
            sql = """
                SELECT DISTINCT r.*, COUNT(DISTINCT tt.termo_normalizado) as term_count
                FROM relatorios r
                JOIN relatorio_termos rt ON r.id = rt.relatorio_id
                JOIN termos_tecnicos tt ON tt.id = rt.termo_id
                WHERE LOWER(tt.termo_normalizado) IN :terms
                GROUP BY r.id
                ORDER BY term_count DESC, r.id DESC
                LIMIT :limit
            """
            
            # Normalize terms for comparison
            normalized_terms = tuple(term.lower() for term in terms)
            
            result = db.execute(
                text(sql),
                {"terms": normalized_terms, "limit": limit}
            )
            
            # Get Report objects
            report_ids = [row[0] for row in result]
            reports = db.query(Relatorio).filter(Relatorio.id.in_(report_ids)).all()
            
            return reports
            
        except Exception as e:
            logger.error(f"Error finding reports by terms: {e}")
            return []
