#!/usr/bin/env python3

import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def clean_duplicates_keep_metadata():
    """Automatically delete duplicate messages, keeping ones with metadata"""
    conn_str = os.getenv('DATABASE_URL')
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # First, get a count of duplicates
            cur.execute("""
                SELECT COUNT(*) as duplicate_timestamps
                FROM (
                    SELECT timestamp
                    FROM messages 
                    GROUP BY timestamp
                    HAVING COUNT(*) > 1
                ) AS duplicates
            """)
            
            duplicate_count = cur.fetchone()[0]
            print(f"Found {duplicate_count} timestamps with duplicate messages")
            
            if duplicate_count == 0:
                print("No duplicates found!")
                return
            
            # Find duplicate timestamps
            cur.execute("""
                SELECT timestamp
                FROM messages 
                GROUP BY timestamp
                HAVING COUNT(*) > 1
                ORDER BY timestamp
            """)
            
            duplicate_timestamps = [row[0] for row in cur.fetchall()]
            print(f"Processing {len(duplicate_timestamps)} duplicate timestamps...")
            
            deleted_count = 0
            
            for i, timestamp in enumerate(duplicate_timestamps):
                # Get all messages for this timestamp, ordered so ones WITH metadata come first
                cur.execute("""
                    SELECT id, meta_data
                    FROM messages 
                    WHERE timestamp = %s
                    ORDER BY 
                        CASE 
                            WHEN meta_data IS NOT NULL AND meta_data::text != '{}' THEN 1
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
                        
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(duplicate_timestamps)} timestamps, deleted {deleted_count} duplicates")
            
            conn.commit()
            print(f"Deleted {deleted_count} duplicate messages, keeping ones with metadata")
            
            # Verify cleanup
            cur.execute("""
                SELECT COUNT(*) as remaining_duplicates
                FROM (
                    SELECT timestamp
                    FROM messages 
                    GROUP BY timestamp
                    HAVING COUNT(*) > 1
                ) AS duplicates
            """)
            
            remaining = cur.fetchone()[0]
            print(f"Verification: {remaining} timestamps still have duplicates (should be 0)")
            
            # Show final counts
            cur.execute("SELECT COUNT(*) FROM messages")
            total_messages = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text' AND (meta_data IS NULL OR meta_data::text = '{}')")
            text_without_meta = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text' AND meta_data IS NOT NULL AND meta_data::text != '{}'")
            text_with_meta = cur.fetchone()[0]
            
            print(f"\nFinal database state:")
            print(f"Total messages: {total_messages:,}")
            print(f"Text messages WITH metadata: {text_with_meta:,}")
            print(f"Text messages WITHOUT metadata: {text_without_meta:,}")

if __name__ == "__main__":
    print("Starting automated duplicate cleanup...")
    clean_duplicates_keep_metadata()
    print("Cleanup completed!")