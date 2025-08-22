#!/usr/bin/env python3

import psycopg
import os
from dotenv import load_dotenv
import json

load_dotenv()

def check_specific_timestamp():
    """Check the specific timestamp you mentioned"""
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, message_text, timestamp, thread_id, source, meta_data
                FROM messages 
                WHERE timestamp = '2022-06-06 18:54:42.000'
                ORDER BY id
            """)
            
            results = cur.fetchall()
            print(f"Found {len(results)} messages with timestamp '2022-06-06 18:54:42.000':")
            
            for i, (msg_id, text, timestamp, thread_id, source, metadata) in enumerate(results):
                print(f"\n--- Message {i+1} (ID: {msg_id}) ---")
                print(f"Text: {text[:80]}...")
                print(f"Source: {source}")
                print(f"Thread: {thread_id}")
                print(f"Has metadata: {'Yes' if metadata and metadata != {} else 'No'}")
                if metadata and metadata != {}:
                    print(f"Phone: {metadata.get('phone_number', 'N/A')}")

def find_duplicate_timestamps():
    """Find all messages with duplicate timestamps"""
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT timestamp, COUNT(*) as count
                FROM messages 
                GROUP BY timestamp
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            duplicates = cur.fetchall()
            print(f"\nFound {len(duplicates)} timestamps with duplicates:")
            
            for timestamp, count in duplicates:
                print(f"\nTimestamp: {timestamp} ({count} duplicates)")
                
                # Get details for this timestamp
                cur.execute("""
                    SELECT id, message_text, source, meta_data, thread_id
                    FROM messages 
                    WHERE timestamp = %s
                    ORDER BY id
                """, (timestamp,))
                
                records = cur.fetchall()
                for i, (msg_id, text, source, metadata, thread_id) in enumerate(records):
                    has_meta = "Yes" if metadata and metadata != {} else "No"
                    phone = metadata.get('phone_number', 'N/A') if metadata else 'N/A'
                    print(f"  {i+1}. ID:{msg_id} [{source}] Meta:{has_meta} Phone:{phone} Thread:{thread_id}")
                    print(f"     Text: {text[:60]}...")

def delete_duplicates_keep_with_metadata():
    """Delete duplicate messages, keeping ones with metadata"""
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Find duplicate timestamps
            cur.execute("""
                SELECT timestamp
                FROM messages 
                GROUP BY timestamp
                HAVING COUNT(*) > 1
            """)
            
            duplicate_timestamps = [row[0] for row in cur.fetchall()]
            print(f"Processing {len(duplicate_timestamps)} timestamps with duplicates...")
            
            deleted_count = 0
            
            for timestamp in duplicate_timestamps:
                # Get all messages for this timestamp
                cur.execute("""
                    SELECT id, meta_data
                    FROM messages 
                    WHERE timestamp = %s
                    ORDER BY 
                        CASE 
                            WHEN meta_data IS NOT NULL AND meta_data != '{}' THEN 1
                            ELSE 2
                        END,
                        id
                """, (timestamp,))
                
                records = cur.fetchall()
                if len(records) > 1:
                    # Keep the first one (which will be the one with metadata if any exists)
                    # Delete the rest
                    ids_to_delete = [record[0] for record in records[1:]]
                    
                    for msg_id in ids_to_delete:
                        cur.execute("DELETE FROM messages WHERE id = %s", (msg_id,))
                        deleted_count += 1
                        
                    if deleted_count % 100 == 0:
                        print(f"Deleted {deleted_count} duplicate messages so far...")
            
            conn.commit()
            print(f"Deleted {deleted_count} duplicate messages, keeping ones with metadata")

if __name__ == "__main__":
    print("Checking specific timestamp...")
    check_specific_timestamp()
    
    print("\nFinding duplicate timestamps...")
    find_duplicate_timestamps()
    
    print("\nDo you want to delete duplicates? (y/N): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        print("Deleting duplicates...")
        delete_duplicates_keep_with_metadata()
        
        print("\nVerification - checking duplicates again...")
        find_duplicate_timestamps()
    else:
        print("Skipping deletion.")