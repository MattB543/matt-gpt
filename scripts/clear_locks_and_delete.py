#!/usr/bin/env python3

import psycopg
import os
from dotenv import load_dotenv
import time

load_dotenv()

def clear_locks_and_delete_messages():
    """Clear any locks and delete all messages from the database"""
    conn_str = os.getenv('DATABASE_URL')
    
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                print("Checking for active connections and locks...")
                
                # Check for active connections
                cur.execute("""
                    SELECT pid, usename, application_name, state, query
                    FROM pg_stat_activity 
                    WHERE datname = current_database() 
                    AND pid != pg_backend_pid()
                    AND state != 'idle'
                """)
                
                active_connections = cur.fetchall()
                print(f"Found {len(active_connections)} active connections")
                
                for pid, user, app, state, query in active_connections:
                    print(f"  PID {pid}: {user} ({app}) - {state}")
                    if query:
                        print(f"    Query: {query[:100]}...")
                
                # Try to cancel any queries that might be holding locks
                print("\nCanceling any active queries...")
                for pid, _, _, _, query in active_connections:
                    if query and ('UPDATE messages' in query or 'DELETE FROM messages' in query):
                        print(f"Attempting to cancel PID {pid}...")
                        try:
                            cur.execute("SELECT pg_cancel_backend(%s)", (pid,))
                        except Exception as e:
                            print(f"  Could not cancel PID {pid}: {e}")
                
                # Wait a moment for cancellations to take effect
                time.sleep(2)
                
                # Check message count before deletion
                cur.execute("SELECT COUNT(*) FROM messages")
                message_count = cur.fetchone()[0]
                print(f"\nFound {message_count:,} messages to delete")
                
                if message_count == 0:
                    print("No messages to delete")
                    return
                
                # Try to delete all messages with a timeout
                print("Attempting to delete all messages...")
                cur.execute("SET statement_timeout = '30s'")
                cur.execute("DELETE FROM messages")
                
                deleted_count = cur.rowcount
                conn.commit()
                
                print(f"✅ Successfully deleted {deleted_count:,} messages")
                
                # Verify deletion
                cur.execute("SELECT COUNT(*) FROM messages")
                remaining = cur.fetchone()[0]
                print(f"Verification: {remaining} messages remaining")
                
                # Reset sequences if needed
                print("Resetting table statistics...")
                cur.execute("VACUUM ANALYZE messages")
                
    except psycopg.errors.DeadlockDetected:
        print("❌ Still getting deadlock. Let's try a different approach...")
        print("You may need to:")
        print("1. Wait a few more minutes for locks to clear")
        print("2. Or restart the PostgreSQL service/connection")
        print("3. Or use TRUNCATE instead of DELETE")
        
        # Try TRUNCATE as alternative (faster and avoids locks)
        try:
            print("\nTrying TRUNCATE instead...")
            with psycopg.connect(conn_str) as conn2:
                with conn2.cursor() as cur2:
                    cur2.execute("TRUNCATE TABLE messages RESTART IDENTITY CASCADE")
                    conn2.commit()
                    print("✅ TRUNCATE successful!")
        except Exception as e:
            print(f"❌ TRUNCATE also failed: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nAlternative approaches:")
        print("1. Wait 5-10 minutes and try again")
        print("2. Restart the database connection")
        print("3. Use TRUNCATE TABLE messages RESTART IDENTITY CASCADE")

if __name__ == "__main__":
    print("Attempting to clear locks and delete messages...")
    clear_locks_and_delete_messages()