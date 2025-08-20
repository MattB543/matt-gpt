#!/usr/bin/env python3

from database import get_session
from models import Message
from sqlmodel import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_text_messages():
    """Check current state of text messages in database"""
    logger.info("Checking text messages in database...")
    
    with get_session() as session:
        # Get all text messages
        text_messages = session.exec(select(Message).where(Message.source == 'text')).all()
        
        # Get all messages for comparison
        all_messages = session.exec(select(Message)).all()
        
        logger.info(f"Total messages in database: {len(all_messages)}")
        logger.info(f"Text messages in database: {len(text_messages)}")
        logger.info(f"Non-text messages: {len(all_messages) - len(text_messages)}")
        
        if text_messages:
            logger.info("Sample text message meta:")
            sample = text_messages[0]
            logger.info(f"  Message text: {sample.message_text[:50]}...")
            logger.info(f"  Timestamp: {sample.timestamp}")
            logger.info(f"  Thread ID: {sample.thread_id}")
            logger.info(f"  Metadata keys: {list(sample.meta_data.keys()) if sample.meta_data else 'None'}")
        
        return len(text_messages)

if __name__ == "__main__":
    count = check_text_messages()