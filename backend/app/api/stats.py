"""
Statistics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional
import logging

from backend.app.db.database import get_db
from backend.app.schemas.schemas import StatsRequest, StatsResponse
from backend.app.models.models import Relatorio, TermoTecnico, RelatorioTermo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=StatsResponse)
async def get_statistics(
    request: StatsRequest,
    db: Session = Depends(get_db)
):
    """
    Get statistics based on the requested metric
    """
    try:
        # Build filters
        filters = []
        params = {}
        
        if request.filters:
            if 'year' in request.filters:
                filters.append("r.ano = :year")
                params['year'] = request.filters['year']
            
            if 'course' in request.filters:
                filters.append("r.curso = :course")
                params['course'] = request.filters['course']
            
            if 'period' in request.filters:
                filters.append("r.periodo = :period")
                params['period'] = request.filters['period']
        
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        # Process different metrics
        if request.metric == "top_technologies":
            sql = f"""
                SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
                FROM relatorio_termos rt
                JOIN termos_tecnicos tt ON tt.id = rt.termo_id
                JOIN relatorios r ON r.id = rt.relatorio_id
                WHERE {where_clause}
                GROUP BY tt.termo_normalizado
                ORDER BY count DESC
                LIMIT 20
            """
            
            result = db.execute(text(sql), params)
            data = {row[0]: row[1] for row in result}
            
        elif request.metric == "top_companies":
            sql = f"""
                SELECT empresa_razao_social, COUNT(*) as count
                FROM relatorios r
                WHERE empresa_razao_social IS NOT NULL AND {where_clause}
                GROUP BY empresa_razao_social
                ORDER BY count DESC
                LIMIT 15
            """
            
            result = db.execute(text(sql), params)
            data = {row[0]: row[1] for row in result}
            
        elif request.metric == "reports_by_year":
            sql = """
                SELECT ano, COUNT(*) as count
                FROM relatorios
                GROUP BY ano
                ORDER BY ano DESC
            """
            
            result = db.execute(text(sql))
            data = {str(row[0]): row[1] for row in result}
            
        elif request.metric == "reports_by_course":
            sql = f"""
                SELECT curso, COUNT(*) as count
                FROM relatorios r
                WHERE {where_clause}
                GROUP BY curso
            """
            
            result = db.execute(text(sql), params)
            data = {row[0]: row[1] for row in result}
            
        elif request.metric == "technologies_by_type":
            sql = f"""
                SELECT tt.tipo, COUNT(DISTINCT rt.relatorio_id) as count
                FROM relatorio_termos rt
                JOIN termos_tecnicos tt ON tt.id = rt.termo_id
                JOIN relatorios r ON r.id = rt.relatorio_id
                WHERE {where_clause}
                GROUP BY tt.tipo
                ORDER BY count DESC
            """
            
            result = db.execute(text(sql), params)
            data = {row[0]: row[1] for row in result}
            
        elif request.metric == "programming_languages":
            sql = f"""
                SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
                FROM relatorio_termos rt
                JOIN termos_tecnicos tt ON tt.id = rt.termo_id
                JOIN relatorios r ON r.id = rt.relatorio_id
                WHERE tt.tipo = 'LINGUAGEM' AND {where_clause}
                GROUP BY tt.termo_normalizado
                ORDER BY count DESC
                LIMIT 15
            """
            
            result = db.execute(text(sql), params)
            data = {row[0]: row[1] for row in result}
            
        elif request.metric == "frameworks":
            sql = f"""
                SELECT tt.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
                FROM relatorio_termos rt
                JOIN termos_tecnicos tt ON tt.id = rt.termo_id
                JOIN relatorios r ON r.id = rt.relatorio_id
                WHERE tt.tipo = 'FRAMEWORK' AND {where_clause}
                GROUP BY tt.termo_normalizado
                ORDER BY count DESC
                LIMIT 15
            """
            
            result = db.execute(text(sql), params)
            data = {row[0]: row[1] for row in result}
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown metric: {request.metric}. "
                       "Available metrics: top_technologies, top_companies, reports_by_year, "
                       "reports_by_course, technologies_by_type, programming_languages, frameworks"
            )
        
        # Get total reports count
        total_sql = f"SELECT COUNT(*) FROM relatorios r WHERE {where_clause}"
        total_reports = db.execute(text(total_sql), params).scalar()
        
        # Get period info if filters include year
        period_str = None
        if request.filters and 'year' in request.filters:
            period_str = str(request.filters['year'])
        
        return StatsResponse(
            metric=request.metric,
            data=data,
            period=period_str,
            total_reports=total_reports
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Error generating statistics")


@router.get("/summary")
async def get_summary_statistics(db: Session = Depends(get_db)):
    """
    Get summary statistics about the database
    """
    try:
        summary = {
            "total_reports": db.query(func.count(Relatorio.id)).scalar(),
            "total_companies": db.query(func.count(func.distinct(Relatorio.empresa_razao_social))).scalar(),
            "total_terms": db.query(func.count(TermoTecnico.id)).scalar(),
            "reports_by_year": {},
            "reports_by_course": {}
        }
        
        # Reports by year
        year_result = db.execute(text("""
            SELECT ano, COUNT(*) FROM relatorios 
            GROUP BY ano ORDER BY ano DESC
        """))
        summary["reports_by_year"] = {str(row[0]): row[1] for row in year_result}
        
        # Reports by course
        course_result = db.execute(text("""
            SELECT curso, COUNT(*) FROM relatorios 
            GROUP BY curso
        """))
        summary["reports_by_course"] = {row[0]: row[1] for row in course_result}
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting summary statistics: {e}")
        raise HTTPException(status_code=500, detail="Error getting summary statistics")
