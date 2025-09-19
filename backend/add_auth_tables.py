"""
Migration script to add User and MagicToken tables for authentication
"""
import sys
import os

# Add the parent directory to sys.path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from backend.app.db.database import engine

def run_migration():
    """Run the migration to add authentication tables"""
    
    migration_sql = """
    -- Create users table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        full_name VARCHAR(255),
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        CONSTRAINT check_usp_email CHECK (email LIKE '%@usp.br')
    );

    -- Create magic_tokens table
    CREATE TABLE IF NOT EXISTS magic_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(255) UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address VARCHAR(45),
        user_agent TEXT,
        CONSTRAINT check_expires_after_creation CHECK (expires_at > created_at)
    );

    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_magic_tokens_user_id ON magic_tokens(user_id);
    CREATE INDEX IF NOT EXISTS idx_magic_tokens_token ON magic_tokens(token);
    CREATE INDEX IF NOT EXISTS idx_magic_tokens_expires_at ON magic_tokens(expires_at);
    CREATE INDEX IF NOT EXISTS idx_magic_tokens_used_at ON magic_tokens(used_at);
    
    -- Update trigger for users.updated_at
    CREATE OR REPLACE FUNCTION update_modified_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_users_modtime ON users;
    CREATE TRIGGER update_users_modtime 
        BEFORE UPDATE ON users 
        FOR EACH ROW 
        EXECUTE FUNCTION update_modified_column();
    """
    
    with engine.connect() as conn:
        # Execute each statement separately to avoid transaction issues
        statements = migration_sql.strip().split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                    print(f"✅ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"❌ Error executing statement: {e}")
                    print(f"Statement: {statement}")
    
    print("🎉 Authentication migration completed!")

if __name__ == "__main__":
    run_migration()