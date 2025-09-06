#!/usr/bin/env python3
"""
Simple migration script to initialize the database schema using SQLAlchemy models.
"""
import sys
import os

# Add the parent directory to sys.path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from backend.app.db.database import init_db

if __name__ == "__main__":
    init_db()

