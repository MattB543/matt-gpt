#!/usr/bin/env python3
"""Investigate specific message ID"""

from database import get_session
from models import Message
from sqlmodel import select

def investigate_message():
    target_id = "b3a5de32-fb4c-405b-997b-c3048902811f"
    
    with get_session() as session:
        # Find the specific message
        query = select(Message).where(Message.id == target_id)
        message = session.exec(query).first()
        
        if message:
            print(f"FOUND MESSAGE {target_id}:")
            print(f"Source: {message.source}")
            print(f"Thread ID: {message.thread_id}")
            print(f"From Matt GPT: {message.from_matt_gpt}")
            print(f"Sent: {message.sent}")
            print(f"Timestamp: {message.timestamp}")
            print(f"Text: {message.message_text}")
            print(f"Has embedding: {message.embedding is not None}")
            print(f"Text length: {len(message.message_text)}")
            print()
            
            # Get the full thread context for this message
            thread_query = select(Message).where(
                Message.thread_id == message.thread_id
            ).order_by(Message.timestamp)
            thread_messages = session.exec(thread_query).all()
            
            print(f"FULL THREAD CONTEXT (Thread: {message.thread_id}):")
            for i, msg in enumerate(thread_messages, 1):
                sender = "Matt" if msg.from_matt_gpt else "User"
                print(f"{i}. [{sender}] {msg.message_text}")
            print()
            
            # Check if there are similar messages with "prepping"
            prepping_query = select(Message).where(Message.message_text.contains("prepping"))
            prepping_messages = session.exec(prepping_query).all()
            
            print(f"Found {len(prepping_messages)} messages containing 'prepping':")
            for i, msg in enumerate(prepping_messages[:10], 1):
                print(f"{i}. ID: {msg.id}")
                print(f"   Text: {msg.message_text[:100]}...")
                print(f"   Source: {msg.source}, From Matt GPT: {msg.from_matt_gpt}")
                print()
            
        else:
            print(f"Message {target_id} not found in database")

if __name__ == "__main__":
    investigate_message()