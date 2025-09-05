"""
Reports API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import logging

from backend.app.db.database import get_db
from backend.app.schemas.schemas import ReportSearchRequest, SearchResponse, ReportSummary
from backend.app.services.privacy_filter import PrivacyFilter
from backend.app.services.vector_search import VectorSearchService
from backend.app.models.models import Relatorio, TermoTecnico, RelatorioTermo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_reports(
    request: ReportSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for reports based on query and filters
    """
    try:
        # Extract technical terms from query
        query_lower = request.query.lower()
        found_terms = []
        
        # Find matching technical terms
        all_terms = db.query(TermoTecnico).all()
        for term in all_terms:
            if term.termo.lower() in query_lower or term.termo_normalizado.lower() in query_lower:
                found_terms.append(term.termo_normalizado)
        
        logger.info(f"Found terms in query: {found_terms}")
        
        # Search by terms if found
        if found_terms:
            reports = VectorSearchService.find_reports_by_terms(
                db, found_terms, limit=request.limit
            )
        else:
            # Fallback to basic text search
            sql = """
                SELECT DISTINCT r.*
                FROM relatorios r
                WHERE (
                    r.json_completo::text ILIKE :query
                    OR r.empresa_razao_social ILIKE :query
                )
            """
            
            params = {"query": f"%{request.query}%"}
            
            # Add filters
            if request.filters:
                if 'year' in request.filters:
                    sql += " AND r.ano = :year"
                    params['year'] = request.filters['year']
                
                if 'course' in request.filters:
                    sql += " AND r.curso = :course"
                    params['course'] = request.filters['course']
            
            sql += f" LIMIT {request.limit}"
            
            result = db.execute(text(sql), params)
            report_ids = [row[0] for row in result]
            reports = db.query(Relatorio).filter(Relatorio.id.in_(report_ids)).all()
        
        # Convert to response format
        results = []
        for report in reports:
            # Get associated technologies
            tech_terms = db.query(TermoTecnico).join(RelatorioTermo).filter(
                RelatorioTermo.relatorio_id == report.id
            ).limit(10).all()
            
            technologies = [term.termo_normalizado for term in tech_terms]
            
            # Create summary
            summary = ReportSummary(
                id=report.id,
                company=report.empresa_razao_social or "Unknown",
                year=report.ano,
                period=report.periodo.value if report.periodo else "Unknown",
                course=report.curso.value if report.curso else "Unknown",
                technologies=technologies,
                activities_summary=None  # Could extract from JSON if needed
            )
            results.append(summary)
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query_interpretation=f"Searched for: {', '.join(found_terms) if found_terms else request.query}"
        )
        
    except Exception as e:
        logger.error(f"Error searching reports: {e}")
        raise HTTPException(status_code=500, detail="Error searching reports")


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific report by ID (with privacy filtering)
    """
    try:
        report = db.query(Relatorio).filter_by(id=report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Apply privacy filter
        filtered_data = PrivacyFilter.filter_report_data(report.json_completo)
        
        return {
            "id": report.id,
            "company": report.empresa_razao_social,
            "year": report.ano,
            "period": report.periodo.value if report.periodo else None,
            "course": report.curso.value if report.curso else None,
            "data": filtered_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving report")
