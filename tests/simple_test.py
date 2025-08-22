#!/usr/bin/env python3

import psycopg
import json
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

def test_basic_processing():
    """Test basic message processing logic without full infrastructure"""
    
    print("Testing basic message processing logic...")
    
    # Test the core logic
    test_messages = [
        ("Hi there how are you doing today?", True),   # Long - should get embedding
        ("Yes", False),                                # Short - no embedding  
        ("OK", False),                                 # Short - no embedding
        ("That sounds like a really great plan!", True), # Long - should get embedding
        ("lol", False),                               # Short - no embedding
        ("Maybe we should consider other options here", True), # Long - should get embedding
        ("k", False),                                 # Short - no embedding
    ]
    
    print("\nTesting embedding logic:")
    logic_correct = True
    
    for message, should_have_embedding in test_messages:
        message_len = len(message.strip())
        would_get_embedding = message_len > 5
        
        status = "PASS" if (would_get_embedding == should_have_embedding) else "FAIL"
        if would_get_embedding != should_have_embedding:
            logic_correct = False
            
        print(f"  '{message}' ({message_len} chars) -> Embedding: {would_get_embedding} [{status}]")
    
    if logic_correct:
        print("\nEmbedding logic test: PASSED")
    else:
        print("\nEmbedding logic test: FAILED")
        return False
    
    # Test database connection
    print("\nTesting database connection...")
    try:
        conn_str = os.getenv('DATABASE_URL')
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # Check if messages table exists and is accessible
                cur.execute("SELECT COUNT(*) FROM messages")
                count = cur.fetchone()[0]
                print(f"Database connected successfully. Current message count: {count:,}")
                
                # Test a simple insert
                test_data = {
                    'source': 'text',
                    'thread_id': 'test_123',
                    'message_text': 'This is a test message for validation',
                    'timestamp': datetime.now(timezone.utc),
                    'embedding': None,  # Test null embedding
                    'meta_data': {'test': True, 'phone_number': '1234567890'}
                }
                
                import uuid
                test_uuid = str(uuid.uuid4())
                
                cur.execute("""
                    INSERT INTO messages (id, source, thread_id, message_text, timestamp, embedding, meta_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    test_uuid,
                    test_data['source'],
                    test_data['thread_id'], 
                    test_data['message_text'],
                    test_data['timestamp'],
                    test_data['embedding'],
                    json.dumps(test_data['meta_data']),
                    datetime.now(timezone.utc)
                ))
                
                test_id = cur.fetchone()[0]
                print(f"Test insert successful, ID: {test_id}")
                
                # Verify the test record
                cur.execute("""
                    SELECT message_text, embedding, meta_data 
                    FROM messages 
                    WHERE id = %s
                """, (test_id,))
                
                text, embedding, metadata = cur.fetchone()
                print(f"Test record verification:")
                print(f"  Text: '{text}'")
                print(f"  Embedding: {embedding}")
                print(f"  Metadata: {metadata}")
                
                # Clean up test record
                cur.execute("DELETE FROM messages WHERE id = %s", (test_id,))
                print("Test record cleaned up")
                
                conn.commit()
                
    except Exception as e:
        print(f"Database test failed: {e}")
        return False
    
    print("\nDatabase test: PASSED")
    
    # Test raw data file access
    print("\nTesting raw data file access...")
    try:
        raw_file = "raw_data/texts/messages.ndjson"
        if not os.path.exists(raw_file):
            print(f"Raw data file not found: {raw_file}")
            return False
            
        sample_count = 0
        valid_count = 0
        
        with open(raw_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                sample_count += 1
                if sample_count > 100:  # Just sample first 100 lines
                    break
                    
                try:
                    data = json.loads(line.strip())
                    if data.get('body') and data.get('date') and data.get('thread_id'):
                        valid_count += 1
                        
                        if valid_count <= 3:  # Show first 3 valid messages
                            body = data['body'][:50]
                            phone = data.get('address', 'N/A')
                            msg_type = data.get('type', 'N/A')
                            print(f"  Sample {valid_count}: '{body}...' | Phone: {phone} | Type: {msg_type}")
                            
                except json.JSONDecodeError:
                    continue
        
        print(f"Raw data access: PASSED ({valid_count}/{sample_count} valid messages in sample)")
        
    except Exception as e:
        print(f"Raw data test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("SIMPLE PROCESSING TEST")
    print("=" * 60)
    
    success = test_basic_processing()
    
    if success:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! Ready for full processing.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TESTS FAILED! Need to fix issues before proceeding.")
        print("=" * 60)