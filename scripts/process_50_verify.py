#!/usr/bin/env python3

import json
import random
import uuid
import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

class SimpleOpenAIClient:
    """Simple OpenAI client for embeddings without external dependencies"""
    def __init__(self):
        import urllib.request
        import urllib.parse
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/embeddings"
    
    def generate_embedding(self, text):
        """Generate embedding using OpenAI API"""
        import urllib.request
        import urllib.parse
        
        data = {
            "model": "text-embedding-3-small",
            "input": text,
            "dimensions": 1536
        }
        
        json_data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(
            self.base_url,
            data=json_data,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                return result['data'][0]['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

def process_50_messages():
    """Process exactly 50 random messages and insert into database"""
    
    print("Step 1: Collecting random messages from raw data...")
    
    raw_file = "raw_data/texts/messages.ndjson"
    all_messages = []
    
    # Collect all valid messages
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            if line_num % 5000 == 0:
                print(f"  Read {line_num:,} lines, found {len(all_messages)} valid messages")
                
            try:
                data = json.loads(line.strip())
                body = data.get("body", "").strip()
                if body and data.get("date") and data.get("thread_id"):
                    all_messages.append(data)
            except:
                continue
    
    print(f"Found {len(all_messages):,} total valid messages")
    
    # Select exactly 50 random messages
    selected_messages = random.sample(all_messages, 50)
    print(f"Selected 50 random messages for processing")
    
    print("\nStep 2: Processing messages with embedding logic...")
    
    client = SimpleOpenAIClient()
    conn_str = os.getenv('DATABASE_URL')
    
    processed_messages = []
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            for i, raw_data in enumerate(selected_messages, 1):
                try:
                    # Extract basic data
                    body = raw_data.get("body", "").strip()
                    date_ms = raw_data.get("date")
                    timestamp = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
                    thread_id = raw_data.get("thread_id", "")
                    
                    # Extract metadata  
                    phone_number = raw_data.get("address", "")
                    message_id = raw_data.get("_id", "")
                    message_type = raw_data.get("type", "")
                    is_sent = message_type == "2"
                    
                    meta_data = {
                        "message_id": message_id,
                        "phone_number": phone_number,
                        "message_type": message_type,
                        "is_sent": is_sent,
                        "read_status": raw_data.get("read", ""),
                        "protocol": raw_data.get("protocol", ""),
                        "service_center": raw_data.get("service_center", ""),
                        "date_sent": raw_data.get("date_sent", "")
                    }
                    
                    # Apply embedding logic
                    message_length = len(body.strip())
                    if message_length <= 5:
                        print(f"  {i:2}/50: SHORT '{body}' ({message_length} chars) -> NO embedding")
                        embedding = None
                    else:
                        print(f"  {i:2}/50: LONG  '{body[:40]}...' ({message_length} chars) -> generating embedding...")
                        embedding = client.generate_embedding(body)
                        if embedding:
                            print(f"         -> embedding generated ({len(embedding)} dimensions)")
                        else:
                            print(f"         -> embedding FAILED!")
                    
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
                    
                    processed_messages.append({
                        'id': msg_uuid,
                        'text': body,
                        'length': message_length,
                        'has_embedding': embedding is not None,
                        'phone': phone_number,
                        'is_sent': is_sent
                    })
                    
                except Exception as e:
                    print(f"  {i:2}/50: ERROR processing message: {e}")
                    continue
            
            # Commit all inserts
            conn.commit()
            print(f"\nStep 3: Committed {len(processed_messages)} messages to database")
    
    return processed_messages

def verify_database():
    """Verify the processed messages in the database"""
    
    print("\nStep 4: Verifying database contents...")
    
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Get all text messages
            cur.execute("""
                SELECT id, message_text, embedding, meta_data, timestamp, thread_id
                FROM messages 
                WHERE source = 'text'
                ORDER BY created_at DESC
            """)
            
            db_messages = cur.fetchall()
            print(f"Found {len(db_messages)} text messages in database")
            
            # Analyze the data
            with_embeddings = 0
            without_embeddings = 0
            short_messages = []
            long_messages = []
            metadata_issues = 0
            
            for msg_id, text, embedding, meta_data, timestamp, thread_id in db_messages:
                text_length = len(text.strip())
                has_embedding = embedding is not None
                
                if has_embedding:
                    with_embeddings += 1
                else:
                    without_embeddings += 1
                
                # Check if logic is correct
                should_have_embedding = text_length > 5
                logic_correct = (should_have_embedding == has_embedding)
                
                if text_length <= 5:
                    short_messages.append((text, has_embedding, logic_correct))
                else:
                    long_messages.append((text[:40], has_embedding, logic_correct))
                
                # Check metadata
                if not meta_data or meta_data == {}:
                    metadata_issues += 1
            
            print(f"\n=== DATABASE VERIFICATION RESULTS ===")
            print(f"Total messages: {len(db_messages)}")
            print(f"With embeddings: {with_embeddings}")
            print(f"Without embeddings: {without_embeddings}")
            print(f"Metadata issues: {metadata_issues}")
            
            print(f"\nShort messages (≤5 chars, should have NO embedding):")
            logic_errors = 0
            for i, (text, has_emb, correct) in enumerate(short_messages[:10]):
                status = "✓" if correct else "✗"
                if not correct:
                    logic_errors += 1
                print(f"  {status} '{text}' -> Embedding: {has_emb}")
            
            print(f"\nLong messages (>5 chars, should have embedding):")
            for i, (text, has_emb, correct) in enumerate(long_messages[:10]):
                status = "✓" if correct else "✗"
                if not correct:
                    logic_errors += 1
                print(f"  {status} '{text}...' -> Embedding: {has_emb}")
            
            print(f"\nSample metadata check:")
            cur.execute("""
                SELECT message_text, meta_data
                FROM messages 
                WHERE source = 'text' AND meta_data IS NOT NULL
                LIMIT 3
            """)
            
            for text, meta in cur.fetchall():
                phone = meta.get('phone_number', 'N/A') if isinstance(meta, dict) else 'N/A'
                direction = "sent by Matt" if meta.get('is_sent') else "received by Matt"
                print(f"  '{text[:30]}...' | Phone: {phone} | {direction}")
            
            # Final verdict
            print(f"\n=== FINAL VERDICT ===")
            if logic_errors == 0:
                print("✅ EMBEDDING LOGIC: PERFECT")
            else:
                print(f"❌ EMBEDDING LOGIC: {logic_errors} errors found")
                
            if metadata_issues == 0:
                print("✅ METADATA: PERFECT") 
            else:
                print(f"❌ METADATA: {metadata_issues} messages missing metadata")
            
            total_success = (logic_errors == 0 and metadata_issues == 0)
            return total_success, len(db_messages)

if __name__ == "__main__":
    print("=" * 60)
    print("PROCESSING 50 RANDOM MESSAGES WITH VERIFICATION")
    print("=" * 60)
    
    try:
        # Process 50 messages
        processed = process_50_messages()
        
        # Verify in database
        is_perfect, total_count = verify_database()
        
        print("\n" + "=" * 60)
        if is_perfect:
            print(f"🎉 SUCCESS! {total_count} messages processed with perfect logic!")
            print("Ready for full processing run.")
        else:
            print(f"❌ Issues found in {total_count} processed messages.")
            print("Need to fix before full run.")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()