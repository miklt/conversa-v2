#!/usr/bin/env python3
"""
Extract and map technical terms from reports to the normalized terms table
"""
import sys
import os
import re
from typing import List, Dict, Set
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import (
    Relatorio, RelatorioTermo, TermoTecnico
)
from backend.app.core.config import settings


def extract_terms_from_text(text: str, termos_dict: Dict[str, int]) -> List[int]:
    """
    Extract technical terms from text using case-insensitive matching
    Returns list of term IDs found in the text
    """
    if not text:
        return []
    
    found_terms = set()
    text_lower = text.lower()
    
    # Check each known term
    for termo, termo_id in termos_dict.items():
        # Use word boundaries for more accurate matching
        # This prevents matching "Java" in "JavaScript"
        pattern = r'\b' + re.escape(termo.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_terms.add(termo_id)
    
    return list(found_terms)


def process_report_terms(session, report: Relatorio, termos_dict: Dict[str, int]) -> Dict:
    """
    Extract and map terms from a single report
    """
    stats = {
        'sobre_empresa': 0,
        'atividades_realizadas': 0,
        'conclusao': 0,
        'total': 0
    }
    
    # Check if terms already extracted for this report
    existing_terms = session.query(RelatorioTermo).filter_by(
        relatorio_id=report.id
    ).all()
    
    if existing_terms:
        return {'skipped': True, 'existing': len(existing_terms)}
    
    json_data = report.json_completo
    all_terms = []
    
    # 1. Extract from sobre_empresa
    sobre_empresa = json_data.get('sobre_empresa', '')
    if sobre_empresa:
        terms = extract_terms_from_text(sobre_empresa, termos_dict)
        for termo_id in terms:
            all_terms.append((termo_id, 'sobre_empresa'))
        stats['sobre_empresa'] = len(terms)
    
    # 2. Extract from atividades_realizadas
    atividades = json_data.get('atividades_realizadas', [])
    for atividade in atividades:
        combined_text = ' '.join([
            str(atividade.get('descricao') or ''),
            str(atividade.get('tarefas_realizadas') or ''),
            str(atividade.get('papel_exercido') or ''),
            str(atividade.get('aprendizados') or ''),
            str(atividade.get('comentarios') or '')
        ])
        
        terms = extract_terms_from_text(combined_text, termos_dict)
        for termo_id in terms:
            all_terms.append((termo_id, 'atividades_realizadas'))
    
    # Count unique terms in atividades
    atividades_terms = {t[0] for t in all_terms if t[1] == 'atividades_realizadas'}
    stats['atividades_realizadas'] = len(atividades_terms)
    
    # 3. Extract from conclusao
    conclusao = json_data.get('conclusao', '')
    if conclusao:
        terms = extract_terms_from_text(conclusao, termos_dict)
        for termo_id in terms:
            all_terms.append((termo_id, 'conclusao'))
        stats['conclusao'] = len(terms)
    
    # Count frequency by section
    term_section_count = Counter(all_terms)
    
    # Insert relationships
    for (termo_id, secao), frequencia in term_section_count.items():
        relatorio_termo = RelatorioTermo(
            relatorio_id=report.id,
            termo_id=termo_id,
            secao=secao,
            frequencia=frequencia
        )
        session.add(relatorio_termo)
    
    stats['total'] = len({t[0] for t in all_terms})  # Unique terms count
    
    if all_terms:
        session.commit()
    
    return stats


def extract_all_terms():
    """
    Extract terms from all reports in the database
    """
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Load all technical terms into memory for faster lookup
    termos = session.query(TermoTecnico).all()
    termos_dict = {termo.termo: termo.id for termo in termos}
    
    print(f"Loaded {len(termos_dict)} technical terms")
    
    # Get all reports
    reports = session.query(Relatorio).all()
    total_reports = len(reports)
    
    print(f"Found {total_reports} reports to process")
    print("=" * 60)
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'total_terms_found': 0
    }
    
    for i, report in enumerate(reports, 1):
        print(f"\n[{i}/{total_reports}] Processing report ID {report.id}")
        print(f"   Company: {report.empresa_razao_social}")
        
        try:
            results = process_report_terms(session, report, termos_dict)
            
            if results.get('skipped'):
                stats['skipped'] += 1
                print(f"   ⚠️  Skipped (already has {results.get('existing', 0)} terms)")
            else:
                stats['processed'] += 1
                stats['total_terms_found'] += results.get('total', 0)
                print(f"   ✅ Found terms: {results.get('total', 0)}")
                print(f"      - sobre_empresa: {results.get('sobre_empresa', 0)}")
                print(f"      - atividades: {results.get('atividades_realizadas', 0)}")
                print(f"      - conclusao: {results.get('conclusao', 0)}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats['errors'] += 1
            session.rollback()
    
    session.close()
    
    print("\n" + "=" * 60)
    print("TERM EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"✅ Processed: {stats['processed']} reports")
    print(f"⚠️  Skipped: {stats['skipped']} reports")
    print(f"❌ Errors: {stats['errors']} reports")
    print(f"🎯 Total terms found: {stats['total_terms_found']}")
    
    # Query statistics
    session = Session()
    
    # Most common terms
    print("\n📊 TOP 10 MOST COMMON TERMS:")
    print("-" * 40)
    
    result = session.execute("""
        SELECT t.termo_normalizado, t.tipo, COUNT(DISTINCT rt.relatorio_id) as report_count
        FROM relatorio_termos rt
        JOIN termos_tecnicos t ON t.id = rt.termo_id
        GROUP BY t.termo_normalizado, t.tipo
        ORDER BY report_count DESC
        LIMIT 10
    """)
    
    for row in result:
        print(f"   {row[0]:<20} ({row[1]:<15}): {row[2]} reports")
    
    # Terms by type
    print("\n📊 TERMS BY TYPE:")
    print("-" * 40)
    
    result = session.execute("""
        SELECT t.tipo, COUNT(DISTINCT rt.relatorio_id, rt.termo_id) as term_report_pairs
        FROM relatorio_termos rt
        JOIN termos_tecnicos t ON t.id = rt.termo_id
        GROUP BY t.tipo
        ORDER BY term_report_pairs DESC
    """)
    
    for row in result:
        print(f"   {row[0]:<20}: {row[1]} term-report pairs")
    
    session.close()


def main():
    """Main function"""
    print("=" * 60)
    print("TECHNICAL TERM EXTRACTION SCRIPT")
    print("=" * 60 + "\n")
    
    extract_all_terms()


if __name__ == "__main__":
    main()
