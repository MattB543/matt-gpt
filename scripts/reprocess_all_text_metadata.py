#!/usr/bin/env python3

import json
import logging
from datetime import datetime, timezone
import psycopg
import os
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reprocess_all_text_metadata():
    """Update metadata for ALL text messages by re-reading raw data"""
    
    raw_file = "raw_data/texts/messages.ndjson"
    
    logger.info(f"Reading ALL raw text data from {raw_file}...")
    
    # Build lookup of raw messages by unique key
    raw_messages = {}
    processed_count = 0
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Reading raw messages"):
            try:
                data = json.loads(line.strip())
                body = data.get("body", "").strip()
                if not body:
                    continue
                    
                # Create unique key based on content and timestamp
                date_ms = data.get("date")
                if not date_ms:
                    continue
                    
                timestamp = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
                thread_id = data.get("thread_id", "")
                
                # Use combination of text + timestamp as key
                key = f"{body}|{timestamp}|{thread_id}"
                raw_messages[key] = data
                processed_count += 1
                
            except (json.JSONDecodeError, ValueError):
                continue
    
    logger.info(f"Loaded {len(raw_messages)} unique raw messages")
    
    # Connect to database and update existing text messages
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Get all text messages that need metadata updates
            cur.execute("""
                SELECT id, message_text, timestamp, thread_id, meta_data
                FROM messages 
                WHERE source = 'text'
                ORDER BY timestamp
            """)
            
            db_messages = cur.fetchall()
            logger.info(f"Found {len(db_messages)} text messages in database")
            
            updated_count = 0
            
            for msg_id, text, timestamp, thread_id, current_meta in tqdm(db_messages, desc="Updating metadata"):
                # Create lookup key
                key = f"{text}|{timestamp}|{thread_id}"
                
                raw_data = raw_messages.get(key)
                if not raw_data:
                    # Try alternate key without thread_id in case there are mismatches
                    alt_key = f"{text}|{timestamp}|"
                    for k, v in raw_messages.items():
                        if k.startswith(f"{text}|{timestamp}|"):
                            raw_data = v
                            break
                
                if raw_data:
                    # Extract comprehensive metadata
                    phone_number = raw_data.get("address", "")
                    message_id = raw_data.get("_id", "")
                    message_type = raw_data.get("type", "")
                    display_name = raw_data.get("__display_name", "")
                    is_sent = message_type == "2"
                    
                    new_meta = {
                        "message_id": message_id,
                        "phone_number": phone_number,
                        "display_name": display_name,
                        "message_type": message_type,
                        "is_sent": is_sent,
                        "read_status": raw_data.get("read", ""),
                        "protocol": raw_data.get("protocol", ""),
                        "service_center": raw_data.get("service_center", ""),
                        "date_sent": raw_data.get("date_sent", ""),
                        "raw_address": phone_number,
                        "status": raw_data.get("status", ""),
                        "locked": raw_data.get("locked", ""),
                        "creator": raw_data.get("creator", "")
                    }
                    
                    # Update if metadata is empty or different
                    if not current_meta or current_meta == {}:
                        cur.execute("""
                            UPDATE messages 
                            SET meta_data = %s 
                            WHERE id = %s
                        """, (json.dumps(new_meta), msg_id))
                        
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            logger.info(f"Updated {updated_count} messages so far...")
                else:
                    logger.warning(f"No raw data found for: {text[:30]}...")
            
            conn.commit()
            logger.info(f"✅ Updated metadata for {updated_count} messages")

def verify_metadata_coverage():
    """Check how many messages now have proper metadata"""
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Count messages with and without metadata
            cur.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN meta_data = '{}' OR meta_data IS NULL THEN 1 ELSE 0 END) as empty_metadata,
                    SUM(CASE WHEN meta_data != '{}' AND meta_data IS NOT NULL THEN 1 ELSE 0 END) as with_metadata
                FROM messages 
                WHERE source = 'text'
            """)
            
            total, empty, with_meta = cur.fetchone()
            
            print(f"\n📊 Text Message Metadata Coverage:")
            print(f"Total text messages: {total:,}")
            print(f"With metadata: {with_meta:,} ({(with_meta/total)*100:.1f}%)")
            print(f"Empty metadata: {empty:,} ({(empty/total)*100:.1f}%)")
            
            # Show sample of messages with metadata
            cur.execute("""
                SELECT message_text, meta_data->'phone_number' as phone, meta_data->'is_sent' as is_sent
                FROM messages 
                WHERE source = 'text' AND meta_data != '{}' 
                LIMIT 5
            """)
            
            print(f"\n📱 Sample messages with metadata:")
            for i, (text, phone, is_sent) in enumerate(cur.fetchall(), 1):
                direction = "sent by Matt" if is_sent else "received by Matt"
                print(f"{i}. [{phone}] {direction}: {text[:60]}...")

if __name__ == "__main__":
    logger.info("Starting complete text metadata reprocessing...")
    reprocess_all_text_metadata()
    verify_metadata_coverage()
    logger.info("✅ Complete metadata reprocessing finished!")