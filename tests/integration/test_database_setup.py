#!/usr/bin/env python3
"""
Integration test to verify database setup and pgvector functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import (
    Base, Relatorio, RelatorioEmbedding, TermoTecnico, 
    CursoEnum, PeriodoEnum, AnoAcademicoEnum
)
from backend.app.core.config import settings
import json
import numpy as np


def test_database_connection():
    """Test database connection"""
    print("\n1. Testing database connection...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✓ Connected to PostgreSQL: {version[:50]}...")
            return True
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return False


def test_pgvector_extension():
    """Test pgvector extension"""
    print("\n2. Testing pgvector extension...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ))
            if result.fetchone():
                print("   ✓ pgvector extension is installed")
                
                # Test vector operations
                result = conn.execute(text(
                    "SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector as distance"
                ))
                distance = result.fetchone()[0]
                print(f"   ✓ Vector distance calculation works: {distance:.2f}")
                return True
            else:
                print("   ✗ pgvector extension is not installed")
                return False
    except Exception as e:
        print(f"   ✗ pgvector test failed: {e}")
        return False


def test_tables_exist():
    """Test if all tables exist"""
    print("\n3. Testing table existence...")
    expected_tables = [
        'relatorios', 'relatorio_embeddings', 'termos_tecnicos',
        'relatorio_termos', 'chat_sessions', 'chat_messages'
    ]
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public'"
            ))
            existing_tables = [row[0] for row in result]
            
            for table in expected_tables:
                if table in existing_tables:
                    print(f"   ✓ Table '{table}' exists")
                else:
                    print(f"   ✗ Table '{table}' does not exist")
                    return False
        return True
    except Exception as e:
        print(f"   ✗ Table check failed: {e}")
        return False


def test_insert_sample_data():
    """Test inserting sample data"""
    print("\n4. Testing data insertion...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create a sample report
        sample_report = Relatorio(
            json_completo={
                "estagiario": {
                    "nome_completo": "Teste Silva",
                    "curso": "Engenharia de Computação"
                },
                "estagio": {
                    "razao_social_empresa": "Empresa Teste LTDA",
                    "cnpj": "12.345.678/0001-90"
                },
                "sobre_empresa": "Esta é uma empresa de teste",
                "atividades_realizadas": [],
                "conclusao": "Conclusão de teste"
            },
            ano=2025,
            periodo=PeriodoEnum.SEGUNDO_QUADRIMESTRE,
            ano_academico=AnoAcademicoEnum.TERCEIRO,
            ordinal_estagio=1,
            curso=CursoEnum.COMPUTACAO,
            empresa_razao_social="Empresa Teste LTDA",
            empresa_cnpj="12.345.678/0001-90",
            folder_origin="2025-2Q-3roAno-1",
            arquivo_origem="teste.json"
        )
        
        session.add(sample_report)
        session.commit()
        print(f"   ✓ Sample report inserted with ID: {sample_report.id}")
        
        # Create a sample embedding
        sample_embedding = RelatorioEmbedding(
            relatorio_id=sample_report.id,
            secao="sobre_empresa",
            conteudo="Esta é uma empresa de teste",
            embedding=np.random.rand(1536).tolist()  # Random vector for testing
        )
        
        session.add(sample_embedding)
        session.commit()
        print(f"   ✓ Sample embedding inserted with ID: {sample_embedding.id}")
        
        # Query back the data
        report_count = session.query(Relatorio).count()
        embedding_count = session.query(RelatorioEmbedding).count()
        termo_count = session.query(TermoTecnico).count()
        
        print(f"\n   Database statistics:")
        print(f"   - Reports: {report_count}")
        print(f"   - Embeddings: {embedding_count}")
        print(f"   - Technical Terms: {termo_count}")
        
        # Clean up test data
        session.delete(sample_embedding)
        session.delete(sample_report)
        session.commit()
        print("\n   ✓ Test data cleaned up")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"   ✗ Data insertion failed: {e}")
        return False


def test_vector_similarity_search():
    """Test vector similarity search"""
    print("\n5. Testing vector similarity search...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create test reports with embeddings
        reports_data = [
            ("Python Development", [0.1, 0.2, 0.3]),
            ("Java Development", [0.4, 0.5, 0.6]),
            ("Machine Learning", [0.7, 0.8, 0.9])
        ]
        
        created_ids = []
        for title, vector_sample in reports_data:
            report = Relatorio(
                json_completo={"title": title},
                ano=2025,
                periodo=PeriodoEnum.PRIMEIRO_SEMESTRE,
                ano_academico=AnoAcademicoEnum.QUARTO,
                ordinal_estagio=1,
                curso=CursoEnum.ELETRICA,
                empresa_razao_social=f"Company for {title}"
            )
            session.add(report)
            session.flush()
            
            # Create full vector (1536 dimensions)
            full_vector = vector_sample * 512  # Repeat to get 1536 dimensions
            
            embedding = RelatorioEmbedding(
                relatorio_id=report.id,
                secao="atividades",
                conteudo=title,
                embedding=full_vector
            )
            session.add(embedding)
            created_ids.append((report.id, embedding.id))
        
        session.commit()
        print("   ✓ Test vectors inserted")
        
        # Test similarity search using raw SQL
        query_vector = [0.15, 0.25, 0.35] * 512  # Similar to first vector
        query_vector_str = '[' + ','.join(map(str, query_vector)) + ']'
        
        result = session.execute(
            text("""
                SELECT r.id, r.empresa_razao_social, 
                       e.embedding <-> CAST(:query_vector AS vector) as distance
                FROM relatorio_embeddings e
                JOIN relatorios r ON r.id = e.relatorio_id
                ORDER BY distance
                LIMIT 3
            """),
            {"query_vector": query_vector_str}
        )
        
        print("\n   Similarity search results:")
        for row in result:
            print(f"   - ID: {row[0]}, Company: {row[1]}, Distance: {row[2]:.4f}")
        
        # Clean up
        for report_id, embedding_id in created_ids:
            session.execute(text("DELETE FROM relatorio_embeddings WHERE id = :id"), {"id": embedding_id})
            session.execute(text("DELETE FROM relatorios WHERE id = :id"), {"id": report_id})
        session.commit()
        print("\n   ✓ Test vectors cleaned up")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"   ✗ Vector similarity search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("DATABASE INTEGRATION TESTS")
    print("=" * 60)
    
    tests = [
        test_database_connection,
        test_pgvector_extension,
        test_tables_exist,
        test_insert_sample_data,
        test_vector_similarity_search
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
        print("\nThe database is properly configured and ready to use.")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("\nPlease fix the failing tests before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
