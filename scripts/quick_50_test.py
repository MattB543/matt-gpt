#!/usr/bin/env python3

import json
import uuid
import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

def process_first_50_valid():
    """Process first 50 valid messages (faster than random sampling)"""
    
    print("Processing first 50 valid messages from raw data...")
    
    raw_file = "raw_data/texts/messages.ndjson"
    processed_count = 0
    target_count = 50
    
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            with open(raw_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if processed_count >= target_count:
                        break
                        
                    if line_num % 1000 == 0:
                        print(f"  Read {line_num:,} lines, processed {processed_count} messages")
                    
                    try:
                        data = json.loads(line.strip())
                        body = data.get("body", "").strip()
                        if not body or not data.get("date") or not data.get("thread_id"):
                            continue
                        
                        # Extract data
                        date_ms = data.get("date")
                        timestamp = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
                        thread_id = data.get("thread_id", "")
                        
                        # Extract metadata  
                        phone_number = data.get("address", "")
                        message_id = data.get("_id", "")
                        message_type = data.get("type", "")
                        is_sent = message_type == "2"
                        
                        meta_data = {
                            "message_id": message_id,
                            "phone_number": phone_number,
                            "message_type": message_type,
                            "is_sent": is_sent,
                            "read_status": data.get("read", ""),
                            "protocol": data.get("protocol", ""),
                            "service_center": data.get("service_center", ""),
                            "date_sent": data.get("date_sent", "")
                        }
                        
                        # Apply embedding logic (without actually calling API for speed)
                        message_length = len(body.strip())
                        if message_length <= 5:
                            print(f"  {processed_count+1:2}/50: SHORT '{body}' ({message_length} chars) -> NO embedding")
                            embedding = None
                        else:
                            print(f"  {processed_count+1:2}/50: LONG  '{body[:40]}...' ({message_length} chars) -> [would get embedding]")
                            # For testing, we'll set a fake embedding array
                            embedding = [0.1] * 1536  # Fake embedding for testing
                        
                        # Insert into database
                        msg_uuid = str(uuid.uuid4())
                        cur.execute("""
                            INSERT INTO messages (id, source, thread_id, message_text, timestamp, embedding, meta_data, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            msg_uuid,
                            "text",
                            thread_id,
                            body,
                            timestamp,
                            embedding,
                            json.dumps(meta_data),
                            datetime.now(timezone.utc)
                        ))
                        
                        processed_count += 1
                        
                    except Exception as e:
                        print(f"  Error on line {line_num}: {e}")
                        continue
            
            # Commit all
            conn.commit()
            print(f"\nCommitted {processed_count} messages to database")

def verify_quick():
    """Quick verification of the database"""
    
    print("\nVerifying database contents...")
    
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Get counts
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text'")
            total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text' AND embedding IS NOT NULL")
            with_embeddings = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text' AND embedding IS NULL")
            without_embeddings = cur.fetchone()[0]
            
            print(f"Total text messages: {total}")
            print(f"With embeddings: {with_embeddings}")
            print(f"Without embeddings: {without_embeddings}")
            
            # Check logic correctness
            cur.execute("""
                SELECT message_text, embedding IS NOT NULL as has_embedding
                FROM messages 
                WHERE source = 'text'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            logic_errors = 0
            print(f"\nLogic verification (recent 20 messages):")
            
            for text, has_embedding in cur.fetchall():
                text_length = len(text.strip())
                should_have_embedding = text_length > 5
                is_correct = (should_have_embedding == has_embedding)
                
                if not is_correct:
                    logic_errors += 1
                
                status = "✓" if is_correct else "✗"
                print(f"  {status} '{text[:30]}...' ({text_length} chars) -> Embedding: {has_embedding}")
            
            # Check metadata
            cur.execute("""
                SELECT message_text, meta_data
                FROM messages 
                WHERE source = 'text' AND meta_data IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            print(f"\nMetadata samples:")
            metadata_count = 0
            for text, meta in cur.fetchall():
                if meta and isinstance(meta, dict) and meta != {}:
                    metadata_count += 1
                    phone = meta.get('phone_number', 'N/A')
                    direction = "sent by Matt" if meta.get('is_sent') else "received by Matt"
                    print(f"  '{text[:25]}...' | Phone: {phone} | {direction}")
            
            print(f"\n=== RESULTS ===")
            print(f"Logic errors: {logic_errors}")
            print(f"Messages with good metadata: {metadata_count}/5 samples")
            
            if logic_errors == 0 and metadata_count >= 4:
                print("✅ TEST PASSED!")
                return True
            else:
                print("❌ Issues found")
                return False

if __name__ == "__main__":
    print("=" * 50)
    print("QUICK 50 MESSAGE TEST")
    print("=" * 50)
    
    try:
        process_first_50_valid()
        success = verify_quick()
        
        if success:
            print("\n🎉 Processing logic is working perfectly!")
        else:
            print("\n❌ Found issues that need fixing")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()