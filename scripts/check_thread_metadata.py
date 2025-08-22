import psycopg
import os
from dotenv import load_dotenv
import json

load_dotenv()

conn_str = os.getenv('DATABASE_URL')
print(f"Connecting to: {conn_str}")

try:
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Check what's in the database for thread_id 2633
            cur.execute("""
                SELECT message_text, meta_data, timestamp 
                FROM messages 
                WHERE thread_id = '2633' 
                ORDER BY timestamp
                LIMIT 5
            """)
            results = cur.fetchall()
            
            print(f'Found {len(results)} messages for thread_id 2633:')
            for i, (text, metadata, timestamp) in enumerate(results):
                print(f'\n--- Message {i+1} ---')
                print(f'Text: {text[:100]}...')
                print(f'Timestamp: {timestamp}')
                print(f'Metadata: {json.dumps(metadata, indent=2)}')
                
except Exception as e:
    print(f"Error: {e}")