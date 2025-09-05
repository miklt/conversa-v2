#!/usr/bin/env python3
"""
Import JSON reports into the database with metadata extraction
"""
import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import (
    Relatorio, CursoEnum, PeriodoEnum, AnoAcademicoEnum
)
from backend.app.core.config import settings


def parse_folder_name(folder_name):
    """
    Parse folder name to extract metadata
    Format: {ano}-{periodo}-{ano_academico}roAno-{ordinal_estagio}
    Example: 2025-2Q-3roAno-1
    """
    pattern = r'(\d{4})-(\w+)-(\d)roAno-(\d)'
    match = re.match(pattern, folder_name)
    
    if not match:
        raise ValueError(f"Invalid folder name format: {folder_name}")
    
    ano = int(match.group(1))
    periodo_str = match.group(2)
    ano_academico_num = match.group(3)
    ordinal_estagio = int(match.group(4))
    
    # Map periodo string to enum
    periodo_map = {
        '1S': PeriodoEnum.PRIMEIRO_SEMESTRE,
        '2S': PeriodoEnum.SEGUNDO_SEMESTRE,
        '1Q': PeriodoEnum.PRIMEIRO_QUADRIMESTRE,
        '2Q': PeriodoEnum.SEGUNDO_QUADRIMESTRE,
        '3Q': PeriodoEnum.TERCEIRO_QUADRIMESTRE
    }
    
    if periodo_str not in periodo_map:
        raise ValueError(f"Invalid period: {periodo_str}")
    
    periodo = periodo_map[periodo_str]
    
    # Map ano academico to enum
    ano_academico_map = {
        '2': AnoAcademicoEnum.SEGUNDO,
        '3': AnoAcademicoEnum.TERCEIRO,
        '4': AnoAcademicoEnum.QUARTO,
        '5': AnoAcademicoEnum.QUINTO
    }
    
    if ano_academico_num not in ano_academico_map:
        raise ValueError(f"Invalid academic year: {ano_academico_num}")
    
    ano_academico = ano_academico_map[ano_academico_num]
    
    return {
        'ano': ano,
        'periodo': periodo,
        'ano_academico': ano_academico,
        'ordinal_estagio': ordinal_estagio
    }


def determine_curso(json_data, periodo):
    """
    Determine the course type based on content and period
    """
    # Check the periodo type
    if periodo in [PeriodoEnum.PRIMEIRO_QUADRIMESTRE, 
                    PeriodoEnum.SEGUNDO_QUADRIMESTRE, 
                    PeriodoEnum.TERCEIRO_QUADRIMESTRE]:
        return CursoEnum.COMPUTACAO
    elif periodo in [PeriodoEnum.PRIMEIRO_SEMESTRE, 
                      PeriodoEnum.SEGUNDO_SEMESTRE]:
        return CursoEnum.ELETRICA
    
    # Fallback: check if curso field contains "Computação"
    curso_field = json_data.get('estagiario', {}).get('curso', '')
    if 'Computação' in curso_field or 'Computacao' in curso_field:
        return CursoEnum.COMPUTACAO
    else:
        return CursoEnum.ELETRICA


def extract_year_from_date(date_str):
    """
    Try to extract year from date string
    """
    if not date_str:
        return None
    
    # Try to find 4-digit year
    year_match = re.search(r'\b(20\d{2})\b', date_str)
    if year_match:
        return int(year_match.group(1))
    
    return None


def import_json_file(session, file_path, folder_metadata):
    """
    Import a single JSON file into the database
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Extract empresa info
        empresa_razao_social = json_data.get('estagio', {}).get('razao_social_empresa')
        if not empresa_razao_social:
            # Try alternative field name
            empresa_razao_social = json_data.get('estagio', {}).get('empresa_razao_social')
        
        empresa_cnpj = json_data.get('estagio', {}).get('cnpj')
        if not empresa_cnpj:
            empresa_cnpj = json_data.get('estagio', {}).get('empresa_cnpj')
        
        # Try to extract year from dates if not in folder
        if not folder_metadata.get('ano'):
            periodo_inicio = json_data.get('estagio', {}).get('periodo_inicio')
            ano_from_date = extract_year_from_date(periodo_inicio)
            if ano_from_date:
                folder_metadata['ano'] = ano_from_date
        
        # Determine curso
        curso = determine_curso(json_data, folder_metadata['periodo'])
        
        # Check if report already exists (by arquivo_origem)
        arquivo_origem = file_path.name
        existing = session.query(Relatorio).filter_by(
            arquivo_origem=arquivo_origem,
            folder_origin=file_path.parent.name
        ).first()
        
        if existing:
            print(f"  ⚠️  Skipping (already exists): {arquivo_origem}")
            return False
        
        # Create new report
        report = Relatorio(
            json_completo=json_data,
            ano=folder_metadata['ano'],
            periodo=folder_metadata['periodo'],
            ano_academico=folder_metadata['ano_academico'],
            ordinal_estagio=folder_metadata['ordinal_estagio'],
            curso=curso,
            empresa_razao_social=empresa_razao_social,
            empresa_cnpj=empresa_cnpj,
            folder_origin=file_path.parent.name,
            arquivo_origem=arquivo_origem
        )
        
        session.add(report)
        session.commit()
        
        print(f"  ✅ Imported: {arquivo_origem} (ID: {report.id})")
        return True
        
    except Exception as e:
        print(f"  ❌ Error importing {file_path.name}: {e}")
        session.rollback()
        return False


def import_all_json_files():
    """
    Import all JSON files from the arquivos/json_saida directory
    """
    base_dir = Path('arquivos/json_saida')
    
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    total_imported = 0
    total_skipped = 0
    total_errors = 0
    
    # Iterate through folders
    for folder in base_dir.iterdir():
        if not folder.is_dir():
            continue
        
        print(f"\n📁 Processing folder: {folder.name}")
        
        try:
            # Parse folder metadata
            folder_metadata = parse_folder_name(folder.name)
            print(f"   Year: {folder_metadata['ano']}, "
                  f"Period: {folder_metadata['periodo'].value}, "
                  f"Academic Year: {folder_metadata['ano_academico'].value}, "
                  f"Internship #: {folder_metadata['ordinal_estagio']}")
        except ValueError as e:
            print(f"  ⚠️  Skipping folder (invalid format): {e}")
            continue
        
        # Process JSON files in folder
        json_files = list(folder.glob('*.json'))
        print(f"   Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            result = import_json_file(session, json_file, folder_metadata)
            if result:
                total_imported += 1
            elif result is False:
                total_skipped += 1
            else:
                total_errors += 1
    
    session.close()
    
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"✅ Imported: {total_imported} reports")
    print(f"⚠️  Skipped (already exists): {total_skipped} reports")
    print(f"❌ Errors: {total_errors} reports")
    print(f"📊 Total in database: {session.query(Relatorio).count()} reports")


def main():
    """Main function"""
    print("=" * 60)
    print("JSON REPORT IMPORT SCRIPT")
    print("=" * 60)
    
    import_all_json_files()


if __name__ == "__main__":
    main()
