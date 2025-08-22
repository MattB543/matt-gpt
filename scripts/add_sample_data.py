#!/usr/bin/env python3
"""Add sample data to test the RAG system."""

from database import get_session
from models import Message, PersonalityDoc
from llm_client import OpenRouterClient
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_sample_data():
    """Add sample messages and personality docs for testing"""
    logger.info("Adding sample data for RAG testing...")
    
    client = OpenRouterClient()
    
    # Sample messages that represent different aspects of Matt's communication
    sample_messages = [
        {
            "text": "I really think we should focus on iterative development rather than waterfall. It gives us more flexibility to adapt.",
            "thread_id": "work_philosophy",
            "source": "slack"
        },
        {
            "text": "Just finished reading about the new AI developments. The pace of change is incredible but we need to stay focused on practical applications.",
            "thread_id": "ai_discussion", 
            "source": "slack"
        },
        {
            "text": "Hey, can we schedule that meeting for next week? I'm pretty booked this week with the product launch.",
            "thread_id": "scheduling",
            "source": "text"
        },
        {
            "text": "I prefer direct communication over beating around the bush. Let's just say what we mean and solve the problem.",
            "thread_id": "communication_style",
            "source": "slack"
        },
        {
            "text": "The user experience should be our top priority. All the fancy tech in the world doesn't matter if users can't figure out how to use it.",
            "thread_id": "product_philosophy",
            "source": "slack"
        }
    ]
    
    # Sample personality document
    personality_content = """
    Matt's Work Philosophy:
    - Prefers iterative development over waterfall methodology
    - Values direct, honest communication
    - Prioritizes user experience and practical solutions
    - Believes in moving fast but being thoughtful about decisions
    - Enjoys discussing AI and technology trends but focuses on practical applications
    - Prefers small, focused teams over large bureaucratic structures
    """
    
    try:
        with get_session() as session:
            logger.info("Adding sample messages...")
            
            # Add sample messages with embeddings
            for i, msg_data in enumerate(sample_messages):
                logger.debug(f"Processing message {i+1}/{len(sample_messages)}: {msg_data['text'][:50]}...")
                
                # Generate embedding
                embedding = client.generate_embedding(msg_data["text"])
                
                message = Message(
                    source=msg_data["source"],
                    thread_id=msg_data["thread_id"],
                    message_text=msg_data["text"],
                    timestamp=datetime.utcnow() - timedelta(days=i),  # Spread across days
                    embedding=embedding,
                    meta_data={"sample": True}
                )
                
                session.add(message)
                logger.debug(f"Message {i+1} added to session")
            
            logger.info("Adding sample personality document...")
            
            # Add personality document
            personality_embedding = client.generate_embedding(personality_content)
            
            personality_doc = PersonalityDoc(
                doc_type="work_philosophy",
                title="Matt's Work Philosophy",
                content=personality_content,
                summary="Core beliefs about work, development, and communication",
                embedding=personality_embedding,
                meta_data={"sample": True}
            )
            
            session.add(personality_doc)
            logger.debug("Personality document added to session")
            
            # Commit all changes
            session.commit()
            logger.info("Sample data committed to database")
            
            # Verify data was added
            from sqlmodel import select
            from sqlalchemy import func
            
            # Use simple count queries instead of JSON contains
            message_count = session.exec(select(func.count(Message.id)).where(Message.source.in_(["slack", "text"]))).first()
            doc_count = session.exec(select(func.count(PersonalityDoc.id)).where(PersonalityDoc.doc_type == "work_philosophy")).first()
            
            logger.info(f"Verification: {message_count} total messages and {doc_count} personality docs in database")
            
    except Exception as e:
        logger.error(f"Failed to add sample data: {e}")
        raise
        
    logger.info("Sample data addition complete!")


if __name__ == "__main__":
    add_sample_data()