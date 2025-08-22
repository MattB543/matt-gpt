#!/usr/bin/env python3

import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def check_database_results():
    """Check the final database results"""
    
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Get overall stats
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text'")
            total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text' AND embedding IS NOT NULL")
            with_embeddings = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text' AND embedding IS NULL")
            without_embeddings = cur.fetchone()[0]
            
            print("=== DATABASE RESULTS ===")
            print(f"Total text messages: {total}")
            print(f"With embeddings: {with_embeddings}")
            print(f"Without embeddings: {without_embeddings}")
            
            # Check embedding logic correctness
            print("\n=== EMBEDDING LOGIC CHECK ===")
            
            # Short messages that should NOT have embeddings
            cur.execute("""
                SELECT message_text, embedding IS NOT NULL as has_embedding
                FROM messages 
                WHERE source = 'text' AND LENGTH(TRIM(message_text)) <= 5
                ORDER BY created_at DESC
            """)
            
            short_messages = cur.fetchall()
            short_logic_errors = 0
            
            print(f"Short messages (<=5 chars, should have NO embedding): {len(short_messages)} found")
            for text, has_embedding in short_messages:
                if has_embedding:
                    short_logic_errors += 1
                    print(f"  ERROR: '{text}' has embedding but shouldn't")
                else:
                    print(f"  OK: '{text}' has no embedding")
            
            # Long messages that should have embeddings  
            cur.execute("""
                SELECT message_text, embedding IS NOT NULL as has_embedding
                FROM messages 
                WHERE source = 'text' AND LENGTH(TRIM(message_text)) > 5
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            long_messages = cur.fetchall()
            long_logic_errors = 0
            
            print(f"\nLong messages (>5 chars, should have embedding): showing 10 samples")
            for text, has_embedding in long_messages:
                if not has_embedding:
                    long_logic_errors += 1
                    print(f"  ERROR: '{text[:40]}...' missing embedding")
                else:
                    print(f"  OK: '{text[:40]}...' has embedding")
            
            # Check metadata quality
            print("\n=== METADATA CHECK ===")
            cur.execute("""
                SELECT message_text, meta_data
                FROM messages 
                WHERE source = 'text' AND meta_data IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            metadata_good = 0
            for text, meta_data in cur.fetchall():
                if isinstance(meta_data, dict) and meta_data != {}:
                    phone = meta_data.get('phone_number', 'N/A')
                    is_sent = meta_data.get('is_sent', 'Unknown')
                    direction = "sent by Matt" if is_sent else "received by Matt"
                    print(f"  OK: '{text[:30]}...' | Phone: {phone} | {direction}")
                    metadata_good += 1
                else:
                    print(f"  ERROR: '{text[:30]}...' has bad metadata")
            
            # Final verdict
            total_errors = short_logic_errors + long_logic_errors
            
            print(f"\n=== FINAL VERDICT ===")
            print(f"Embedding logic errors: {total_errors}")
            print(f"Messages with good metadata: {metadata_good}/5 samples")
            
            if total_errors == 0:
                print("EMBEDDING LOGIC: PERFECT!")
            else:
                print(f"EMBEDDING LOGIC: {total_errors} errors found")
                
            if metadata_good >= 4:
                print("METADATA: EXCELLENT!")
            else:
                print("METADATA: Issues found")
            
            if total_errors == 0 and metadata_good >= 4:
                print("\n🎉 SUCCESS: Processing logic is working perfectly!")
                print("Ready for full processing run.")
                return True
            else:
                print("\n❌ Issues found that need fixing")
                return False

if __name__ == "__main__":
    check_database_results()