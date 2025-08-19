#!/usr/bin/env python3
"""Drop and recreate all database tables."""

from sqlmodel import SQLModel
from sqlalchemy import text
from database import engine
from models import Message, PersonalityDoc, QueryLog  # Import models to register them

def recreate_database():
    """Drop all tables and recreate them"""
    print("Dropping existing tables...")
    
    with engine.connect() as conn:
        # Drop all tables
        conn.execute(text("DROP TABLE IF EXISTS query_logs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS personality_docs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
        conn.commit()
        print("+ Dropped existing tables")
        
        # Ensure pgvector extension exists
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("+ Created pgvector extension")
    
    # Recreate all tables
    SQLModel.metadata.create_all(engine)
    print("+ Created new tables with updated schema")
    
    print("\n+ Database recreation completed!")

if __name__ == "__main__":
    recreate_database()