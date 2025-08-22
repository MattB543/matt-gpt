#!/usr/bin/env python3
"""
Migration script to add conversation_id column to query_logs table
Run this once to update existing database schema
"""

import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def run_migration():
    """Add conversation_id column and indexes to query_logs table"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    logger.info("Starting migration: Add conversation_id to query_logs")
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            logger.info("Checking if conversation_id column already exists...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'query_logs' 
                AND column_name = 'conversation_id'
            """))
            
            if result.fetchone():
                logger.info("conversation_id column already exists, skipping migration")
                return
            
            # Add the conversation_id column
            logger.info("Adding conversation_id column to query_logs table...")
            conn.execute(text("""
                ALTER TABLE query_logs 
                ADD COLUMN conversation_id UUID
            """))
            
            # Update existing rows with random UUIDs (each gets its own conversation)
            logger.info("Setting conversation_id for existing rows...")
            conn.execute(text("""
                UPDATE query_logs 
                SET conversation_id = gen_random_uuid() 
                WHERE conversation_id IS NULL
            """))
            
            # Make the column NOT NULL now that all rows have values
            logger.info("Setting conversation_id column to NOT NULL...")
            conn.execute(text("""
                ALTER TABLE query_logs 
                ALTER COLUMN conversation_id SET NOT NULL
            """))
            
            # Create indexes for performance
            logger.info("Creating indexes for conversation_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_query_logs_conversation_id 
                ON query_logs(conversation_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_query_logs_conversation_created 
                ON query_logs(conversation_id, created_at)
            """))
            
            # Commit all changes
            conn.commit()
            logger.info("Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()