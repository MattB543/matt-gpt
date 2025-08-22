#!/usr/bin/env python3

from database import get_session
from models import Message, PersonalityDoc
from sqlmodel import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_data():
    """Check what data exists in the database"""
    logger.info("Checking database data...")
    
    try:
        with get_session() as session:
            # Count messages
            messages = session.exec(select(Message)).all()
            message_count = len(messages)
            
            # Count personality docs
            personality_docs = session.exec(select(PersonalityDoc)).all()
            doc_count = len(personality_docs)
            
            logger.info(f"Messages in database: {message_count}")
            logger.info(f"Personality documents in database: {doc_count}")
            
            # Check for messages with embeddings
            messages_with_embeddings = len([m for m in messages if m.embedding is not None])
            docs_with_embeddings = len([d for d in personality_docs if d.embedding is not None])
            
            logger.info(f"Messages with embeddings: {messages_with_embeddings}")
            logger.info(f"Personality docs with embeddings: {docs_with_embeddings}")
            
            if message_count == 0 and doc_count == 0:
                logger.warning("⚠️  DATABASE IS EMPTY - No messages or personality docs found!")
                logger.warning("This explains why the API might be timing out - no context to retrieve!")
                return False
            
            if messages_with_embeddings == 0 and docs_with_embeddings == 0:
                logger.warning("⚠️  NO EMBEDDINGS FOUND - Data exists but no embeddings generated!")
                logger.warning("The retriever will fail to find relevant context!")
                return False
                
            logger.info("✅ Database contains data with embeddings")
            return True
            
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

if __name__ == "__main__":
    check_database_data()