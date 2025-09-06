#!/usr/bin/env python3
"""
Generate embeddings for report sections using OpenAI API
"""
import sys
import os
import json
from typing import List, Dict, Optional
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import Relatorio, RelatorioEmbedding
from backend.app.core.config import settings
from openai import OpenAI
from dotenv import load_dotenv
from google import genai
from google.genai import types
# Load environment variables
load_dotenv()

# Initialize OpenAI client
#client = OpenAI(api_key=settings.OPENAI_API_KEY)

client = genai.Client()



def extract_atividades_text(atividades: List[Dict]) -> str:
    """
    Extract and combine text from atividades_realizadas section
    """
    if not atividades:
        return ""
    
    text_parts = []
    for i, atividade in enumerate(atividades, 1):
        parts = []
        if atividade.get('descricao'):
            parts.append(f"Atividade {i}: {atividade['descricao']}")
        if atividade.get('tarefas_realizadas'):
            parts.append(f"Tarefas: {atividade['tarefas_realizadas']}")
        if atividade.get('papel_exercido'):
            parts.append(f"Papel: {atividade['papel_exercido']}")
        if atividade.get('aprendizados'):
            parts.append(f"Aprendizados: {atividade['aprendizados']}")
        if atividade.get('comentarios'):
            parts.append(f"Comentários: {atividade['comentarios']}")
        
        if parts:
            text_parts.append(" ".join(parts))
    
    return "\n\n".join(text_parts)


def generate_embedding(text: str, max_retries: int = 3) -> Optional[List[float]]:
    """
    Generate embedding for text using OpenAI API with retry logic
    """
    if not text or not text.strip():
        return None
    
    for attempt in range(max_retries):
        try:
            # Truncate text if too long (OpenAI has token limits)
            max_chars = 18000  # Conservative limit
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            # response = client.embeddings.create(
            #     model="text-embedding-3-small",  # Cheaper and faster model
            #     input=text,
            #     dimensions=1536  # Match our database schema
            #         config=types.EmbedContentConfig(output_dimensionality=768)

            # )
            
            # return response.data[0].embedding

            result = client.models.embed_content(
                model='gemini-embedding-001',
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=1536,
                    task_type="retrieval_document",
                    title="Document chunk"
                    )
                )
            
        ## google ai embedding:
            if result.embeddings:
                print('tamanho embedding', len(result.embeddings[0].values) if result.embeddings else None)
                return result.embeddings[0].values

            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"      Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"      ❌ Failed after {max_retries} attempts: {e}")
                return None


def process_report_embeddings(session, report: Relatorio) -> Dict[str, bool]:
    """
    Generate embeddings for all sections of a report
    """
    results = {}
    json_data = report.json_completo
    
    # Check if embeddings already exist
    existing_embeddings = session.query(RelatorioEmbedding).filter_by(
        relatorio_id=report.id
    ).all()
    
    existing_sections = {e.secao for e in existing_embeddings}
    
    sections_to_process = []
    
    # 1. Sobre a empresa
    if 'sobre_empresa' not in existing_sections:
        sobre_empresa = json_data.get('sobre_empresa', '')
        if sobre_empresa:
            sections_to_process.append(('sobre_empresa', sobre_empresa))
    
    # 2. Atividades realizadas
    if 'atividades_realizadas' not in existing_sections:
        atividades = json_data.get('atividades_realizadas', [])
        atividades_text = extract_atividades_text(atividades)
        if atividades_text:
            sections_to_process.append(('atividades_realizadas', atividades_text))
    
    # 3. Conclusão
    if 'conclusao' not in existing_sections:
        conclusao = json_data.get('conclusao', '')
        if conclusao:
            sections_to_process.append(('conclusao', conclusao))
    
    if not sections_to_process:
        print(f"   ⚠️  Report {report.id}: All embeddings already exist")
        return {'skipped': True}
    
    # Generate embeddings for missing sections
    for secao, conteudo in sections_to_process:
        print(f"      Generating embedding for '{secao}'...")
        embedding = generate_embedding(conteudo)
        if embedding:
            embedding_obj = RelatorioEmbedding(
                relatorio_id=report.id,
                secao=secao,
                conteudo=conteudo[:5000],  # Store truncated content
                embedding=embedding,
                modelo='gemini-embedding-001'
            )
            session.add(embedding_obj)
            results[secao] = True
        else:
            results[secao] = False
    
    if any(results.values()):
        session.commit()
    
    return results


def generate_all_embeddings():
    """
    Generate embeddings for all reports in the database
    """
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Get all reports
    reports = session.query(Relatorio).all()
    total_reports = len(reports)
    
    print(f"Found {total_reports} reports to process")
    print("=" * 60)
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'embeddings_created': 0
    }
    
    for i, report in enumerate(reports, 1):
        print(f"\n[{i}/{total_reports}] Processing report ID {report.id}")
        print(f"   Company: {report.empresa_razao_social}")
        
        try:
            results = process_report_embeddings(session, report)
            
            if results.get('skipped'):
                stats['skipped'] += 1
            else:
                stats['processed'] += 1
                successful_sections = sum(1 for v in results.values() if v is True)
                stats['embeddings_created'] += successful_sections
                print(f"   ✅ Generated {successful_sections} embeddings")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats['errors'] += 1
            session.rollback()
        
        # Rate limiting (be nice to OpenAI API)
        if i < total_reports:
            time.sleep(0.5)  # Small delay between reports
    
    session.close()
    
    print("\n" + "=" * 60)
    print("EMBEDDING GENERATION SUMMARY")
    print("=" * 60)
    print(f"✅ Processed: {stats['processed']} reports")
    print(f"⚠️  Skipped: {stats['skipped']} reports")
    print(f"❌ Errors: {stats['errors']} reports")
    print(f"🎯 Total embeddings created: {stats['embeddings_created']}")
    
    # Query final count
    session = Session()
    total_embeddings = session.query(RelatorioEmbedding).count()
    print(f"📊 Total embeddings in database: {total_embeddings}")
    session.close()


def main():
    """Main function"""
    if not settings.GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not found in environment variables!")
        print("Please set it in your .env file")
        return
    
    print("=" * 60)
    print("EMBEDDING GENERATION SCRIPT")
    print("=" * 60)
    print("Using OpenAI model: gemini-embedding-001")
    print("Embedding dimensions: 1536")
    print("=" * 60 + "\n")
    
    generate_all_embeddings()


if __name__ == "__main__":
    main()
