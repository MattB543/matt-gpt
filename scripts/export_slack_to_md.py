#!/usr/bin/env python3

import json
import os
import glob
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set
import re

# Matt's user ID from the Slack export
MATT_USER_ID = "U01G5FH679T"
SLACK_DATA_PATH = "raw_data/slack"

def load_users() -> Dict[str, str]:
    """Load user ID to display name mapping"""
    users = {}
    users_file = os.path.join(SLACK_DATA_PATH, "users.json")
    
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
            for user in user_data:
                user_id = user.get('id')
                profile = user.get('profile', {})
                display_name = profile.get('display_name') or profile.get('real_name') or user.get('name', 'Unknown')
                users[user_id] = display_name
    
    return users

def format_user_name(full_name: str) -> str:
    """Format user name to First Last Initial"""
    if not full_name or full_name == 'Unknown':
        return full_name
    
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    
    first_name = parts[0]
    last_initial = parts[-1][0] if len(parts) > 1 else ''
    
    return f"{first_name} {last_initial}" if last_initial else first_name

def clean_message_text(text: str) -> str:
    """Clean Slack message text formatting"""
    if not text:
        return ""
    
    # Remove user mentions and replace with @user
    text = re.sub(r'<@([A-Z0-9]+)>', '@user', text)
    
    # Clean channel mentions  
    text = re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', text)
    text = re.sub(r'<#([A-Z0-9]+)>', '#channel', text)
    
    # Clean URLs - special handling for block-kit-builder
    text = re.sub(r'<(https://app\.slack\.com/block-kit-builder[^|>]+)\|([^>]+)>', r'\2 (https://app.slack.com/block-kit-builder)', text)
    text = re.sub(r'<(https://app\.slack\.com/block-kit-builder[^>]+)>', r'https://app.slack.com/block-kit-builder', text)
    text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2 (\1)', text)
    text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
    
    # Remove formatting but keep text
    text = re.sub(r'```([^`]+)```', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'~([^~]+)~', r'\1', text)
    
    # Clean emoji codes
    text = re.sub(r':([a-z0-9_+-]+):', r'[\1]', text)
    
    # Decode HTML entities
    text = text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def deduplicate_emojis(text: str) -> str:
    """Remove duplicate emojis in a row like [pray] [pray] [pray] -> [pray]"""
    # Pattern to match repeated emoji codes
    text = re.sub(r'(\[[a-z0-9_+-]+\])(\s*\1)+', r'\1', text)
    return text


def process_channel_messages(channel_dir: str, channel_name: str, users: Dict[str, str]) -> List[Dict]:
    """Process messages with context: include messages before Matt's on same day"""
    all_daily_messages = []
    
    # First, collect all messages by date
    for json_file in glob.glob(os.path.join(channel_dir, "*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                daily_messages = json.load(f)
                
            for msg in daily_messages:
                # Skip if no user or subtype messages
                if not msg.get('user') or msg.get('subtype'):
                    continue
                    
                # Skip if no text
                text = msg.get('text', '').strip()
                if not text:
                    continue
                
                # Parse timestamp
                try:
                    ts = float(msg.get('ts', 0))
                    date = datetime.fromtimestamp(ts)
                except (ValueError, TypeError):
                    continue
                
                # Get user info
                user_id = msg.get('user')
                user_name = users.get(user_id, 'Unknown')
                formatted_name = format_user_name(user_name)
                
                # Clean text
                clean_text = clean_message_text(text)
                clean_text = deduplicate_emojis(clean_text)
                
                all_daily_messages.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'timestamp': ts,
                    'channel': channel_name,
                    'user_id': user_id,
                    'user_name': formatted_name,
                    'text': clean_text,
                    'is_matt': user_id == MATT_USER_ID,
                    'is_reply': bool(msg.get('thread_ts')),
                    'thread_ts': msg.get('thread_ts')
                })
                
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by timestamp
    all_daily_messages.sort(key=lambda x: x['timestamp'])
    
    # Group by date and apply new logic
    messages_by_date = defaultdict(list)
    for msg in all_daily_messages:
        messages_by_date[msg['date']].append(msg)
    
    final_messages = []
    
    for date, day_messages in messages_by_date.items():
        # Find Matt's messages for this day
        matt_message_indices = [i for i, msg in enumerate(day_messages) if msg['is_matt']]
        
        if not matt_message_indices:
            continue  # No Matt messages this day
        
        # For each Matt message, include context messages before it on same day
        included_indices = set()
        
        for matt_idx in matt_message_indices:
            # Always include Matt's message
            included_indices.add(matt_idx)
            
            # Include all messages before Matt's message on same day
            for i in range(matt_idx):
                included_indices.add(i)
        
        # Add the selected messages
        for i in sorted(included_indices):
            final_messages.append(day_messages[i])
    
    return final_messages

def export_slack_messages():
    """Export Slack messages to markdown"""
    print("SLACK MESSAGE EXPORT TO MARKDOWN")
    print("=" * 60)
    
    # Load users
    print("Loading users...")
    users = load_users()
    print(f"Loaded {len(users)} users")
    
    # Process all channels
    all_messages = []
    channel_dirs = [d for d in os.listdir(SLACK_DATA_PATH) 
                   if os.path.isdir(os.path.join(SLACK_DATA_PATH, d)) and d not in ['channels.json', 'users.json']]
    
    print(f"Processing {len(channel_dirs)} channels...")
    
    for i, channel_name in enumerate(channel_dirs):
        channel_dir = os.path.join(SLACK_DATA_PATH, channel_name)
        if i % 20 == 0:  # Progress indicator every 20 channels
            print(f"  Processed {i}/{len(channel_dirs)} channels...")
        
        channel_messages = process_channel_messages(channel_dir, channel_name, users)
        all_messages.extend(channel_messages)
    
    if not all_messages:
        print("No messages found!")
        return
    
    print(f"Found {len(all_messages)} total messages")
    
    # Sort messages by date and timestamp
    all_messages.sort(key=lambda x: (x['date'], x['timestamp']))
    
    # Group by date and channel
    grouped = defaultdict(lambda: defaultdict(list))
    for msg in all_messages:
        grouped[msg['date']][msg['channel']].append(msg)
    
    # Filter threads based on Matt's participation percentage
    filtered_grouped = defaultdict(lambda: defaultdict(list))
    filtered_stats = {'total_threads': 0, 'kept_threads': 0, 'total_chars_before': 0, 'total_chars_after': 0}
    
    for date in grouped:
        for channel in grouped[date]:
            messages = grouped[date][channel]
            
            # Calculate character counts
            matt_chars = sum(len(msg['text']) for msg in messages if msg['is_matt'])
            total_chars = sum(len(msg['text']) for msg in messages)
            
            filtered_stats['total_threads'] += 1
            filtered_stats['total_chars_before'] += total_chars
            
            # Only keep thread if Matt contributes more than 10% of characters
            if total_chars > 0 and (matt_chars / total_chars) > 0.10:
                filtered_grouped[date][channel] = messages
                filtered_stats['kept_threads'] += 1
                filtered_stats['total_chars_after'] += total_chars
    
    grouped = filtered_grouped
    
    # Generate markdown
    lines = []
    lines.append("# Complete Slack Message History")
    lines.append("")
    lines.append(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Sort dates
    for date in sorted(grouped.keys()):
        lines.append(f"{date}")
        lines.append("")
        
        # Sort channels alphabetically
        for channel in sorted(grouped[date].keys()):
            messages = grouped[date][channel]
            
            lines.append(f"#{channel}")
            lines.append("")
            
            # Group consecutive messages from same non-Matt user
            grouped_messages = []
            current_group = None
            
            for msg in messages:
                if msg['is_matt']:
                    # Matt's messages stay separate
                    if current_group:
                        grouped_messages.append(current_group)
                        current_group = None
                    grouped_messages.append(msg)
                else:
                    # Non-Matt messages - group consecutive ones from same user
                    if current_group and current_group['user_name'] == msg['user_name']:
                        # Same user, add to current group
                        current_group['texts'].append(msg['text'])
                    else:
                        # Different user or first message, start new group
                        if current_group:
                            grouped_messages.append(current_group)
                        current_group = {
                            'user_name': msg['user_name'],
                            'texts': [msg['text']],
                            'is_matt': False,
                            'is_reply': msg['is_reply'],
                            'thread_ts': msg['thread_ts']
                        }
            
            # Don't forget the last group
            if current_group:
                grouped_messages.append(current_group)
            
            # Now format the grouped messages
            for item in grouped_messages:
                if item['is_matt']:
                    # Matt's individual messages
                    sender = "Matt"
                    if item['is_reply'] and item['thread_ts']:
                        lines.append(f"  └ {sender}: {item['text']}")
                    else:
                        lines.append(f"{sender}: {item['text']}")
                else:
                    # Grouped messages from others
                    sender = item['user_name']
                    combined_text = '\n'.join(item['texts'])
                    if item['is_reply'] and item['thread_ts']:
                        lines.append(f"  └ {sender}: {combined_text}")
                    else:
                        lines.append(f"{sender}: {combined_text}")
            
            lines.append("")
            lines.append("---")
            lines.append("")
    
    # Write to file
    output_file = "complete_slack_messages.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    # Calculate final message counts after filtering
    final_messages = []
    for date_channels in grouped.values():
        for channel_messages in date_channels.values():
            final_messages.extend(channel_messages)
    
    # Stats
    total_days = len(grouped)
    total_channels = len(set(msg['channel'] for msg in final_messages)) if final_messages else 0
    matt_messages = len([m for m in final_messages if m['is_matt']])
    thread_messages = len(final_messages) - matt_messages
    
    print("")
    print("Export complete!")
    print(f"File saved as: {output_file}")
    print(f"Thread Filtering Results:")
    print(f"  - Original threads: {filtered_stats['total_threads']}")
    print(f"  - Kept threads (>10% Matt): {filtered_stats['kept_threads']}")
    print(f"  - Threads filtered out: {filtered_stats['total_threads'] - filtered_stats['kept_threads']}")
    print(f"  - Character reduction: {filtered_stats['total_chars_before']:,} -> {filtered_stats['total_chars_after']:,}")
    print(f"Final Statistics:")
    print(f"  - Total Days: {total_days}")
    print(f"  - Total Channels: {total_channels}")
    print(f"  - Total Messages: {len(final_messages)}")
    print(f"  - Matt's Messages: {matt_messages}")
    print(f"  - Thread Messages: {thread_messages}")
    print("=" * 60)

if __name__ == "__main__":
    export_slack_messages()