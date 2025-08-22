#!/usr/bin/env python3

import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

load_dotenv()

def export_messages_to_markdown():
    """Export all text messages from database to a clean markdown file"""
    
    print("Exporting messages from database to markdown...")
    
    conn_str = os.getenv('DATABASE_URL')
    
    # Data structure: date -> thread_id -> messages
    messages_by_date_thread = defaultdict(lambda: defaultdict(list))
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Get all text messages ordered by date and time
            cur.execute("""
                SELECT 
                    message_text,
                    timestamp,
                    thread_id,
                    sent,
                    meta_data
                FROM messages 
                WHERE source = 'text'
                ORDER BY timestamp, thread_id
            """)
            
            messages = cur.fetchall()
            print(f"Found {len(messages):,} text messages to export")
            
            # Group messages by date and thread
            for message_text, timestamp, thread_id, sent, meta_data in messages:
                date_str = timestamp.strftime('%Y-%m-%d')
                
                # Extract display name and phone number
                display_name = "Unknown"
                phone = "Unknown"
                if meta_data and isinstance(meta_data, dict):
                    display_name = meta_data.get('display_name', '')
                    phone = meta_data.get('phone_number', 'Unknown')
                    
                    # Use display_name if available, otherwise last 4 digits
                    if display_name and display_name.strip():
                        contact_name = display_name.strip()
                    elif phone and phone != 'Unknown':
                        # Get last 4 digits
                        clean_phone = phone.replace('+1', '').replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                        if len(clean_phone) >= 4:
                            contact_name = f"x{clean_phone[-4:]}"
                        else:
                            contact_name = f"x{clean_phone}"
                    else:
                        contact_name = "Unknown"
                
                # Create thread identifier (will be updated later with participant info)
                thread_key = f"{thread_id}"
                
                # Add message to structure
                messages_by_date_thread[date_str][thread_key].append({
                    'text': message_text,
                    'sent': sent,
                    'time': timestamp.strftime('%H:%M'),
                    'contact_name': contact_name,
                    'display_name': display_name,
                    'phone': phone
                })
    
    # Generate markdown content
    markdown_content = []
    markdown_content.append("# Complete Text Message History")
    markdown_content.append("")
    markdown_content.append(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    markdown_content.append("")
    markdown_content.append("---")
    markdown_content.append("")
    
    # Sort dates chronologically
    sorted_dates = sorted(messages_by_date_thread.keys())
    
    for date_str in sorted_dates:
        # Date header
        markdown_content.append(f"## {date_str}")
        markdown_content.append("")
        
        threads_for_date = messages_by_date_thread[date_str]
        
        # Sort threads by first message time
        def get_first_message_time(thread_data):
            if thread_data[1]:  # If there are messages
                return min(msg.get('time', '00:00') for msg in thread_data[1])
            return '00:00'
        
        sorted_threads = sorted(threads_for_date.items(), 
                              key=lambda x: get_first_message_time(x))
        
        for thread_key, messages_in_thread in sorted_threads:
            # Determine thread participants and create proper thread name
            participants = set()
            contact_names = set()
            
            for msg in messages_in_thread:
                if not msg['sent'] and msg['contact_name'] != 'Unknown':
                    participants.add(msg['contact_name'])
                    contact_names.add(msg['contact_name'])
            
            # Create thread title
            if len(participants) == 1:
                # One-on-one conversation
                other_person = list(participants)[0]
                thread_title = f"Matt & {other_person}"
            else:
                # Group conversation or unknown participants
                if participants:
                    thread_title = f"Thread {thread_key}: {', '.join(sorted(participants))}"
                else:
                    thread_title = f"Thread {thread_key}"
            
            # Thread header
            markdown_content.append(f"### {thread_title}")
            markdown_content.append("")
            
            # Sort messages within thread by time
            sorted_messages = sorted(messages_in_thread, 
                                   key=lambda x: x.get('time', '00:00'))
            
            for msg in sorted_messages:
                # Format message based on who sent it
                if msg['sent']:
                    # Matt sent this message
                    sender = "Matt"
                else:
                    # Matt received this message
                    sender = msg['contact_name']
                
                markdown_content.append(f"{sender}: {msg['text']}")
            
            markdown_content.append("---")
            markdown_content.append("")
    
    # Write to file
    output_file = "complete_text_messages.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown_content))
    
    print("Export complete!")
    print(f"File saved as: {output_file}")
    print(f"Exported {len(sorted_dates)} days of messages")
    
    # Count total messages
    total_messages = 0
    for date_threads in messages_by_date_thread.values():
        for thread_messages in date_threads.values():
            total_messages += len(thread_messages)
    print(f"Total messages: {total_messages:,}")

def export_simple_format():
    """Export in the simpler format like your console example"""
    
    print("\nCreating simple format export...")
    
    conn_str = os.getenv('DATABASE_URL')
    
    # Data structure: date -> thread_id -> messages  
    messages_by_date_thread = defaultdict(lambda: defaultdict(list))
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    message_text,
                    timestamp,
                    thread_id,
                    sent,
                    meta_data
                FROM messages 
                WHERE source = 'text'
                ORDER BY timestamp
            """)
            
            messages = cur.fetchall()
            
            # Group by date and thread
            for message_text, timestamp, thread_id, sent, meta_data in messages:
                date_str = timestamp.strftime('%Y-%m-%d')
                
                messages_by_date_thread[date_str][thread_id].append({
                    'text': message_text,
                    'sent': sent,
                    'time': timestamp.strftime('%H:%M')
                })
    
    # Generate simple markdown
    simple_content = []
    simple_content.append("# Text Messages - Simple Format")
    simple_content.append("")
    
    for date_str in sorted(messages_by_date_thread.keys()):
        simple_content.append(f"## {date_str}")
        simple_content.append("")
        
        threads_for_date = messages_by_date_thread[date_str]
        
        for thread_id in sorted(threads_for_date.keys()):
            simple_content.append(f"=== {thread_id} - {date_str} ===")
            simple_content.append("")
            
            messages_in_thread = threads_for_date[thread_id]
            
            for msg in messages_in_thread:
                simple_content.append(f"[{msg['time']}] {msg['text']}")
                simple_content.append("")
            
            simple_content.append("")
    
    # Write simple format
    simple_file = "text_messages_simple.md"
    
    with open(simple_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(simple_content))
    
    print("Simple format export complete!")
    print(f"File saved as: {simple_file}")

if __name__ == "__main__":
    print("=" * 60)
    print("TEXT MESSAGE EXPORT TO MARKDOWN")
    print("=" * 60)
    
    try:
        # Check if we have any messages to export
        conn_str = os.getenv('DATABASE_URL')
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM messages WHERE source = 'text'")
                count = cur.fetchone()[0]
                
                if count == 0:
                    print("No text messages found in database!")
                    print("Run the text processing script first: python process_text_messages.py")
                    exit(1)
                
                print(f"Found {count:,} text messages to export")
        
        # Export in both formats
        export_messages_to_markdown()
        export_simple_format()
        
        print("\n" + "=" * 60)
        print("Export completed! You now have:")
        print("  complete_text_messages.md - Detailed format with contact names")
        print("  text_messages_simple.md - Simple format like your example")
        print("=" * 60)
        
    except Exception as e:
        print(f"Export failed: {e}")
        import traceback
        traceback.print_exc()