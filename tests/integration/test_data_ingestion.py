#!/usr/bin/env python3
"""
Integration test for the data ingestion pipeline
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import (
    Relatorio, RelatorioEmbedding, RelatorioTermo, TermoTecnico
)
from backend.app.core.config import settings


def test_reports_loaded():
    """Test that reports are loaded in the database"""
    print("\n1. Testing reports are loaded...")
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count reports
        report_count = session.query(Relatorio).count()
        print(f"   ✓ Found {report_count} reports in database")
        
        # Check metadata
        sample_report = session.query(Relatorio).first()
        if sample_report:
            print(f"   ✓ Sample report has metadata:")
            print(f"      - Year: {sample_report.ano}")
            print(f"      - Period: {sample_report.periodo.value}")
            print(f"      - Academic Year: {sample_report.ano_academico.value}")
            print(f"      - Course: {sample_report.curso.value}")
            print(f"      - Company: {sample_report.empresa_razao_social}")
        
        # Check different courses
        computacao_count = session.query(Relatorio).filter_by(curso='COMPUTACAO').count()
        eletrica_count = session.query(Relatorio).filter_by(curso='ELETRICA').count()
        print(f"   ✓ Reports by course:")
        print(f"      - Engenharia de Computação: {computacao_count}")
        print(f"      - Engenharia Elétrica: {eletrica_count}")
        
        session.close()
        return report_count > 0
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        session.close()
        return False


def test_embeddings_generated():
    """Test that embeddings are generated for reports"""
    print("\n2. Testing embeddings generation...")
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count embeddings
        embedding_count = session.query(RelatorioEmbedding).count()
        print(f"   ✓ Found {embedding_count} embeddings in database")
        
        # Check sections
        sections = session.execute(text("""
            SELECT secao, COUNT(*) as count
            FROM relatorio_embeddings
            GROUP BY secao
            ORDER BY secao
        """))
        
        print("   ✓ Embeddings by section:")
        for row in sections:
            print(f"      - {row[0]}: {row[1]} embeddings")
        
        # Test vector search
        result = session.execute(text("""
            SELECT COUNT(*) FROM relatorio_embeddings 
            WHERE embedding IS NOT NULL
        """))
        non_null_count = result.scalar()
        print(f"   ✓ Valid embeddings (non-null): {non_null_count}")
        
        session.close()
        return embedding_count > 0
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        session.close()
        return False


def test_terms_extracted():
    """Test that technical terms are extracted"""
    print("\n3. Testing term extraction...")
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count term-report relationships
        relationship_count = session.query(RelatorioTermo).count()
        print(f"   ✓ Found {relationship_count} term-report relationships")
        
        # Reports with terms
        reports_with_terms = session.execute(text("""
            SELECT COUNT(DISTINCT relatorio_id) FROM relatorio_termos
        """)).scalar()
        print(f"   ✓ Reports with extracted terms: {reports_with_terms}")
        
        # Most common terms
        result = session.execute(text("""
            SELECT t.termo_normalizado, COUNT(DISTINCT rt.relatorio_id) as count
            FROM relatorio_termos rt
            JOIN termos_tecnicos t ON t.id = rt.termo_id
            GROUP BY t.termo_normalizado
            ORDER BY count DESC
            LIMIT 5
        """))
        
        print("   ✓ Top 5 most common terms:")
        for row in result:
            print(f"      - {row[0]}: found in {row[1]} reports")
        
        session.close()
        return relationship_count > 0
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        session.close()
        return False


def test_search_capability():
    """Test vector search capability"""
    print("\n4. Testing search capability...")
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Test a simple vector similarity search
        # Using a dummy vector for testing
        test_vector = [0.1] * 1536
        
        result = session.execute(text("""
            SELECT r.id, r.empresa_razao_social,
                   e.embedding <-> CAST(:test_vector AS vector) as distance
            FROM relatorio_embeddings e
            JOIN relatorios r ON r.id = e.relatorio_id
            WHERE e.embedding IS NOT NULL
            ORDER BY distance
            LIMIT 5
        """), {"test_vector": str(test_vector)})
        
        print("   ✓ Vector search works, top 5 results:")
        count = 0
        for row in result:
            count += 1
            print(f"      - Report {row[0]} ({row[1]}): distance {row[2]:.4f}")
        
        if count > 0:
            print(f"   ✓ Successfully retrieved {count} similar reports")
            return True
        else:
            print("   ⚠️  No results found (embeddings may not be generated yet)")
            return False
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        session.close()
        return False


def test_data_statistics():
    """Display overall data statistics"""
    print("\n5. Data Statistics...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Overall stats
            stats = {}
            
            stats['reports'] = conn.execute(text("SELECT COUNT(*) FROM relatorios")).scalar()
            stats['embeddings'] = conn.execute(text("SELECT COUNT(*) FROM relatorio_embeddings")).scalar()
            stats['terms'] = conn.execute(text("SELECT COUNT(*) FROM termos_tecnicos")).scalar()
            stats['term_relationships'] = conn.execute(text("SELECT COUNT(*) FROM relatorio_termos")).scalar()
            
            print("   📊 Database Statistics:")
            print(f"      - Reports: {stats['reports']}")
            print(f"      - Embeddings: {stats['embeddings']}")
            print(f"      - Technical Terms: {stats['terms']}")
            print(f"      - Term-Report Relations: {stats['term_relationships']}")
            
            # Company distribution
            result = conn.execute(text("""
                SELECT empresa_razao_social, COUNT(*) as count
                FROM relatorios
                WHERE empresa_razao_social IS NOT NULL
                GROUP BY empresa_razao_social
                ORDER BY count DESC
                LIMIT 5
            """))
            
            print("\n   📊 Top 5 Companies by Report Count:")
            for row in result:
                print(f"      - {row[0]}: {row[1]} reports")
            
            # Year distribution
            result = conn.execute(text("""
                SELECT ano, COUNT(*) as count
                FROM relatorios
                GROUP BY ano
                ORDER BY ano
            """))
            
            print("\n   📊 Reports by Year:")
            for row in result:
                print(f"      - {row[0]}: {row[1]} reports")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def main():
    """Run all integration tests"""
    print("=" * 60)
    print("DATA INGESTION INTEGRATION TESTS")
    print("=" * 60)
    
    tests = [
        test_reports_loaded,
        test_embeddings_generated,
        test_terms_extracted,
        test_search_capability,
        test_data_statistics
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"   ✗ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed!")
        print("\nThe data ingestion pipeline is working correctly!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("\nSome components may need attention.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
