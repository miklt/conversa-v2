#!/usr/bin/env python3
"""
Simple migration script to initialize the database schema using SQLAlchemy models.
"""
from backend.app.db.database import init_db

if __name__ == "__main__":
    init_db()

