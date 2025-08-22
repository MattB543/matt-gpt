#!/usr/bin/env python3
"""
Simple script to count total characters in text message bodies.
"""

import json

def count_text_characters():
    """Count total characters in text message bodies from Jan 2021 onwards."""
    total_characters = 0
    message_count = 0
    filtered_count = 0
    
    # January 1, 2021 00:00:00 UTC in milliseconds
    jan_2021_timestamp = 1609459200000
    
    try:
        with open('raw_data/texts/messages.ndjson', 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    message = json.loads(line.strip())
                    message_count += 1
                    
                    # Check if message is from Jan 2021 onwards
                    date = int(message.get('date', 0))
                    if date >= jan_2021_timestamp:
                        body = message.get('body', '')
                        total_characters += len(body)
                        filtered_count += 1
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
    
    except FileNotFoundError:
        print("Error: raw_data/texts/messages.ndjson not found")
        return
    
    print(f"Total messages processed: {message_count:,}")
    print(f"Messages from Jan 2021 onwards: {filtered_count:,}")
    print(f"Total characters in filtered message bodies: {total_characters:,}")
    
    if filtered_count > 0:
        avg_chars = total_characters / filtered_count
        print(f"Average characters per filtered message: {avg_chars:.1f}")

if __name__ == "__main__":
    count_text_characters()