#!/usr/bin/env python3
"""
Initialize database with schema and populate technical terms
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import Base, TermoTecnico, TipoTermoEnum
from backend.app.core.config import settings


def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    # Connect to PostgreSQL without specifying a database
    db_url_parts = settings.DATABASE_URL.rsplit('/', 1)
    postgres_url = f"{db_url_parts[0]}/postgres"
    db_name = db_url_parts[1].split('?')[0]
    
    engine = create_engine(postgres_url, isolation_level='AUTOCOMMIT')
    
    with engine.connect() as conn:
        # Check if database exists
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        )
        exists = result.fetchone() is not None
        
        if not exists:
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")


def init_database():
    """Initialize database schema and extensions"""
    engine = create_engine(settings.DATABASE_URL)
    
    # Create pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("pgvector extension enabled.")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    return engine


def populate_technical_terms(engine):
    """Populate technical terms table with initial data"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Define technical terms
    terms_data = [
        # Programming Languages
        ("Python", TipoTermoEnum.LINGUAGEM, "python"),
        ("python", TipoTermoEnum.LINGUAGEM, "python"),
        ("JavaScript", TipoTermoEnum.LINGUAGEM, "javascript"),
        ("javascript", TipoTermoEnum.LINGUAGEM, "javascript"),
        ("JS", TipoTermoEnum.LINGUAGEM, "javascript"),
        ("TypeScript", TipoTermoEnum.LINGUAGEM, "typescript"),
        ("typescript", TipoTermoEnum.LINGUAGEM, "typescript"),
        ("TS", TipoTermoEnum.LINGUAGEM, "typescript"),
        ("Java", TipoTermoEnum.LINGUAGEM, "java"),
        ("java", TipoTermoEnum.LINGUAGEM, "java"),
        ("C#", TipoTermoEnum.LINGUAGEM, "csharp"),
        ("CSharp", TipoTermoEnum.LINGUAGEM, "csharp"),
        ("C++", TipoTermoEnum.LINGUAGEM, "cpp"),
        ("cpp", TipoTermoEnum.LINGUAGEM, "cpp"),
        ("Go", TipoTermoEnum.LINGUAGEM, "go"),
        ("Golang", TipoTermoEnum.LINGUAGEM, "go"),
        ("Rust", TipoTermoEnum.LINGUAGEM, "rust"),
        ("Kotlin", TipoTermoEnum.LINGUAGEM, "kotlin"),
        ("Swift", TipoTermoEnum.LINGUAGEM, "swift"),
        ("PHP", TipoTermoEnum.LINGUAGEM, "php"),
        ("Ruby", TipoTermoEnum.LINGUAGEM, "ruby"),
        ("R", TipoTermoEnum.LINGUAGEM, "r"),
        ("SQL", TipoTermoEnum.LINGUAGEM, "sql"),
        ("MATLAB", TipoTermoEnum.LINGUAGEM, "matlab"),
        ("Scala", TipoTermoEnum.LINGUAGEM, "scala"),
        
        # Frameworks
        ("React", TipoTermoEnum.FRAMEWORK, "react"),
        ("React.js", TipoTermoEnum.FRAMEWORK, "react"),
        ("ReactJS", TipoTermoEnum.FRAMEWORK, "react"),
        ("React Native", TipoTermoEnum.FRAMEWORK, "react_native"),
        ("Angular", TipoTermoEnum.FRAMEWORK, "angular"),
        ("AngularJS", TipoTermoEnum.FRAMEWORK, "angular"),
        ("Vue", TipoTermoEnum.FRAMEWORK, "vue"),
        ("Vue.js", TipoTermoEnum.FRAMEWORK, "vue"),
        ("VueJS", TipoTermoEnum.FRAMEWORK, "vue"),
        ("Next.js", TipoTermoEnum.FRAMEWORK, "nextjs"),
        ("NextJS", TipoTermoEnum.FRAMEWORK, "nextjs"),
        ("Django", TipoTermoEnum.FRAMEWORK, "django"),
        ("Flask", TipoTermoEnum.FRAMEWORK, "flask"),
        ("FastAPI", TipoTermoEnum.FRAMEWORK, "fastapi"),
        ("Express", TipoTermoEnum.FRAMEWORK, "express"),
        ("Express.js", TipoTermoEnum.FRAMEWORK, "express"),
        ("Spring", TipoTermoEnum.FRAMEWORK, "spring"),
        ("Spring Boot", TipoTermoEnum.FRAMEWORK, "spring_boot"),
        ("SpringBoot", TipoTermoEnum.FRAMEWORK, "spring_boot"),
        ("Rails", TipoTermoEnum.FRAMEWORK, "rails"),
        ("Ruby on Rails", TipoTermoEnum.FRAMEWORK, "rails"),
        ("Laravel", TipoTermoEnum.FRAMEWORK, "laravel"),
        (".NET", TipoTermoEnum.FRAMEWORK, "dotnet"),
        ("dotnet", TipoTermoEnum.FRAMEWORK, "dotnet"),
        ("Node.js", TipoTermoEnum.FRAMEWORK, "nodejs"),
        ("NodeJS", TipoTermoEnum.FRAMEWORK, "nodejs"),
        
        # Tools
        ("Git", TipoTermoEnum.FERRAMENTA, "git"),
        ("GitHub", TipoTermoEnum.FERRAMENTA, "github"),
        ("GitLab", TipoTermoEnum.FERRAMENTA, "gitlab"),
        ("Bitbucket", TipoTermoEnum.FERRAMENTA, "bitbucket"),
        ("Docker", TipoTermoEnum.FERRAMENTA, "docker"),
        ("Kubernetes", TipoTermoEnum.FERRAMENTA, "kubernetes"),
        ("k8s", TipoTermoEnum.FERRAMENTA, "kubernetes"),
        ("Jenkins", TipoTermoEnum.FERRAMENTA, "jenkins"),
        ("Jira", TipoTermoEnum.FERRAMENTA, "jira"),
        ("Confluence", TipoTermoEnum.FERRAMENTA, "confluence"),
        ("Postman", TipoTermoEnum.FERRAMENTA, "postman"),
        ("VSCode", TipoTermoEnum.FERRAMENTA, "vscode"),
        ("Visual Studio Code", TipoTermoEnum.FERRAMENTA, "vscode"),
        ("IntelliJ", TipoTermoEnum.FERRAMENTA, "intellij"),
        ("Figma", TipoTermoEnum.FERRAMENTA, "figma"),
        ("Terraform", TipoTermoEnum.FERRAMENTA, "terraform"),
        ("Ansible", TipoTermoEnum.FERRAMENTA, "ansible"),
        
        # Platforms
        ("AWS", TipoTermoEnum.PLATAFORMA, "aws"),
        ("Amazon Web Services", TipoTermoEnum.PLATAFORMA, "aws"),
        ("Azure", TipoTermoEnum.PLATAFORMA, "azure"),
        ("Microsoft Azure", TipoTermoEnum.PLATAFORMA, "azure"),
        ("GCP", TipoTermoEnum.PLATAFORMA, "gcp"),
        ("Google Cloud", TipoTermoEnum.PLATAFORMA, "gcp"),
        ("Google Cloud Platform", TipoTermoEnum.PLATAFORMA, "gcp"),
        ("Heroku", TipoTermoEnum.PLATAFORMA, "heroku"),
        ("Vercel", TipoTermoEnum.PLATAFORMA, "vercel"),
        ("Netlify", TipoTermoEnum.PLATAFORMA, "netlify"),
        ("DigitalOcean", TipoTermoEnum.PLATAFORMA, "digitalocean"),
        
        # Databases
        ("PostgreSQL", TipoTermoEnum.BANCO_DADOS, "postgresql"),
        ("Postgres", TipoTermoEnum.BANCO_DADOS, "postgresql"),
        ("MySQL", TipoTermoEnum.BANCO_DADOS, "mysql"),
        ("MariaDB", TipoTermoEnum.BANCO_DADOS, "mariadb"),
        ("MongoDB", TipoTermoEnum.BANCO_DADOS, "mongodb"),
        ("Redis", TipoTermoEnum.BANCO_DADOS, "redis"),
        ("Elasticsearch", TipoTermoEnum.BANCO_DADOS, "elasticsearch"),
        ("Oracle", TipoTermoEnum.BANCO_DADOS, "oracle"),
        ("SQL Server", TipoTermoEnum.BANCO_DADOS, "sqlserver"),
        ("SQLite", TipoTermoEnum.BANCO_DADOS, "sqlite"),
        ("DynamoDB", TipoTermoEnum.BANCO_DADOS, "dynamodb"),
        ("Cassandra", TipoTermoEnum.BANCO_DADOS, "cassandra"),
        ("Neo4j", TipoTermoEnum.BANCO_DADOS, "neo4j"),
        
        # Techniques/Methodologies
        ("Scrum", TipoTermoEnum.TECNICA, "scrum"),
        ("Kanban", TipoTermoEnum.TECNICA, "kanban"),
        ("Agile", TipoTermoEnum.TECNICA, "agile"),
        ("Waterfall", TipoTermoEnum.TECNICA, "waterfall"),
        ("DevOps", TipoTermoEnum.TECNICA, "devops"),
        ("CI/CD", TipoTermoEnum.TECNICA, "cicd"),
        ("TDD", TipoTermoEnum.TECNICA, "tdd"),
        ("Test Driven Development", TipoTermoEnum.TECNICA, "tdd"),
        ("BDD", TipoTermoEnum.TECNICA, "bdd"),
        ("Microservices", TipoTermoEnum.TECNICA, "microservices"),
        ("Microsserviços", TipoTermoEnum.TECNICA, "microservices"),
        ("REST", TipoTermoEnum.TECNICA, "rest"),
        ("RESTful", TipoTermoEnum.TECNICA, "rest"),
        ("GraphQL", TipoTermoEnum.TECNICA, "graphql"),
        ("SOAP", TipoTermoEnum.TECNICA, "soap"),
        
        # Project Types
        ("Web", TipoTermoEnum.TIPO_PROJETO, "web"),
        ("Sistema Web", TipoTermoEnum.TIPO_PROJETO, "web"),
        ("Aplicação Web", TipoTermoEnum.TIPO_PROJETO, "web"),
        ("Mobile", TipoTermoEnum.TIPO_PROJETO, "mobile"),
        ("Mobile App", TipoTermoEnum.TIPO_PROJETO, "mobile"),
        ("Aplicativo Mobile", TipoTermoEnum.TIPO_PROJETO, "mobile"),
        ("Backend", TipoTermoEnum.TIPO_PROJETO, "backend"),
        ("Frontend", TipoTermoEnum.TIPO_PROJETO, "frontend"),
        ("Full Stack", TipoTermoEnum.TIPO_PROJETO, "fullstack"),
        ("Fullstack", TipoTermoEnum.TIPO_PROJETO, "fullstack"),
        ("API", TipoTermoEnum.TIPO_PROJETO, "api"),
        ("REST API", TipoTermoEnum.TIPO_PROJETO, "api"),
        ("Data Science", TipoTermoEnum.TIPO_PROJETO, "data_science"),
        ("Machine Learning", TipoTermoEnum.TIPO_PROJETO, "machine_learning"),
        ("ML", TipoTermoEnum.TIPO_PROJETO, "machine_learning"),
        ("AI", TipoTermoEnum.TIPO_PROJETO, "ai"),
        ("Inteligência Artificial", TipoTermoEnum.TIPO_PROJETO, "ai"),
        ("IoT", TipoTermoEnum.TIPO_PROJETO, "iot"),
        ("Internet of Things", TipoTermoEnum.TIPO_PROJETO, "iot"),
        ("Internet das Coisas", TipoTermoEnum.TIPO_PROJETO, "iot"),
        ("DevOps", TipoTermoEnum.TIPO_PROJETO, "devops"),
        ("Infrastructure", TipoTermoEnum.TIPO_PROJETO, "infrastructure"),
        ("Infraestrutura", TipoTermoEnum.TIPO_PROJETO, "infrastructure"),
        ("Embedded", TipoTermoEnum.TIPO_PROJETO, "embedded"),
        ("Embarcado", TipoTermoEnum.TIPO_PROJETO, "embedded"),
        ("Cloud", TipoTermoEnum.TIPO_PROJETO, "cloud"),
        ("Desktop", TipoTermoEnum.TIPO_PROJETO, "desktop"),
    ]
    
    # Insert terms
    count = 0
    for termo, tipo, normalizado in terms_data:
        # Check if term already exists
        existing = session.query(TermoTecnico).filter_by(
            termo=termo, tipo=tipo
        ).first()
        
        if not existing:
            new_term = TermoTecnico(
                termo=termo,
                tipo=tipo,
                termo_normalizado=normalizado
            )
            session.add(new_term)
            count += 1
    
    session.commit()
    session.close()
    
    print(f"Added {count} technical terms to the database.")


def main():
    """Main function"""
    print("=" * 50)
    print("Database Initialization Script")
    print("=" * 50)
    
    # Step 1: Create database if needed
    create_database_if_not_exists()
    
    # Step 2: Initialize schema
    engine = init_database()
    
    # Step 3: Populate technical terms
    populate_technical_terms(engine)
    
    print("=" * 50)
    print("Database initialization completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()
