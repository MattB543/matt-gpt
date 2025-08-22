#!/usr/bin/env python3

import json
import logging
import random
from typing import List, Dict
from datetime import datetime, timezone
from database import get_session
from models import Message
from llm_client import OpenRouterClient
from sqlmodel import select
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_50_random_messages():
    """Test the improved processing on 50 random text messages"""
    
    raw_file = "raw_data/texts/messages.ndjson"
    
    # First, collect all valid messages from the raw file
    logger.info(f"Reading all messages from {raw_file} to select random sample...")
    all_messages = []
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            if line_num % 10000 == 0:
                logger.info(f"Read {line_num} lines, found {len(all_messages)} valid messages")
                
            try:
                data = json.loads(line.strip())
                body = data.get("body", "").strip()
                if not body:
                    continue
                    
                # Check if it has basic required fields
                if data.get("date") and data.get("thread_id"):
                    all_messages.append(data)
                    
            except json.JSONDecodeError:
                continue
    
    logger.info(f"Found {len(all_messages)} total valid messages")
    
    # Select 50 random messages
    if len(all_messages) < 50:
        logger.warning(f"Only found {len(all_messages)} messages, using all of them")
        sample_messages = all_messages
    else:
        sample_messages = random.sample(all_messages, 50)
        
    logger.info(f"Selected {len(sample_messages)} messages for testing")
    
    # Process the sample messages
    client = OpenRouterClient()
    processed_count = 0
    with_embeddings = 0
    without_embeddings = 0
    
    try:
        with get_session() as session:
            for i, raw_data in enumerate(sample_messages, 1):
                try:
                    # Extract message data (same logic as main processor)
                    body = raw_data.get("body", "").strip()
                    date_ms = raw_data.get("date")
                    timestamp = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
                    
                    # Extract metadata
                    phone_number = raw_data.get("address", "")
                    message_id = raw_data.get("_id", "")
                    message_type = raw_data.get("type", "")
                    is_sent = message_type == "2"
                    
                    meta = {
                        "message_id": message_id,
                        "phone_number": phone_number,
                        "message_type": message_type,
                        "is_sent": is_sent,
                        "read_status": raw_data.get("read", ""),
                        "protocol": raw_data.get("protocol", ""),
                        "service_center": raw_data.get("service_center", ""),
                        "date_sent": raw_data.get("date_sent", "")
                    }
                    
                    # Check message length for embedding decision
                    if len(body.strip()) <= 5:
                        logger.info(f"Message {i}/50: SHORT '{body}' (no embedding)")
                        embedding = None
                        without_embeddings += 1
                    else:
                        logger.info(f"Message {i}/50: '{body[:50]}...' (generating embedding)")
                        embedding = client.generate_embedding(body)
                        with_embeddings += 1
                    
                    # Create and save message
                    db_message = Message(
                        source="text",
                        thread_id=raw_data.get("thread_id", ""),
                        message_text=body,
                        timestamp=timestamp,
                        embedding=embedding,
                        meta_data=meta
                    )
                    
                    session.add(db_message)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process message {i}: {e}")
                    continue
            
            # Commit all messages
            session.commit()
            logger.info(f"✅ Successfully processed {processed_count}/50 messages")
            logger.info(f"  - With embeddings: {with_embeddings}")
            logger.info(f"  - Without embeddings: {without_embeddings}")
            
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        raise

def verify_database_data():
    """Check the database to verify the processed messages look correct"""
    logger.info("\n" + "="*60)
    logger.info("VERIFYING DATABASE DATA")
    logger.info("="*60)
    
    try:
        with get_session() as session:
            # Get all text messages
            messages = session.exec(
                select(Message).where(Message.source == 'text').order_by(Message.timestamp)
            ).all()
            
            logger.info(f"Found {len(messages)} text messages in database")
            
            # Analyze the data
            with_embeddings = 0
            without_embeddings = 0
            with_metadata = 0
            without_metadata = 0
            short_messages = []
            long_messages = []
            
            for msg in messages:
                # Check embeddings
                if msg.embedding is not None:
                    with_embeddings += 1
                else:
                    without_embeddings += 1
                    
                # Check metadata
                if msg.meta_data and msg.meta_data != {}:
                    with_metadata += 1
                else:
                    without_metadata += 1
                
                # Categorize by length
                if len(msg.message_text.strip()) <= 5:
                    short_messages.append(msg)
                else:
                    long_messages.append(msg)
            
            logger.info(f"\nEMBEDDING ANALYSIS:")
            logger.info(f"  With embeddings: {with_embeddings}")
            logger.info(f"  Without embeddings: {without_embeddings}")
            
            logger.info(f"\nMETADATA ANALYSIS:")
            logger.info(f"  With metadata: {with_metadata}")
            logger.info(f"  Without metadata: {without_metadata}")
            
            logger.info(f"\nMESSAGE LENGTH ANALYSIS:")
            logger.info(f"  Short messages (≤5 chars): {len(short_messages)}")
            logger.info(f"  Long messages (>5 chars): {len(long_messages)}")
            
            # Show sample short messages (should have no embeddings)
            logger.info(f"\nSAMPLE SHORT MESSAGES (should have no embeddings):")
            for i, msg in enumerate(short_messages[:5]):
                has_embedding = "YES" if msg.embedding else "NO"
                phone = msg.meta_data.get('phone_number', 'N/A') if msg.meta_data else 'N/A'
                logger.info(f"  {i+1}. '{msg.message_text}' | Embedding: {has_embedding} | Phone: {phone}")
            
            # Show sample long messages (should have embeddings)
            logger.info(f"\nSAMPLE LONG MESSAGES (should have embeddings):")
            for i, msg in enumerate(long_messages[:5]):
                has_embedding = "YES" if msg.embedding else "NO"
                phone = msg.meta_data.get('phone_number', 'N/A') if msg.meta_data else 'N/A'
                direction = "sent by Matt" if msg.meta_data and msg.meta_data.get('is_sent') else "received by Matt"
                logger.info(f"  {i+1}. '{msg.message_text[:50]}...' | Embedding: {has_embedding} | Phone: {phone} | {direction}")
            
            # Verify the logic is working correctly
            embedding_logic_errors = 0
            for msg in messages:
                is_short = len(msg.message_text.strip()) <= 5
                has_embedding = msg.embedding is not None
                
                if is_short and has_embedding:
                    embedding_logic_errors += 1
                    logger.error(f"ERROR: Short message has embedding: '{msg.message_text}'")
                elif not is_short and not has_embedding:
                    embedding_logic_errors += 1
                    logger.error(f"ERROR: Long message missing embedding: '{msg.message_text[:50]}...'")
            
            if embedding_logic_errors == 0:
                logger.info(f"\n✅ EMBEDDING LOGIC PERFECT: All short messages lack embeddings, all long messages have embeddings")
            else:
                logger.error(f"\n❌ EMBEDDING LOGIC ERRORS: {embedding_logic_errors} messages with incorrect embedding logic")
            
            return len(messages), embedding_logic_errors == 0
            
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return 0, False

if __name__ == "__main__":
    logger.info("Starting 50-message test...")
    
    # Check if database is empty first
    try:
        with get_session() as session:
            existing_count = session.exec(select(Message).where(Message.source == 'text')).first()
            if existing_count:
                logger.warning("Database already has text messages. This test will add to existing data.")
                response = input("Continue? (y/N): ").strip().lower()
                if response != 'y':
                    logger.info("Test cancelled")
                    exit()
    except:
        pass
    
    # Run the test
    test_50_random_messages()
    
    # Verify results
    count, is_perfect = verify_database_data()
    
    if is_perfect and count > 0:
        logger.info(f"\n🎉 TEST PASSED! {count} messages processed with perfect logic!")
    else:
        logger.error(f"\n💥 TEST ISSUES FOUND! Check the errors above.")