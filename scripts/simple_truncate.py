#!/usr/bin/env python3

import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def simple_truncate():
    """Simple TRUNCATE to clear messages table"""
    conn_str = os.getenv('DATABASE_URL')
    
    try:
        print("Connecting to database...")
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                print("Executing TRUNCATE TABLE messages...")
                cur.execute("TRUNCATE TABLE messages RESTART IDENTITY CASCADE")
                conn.commit()
                print("✅ Messages table cleared successfully!")
                
                # Verify
                cur.execute("SELECT COUNT(*) FROM messages")
                count = cur.fetchone()[0]
                print(f"Verification: {count} messages remaining")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nIf this fails, you may need to:")
        print("1. Wait for the PostgreSQL locks to timeout")
        print("2. Restart your database connection")
        print("3. Or manually run: TRUNCATE TABLE messages RESTART IDENTITY CASCADE;")

if __name__ == "__main__":
    simple_truncate()