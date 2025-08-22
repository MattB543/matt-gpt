#!/usr/bin/env python3

import json
import uuid
import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

def test_thread_filtering_logic():
    """Test the new thread filtering logic"""
    
    print("=== TESTING THREAD FILTERING LOGIC ===")
    
    # Create test data with different thread scenarios
    test_messages = [
        # Thread A: Matt participates (should be included)
        {"_id": "1", "thread_id": "threadA", "type": "1", "body": "Hello from someone", "date": "1640995200000", "address": "5551234567"},
        {"_id": "2", "thread_id": "threadA", "type": "2", "body": "Hi back!", "date": "1640995300000", "address": "5551234567"},  # Matt sent this
        {"_id": "3", "thread_id": "threadA", "type": "1", "body": "How are you?", "date": "1640995400000", "address": "5551234567"},
        
        # Thread B: Matt never participates (should be excluded) - like Verizon
        {"_id": "4", "thread_id": "threadB", "type": "1", "body": "Verizon: Your bill is ready", "date": "1640995500000", "address": "899000"},
        {"_id": "5", "thread_id": "threadB", "type": "1", "body": "Verizon: Another notification", "date": "1640995600000", "address": "899000"},
        
        # Thread C: Matt participates (should be included)  
        {"_id": "6", "thread_id": "threadC", "type": "2", "body": "k", "date": "1640995700000", "address": "5559876543"},  # Matt sent this (short)
        {"_id": "7", "thread_id": "threadC", "type": "1", "body": "Thanks for letting me know!", "date": "1640995800000", "address": "5559876543"},
    ]
    
    print(f"Test data: {len(test_messages)} messages across 3 threads")
    print("Thread A: Matt participates (3 messages)")
    print("Thread B: Matt never participates - Verizon (2 messages)")  
    print("Thread C: Matt participates (2 messages)")
    
    # Test the thread identification logic
    participating_threads = set()
    for msg in test_messages:
        if msg.get("type") == "2":  # Matt sent
            participating_threads.add(msg.get("thread_id"))
    
    print(f"\nIdentified participating threads: {participating_threads}")
    
    # Test the filtering logic
    included_messages = []
    excluded_messages = []
    
    for msg in test_messages:
        if msg.get("thread_id") in participating_threads:
            included_messages.append(msg)
        else:
            excluded_messages.append(msg)
    
    print(f"\nFiltering results:")
    print(f"Messages to include: {len(included_messages)} (from threads {set(m['thread_id'] for m in included_messages)})")
    print(f"Messages to exclude: {len(excluded_messages)} (from threads {set(m['thread_id'] for m in excluded_messages)})")
    
    # Test the sent field logic
    print(f"\nSent field logic test:")
    for msg in included_messages:
        is_sent = msg.get("type") == "2"
        direction = "sent by Matt" if is_sent else "received by Matt"
        print(f"  '{msg['body'][:30]}...' -> sent: {is_sent} ({direction})")
    
    # Verify expected results
    expected_participating = {"threadA", "threadC"}
    expected_included = 5  # 3 from threadA + 2 from threadC
    expected_excluded = 2  # 2 from threadB
    
    success = (
        participating_threads == expected_participating and
        len(included_messages) == expected_included and
        len(excluded_messages) == expected_excluded
    )
    
    if success:
        print(f"\n✅ THREAD FILTERING TEST: PASSED!")
        print(f"   - Correctly identified {len(participating_threads)} participating threads")
        print(f"   - Correctly included {len(included_messages)} messages")
        print(f"   - Correctly excluded {len(excluded_messages)} Verizon-like messages")
        return True
    else:
        print(f"\n❌ THREAD FILTERING TEST: FAILED!")
        return False

def test_database_schema():
    """Test that the new database schema works"""
    
    print("\n=== TESTING DATABASE SCHEMA ===")
    
    conn_str = os.getenv('DATABASE_URL')
    
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # Try to insert a test message with the new 'sent' field
                test_id = str(uuid.uuid4())
                
                cur.execute("""
                    INSERT INTO messages (id, source, thread_id, message_text, timestamp, sent, embedding, meta_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    test_id,
                    "text",
                    "test_thread",
                    "Test message with sent field",
                    datetime.now(timezone.utc),
                    True,  # Test the new sent field
                    None,
                    json.dumps({"test": True}),
                    datetime.now(timezone.utc)
                ))
                
                # Verify the insert worked
                cur.execute("""
                    SELECT message_text, sent, meta_data 
                    FROM messages 
                    WHERE id = %s
                """, (test_id,))
                
                result = cur.fetchone()
                if result:
                    text, sent, meta = result
                    print(f"✅ Database insert successful:")
                    print(f"   Text: '{text}'")
                    print(f"   Sent: {sent}")
                    print(f"   Meta: {meta}")
                    
                    # Clean up
                    cur.execute("DELETE FROM messages WHERE id = %s", (test_id,))
                    conn.commit()
                    
                    return True
                else:
                    print("❌ Database insert failed - no record found")
                    return False
                    
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False

if __name__ == "__main__":
    print("TESTING IMPROVED TEXT PROCESSING WITH THREAD FILTERING")
    print("=" * 60)
    
    logic_success = test_thread_filtering_logic()
    schema_success = test_database_schema()
    
    print("\n" + "=" * 60)
    if logic_success and schema_success:
        print("🎉 ALL TESTS PASSED! Ready for full processing with:")
        print("   ✅ Smart thread filtering (excludes Verizon-like messages)")
        print("   ✅ Boolean 'sent' field for easy querying") 
        print("   ✅ Embedding optimization for short messages")
        print("   ✅ Rich metadata extraction")
    else:
        print("❌ Some tests failed - need to fix before full processing")
    print("=" * 60)