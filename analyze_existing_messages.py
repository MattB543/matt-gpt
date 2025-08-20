#!/usr/bin/env python3

from database import get_session
from models import Message
from sqlmodel import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_existing_messages():
    """Analyze what text messages are currently in the database"""
    logger.info("Analyzing existing text messages...")
    
    with get_session() as session:
        text_messages = session.exec(select(Message).where(Message.source == 'text')).all()
        
        logger.info(f"Found {len(text_messages)} text messages")
        
        # Check meta structure
        meta_types = {}
        thread_ids = set()
        phone_numbers = set()
        
        for msg in text_messages[:100]:  # Sample first 100
            if msg.meta_data:
                for key in msg.meta_data.keys():
                    meta_types[key] = meta_types.get(key, 0) + 1
            
            thread_ids.add(msg.thread_id)
            
            # Check if meta has phone number
            if msg.meta_data and 'phone_number' in msg.meta_data:
                phone_numbers.add(msg.meta_data['phone_number'])
        
        logger.info("=== METADATA ANALYSIS ===")
        logger.info(f"Metadata field frequency:")
        for field, count in meta_types.items():
            logger.info(f"  {field}: {count} messages")
        
        logger.info(f"\nUnique thread IDs (first 10): {list(thread_ids)[:10]}")
        logger.info(f"Total unique thread IDs: {len(thread_ids)}")
        
        logger.info(f"\nUnique phone numbers (first 5): {list(phone_numbers)[:5]}")
        logger.info(f"Total unique phone numbers: {len(phone_numbers)}")
        
        # Check if these look like real phone numbers vs test data
        real_phone_pattern = any(phone.startswith('+1') for phone in phone_numbers)
        logger.info(f"Contains real phone numbers: {real_phone_pattern}")
        
        # Sample a few messages to see their content
        logger.info("\n=== SAMPLE MESSAGES ===")
        for i, msg in enumerate(text_messages[:3]):
            logger.info(f"Message {i+1}:")
            logger.info(f"  Text: {msg.message_text[:100]}...")
            logger.info(f"  Thread: {msg.thread_id}")
            logger.info(f"  Timestamp: {msg.timestamp}")
            logger.info(f"  Metadata: {msg.meta_data}")
        
        return {
            "total_count": len(text_messages),
            "has_real_meta": len(meta_types) > 1,
            "has_phone_numbers": len(phone_numbers) > 0,
            "looks_like_real_data": real_phone_pattern and len(meta_types) > 1
        }

if __name__ == "__main__":
    result = analyze_existing_messages()
    print(f"\nSUMMARY: {'Real data detected' if result['looks_like_real_data'] else 'Appears to be test/sample data'}")