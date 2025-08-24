#!/usr/bin/env python3
"""
Test script to verify other_conversation_context parameter works
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://127.0.0.1:9005/chat"
BEARER_TOKEN = os.getenv("MATT_GPT_BEARER_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def test_personality_only():
    """Test personality-only mode vs full RAG mode"""
    
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    test_query = "What are your core values and beliefs?"
    
    print("=== Testing Full RAG Mode (other_conversation_context=True) ===")
    payload_full = {
        "message": test_query,
        "openrouter_api_key": OPENROUTER_API_KEY,
        "model": "anthropic/claude-3.5-sonnet",
        "other_conversation_context": True
    }
    
    response_full = requests.post(API_URL, headers=headers, json=payload_full)
    print(f"Status: {response_full.status_code}")
    if response_full.ok:
        result_full = response_full.json()
        print(f"Response length: {len(result_full['response'])}")
        print(f"Context items used: {result_full['context_items_used']}")
        print(f"Response preview: {result_full['response'][:200]}...")
    else:
        print(f"Error: {response_full.text}")
    
    print("\n" + "="*80 + "\n")
    
    print("=== Testing Personality-Only Mode (other_conversation_context=False) ===")
    payload_personality = {
        "message": test_query,
        "openrouter_api_key": OPENROUTER_API_KEY,
        "model": "anthropic/claude-3.5-sonnet",
        "other_conversation_context": False
    }
    
    response_personality = requests.post(API_URL, headers=headers, json=payload_personality)
    print(f"Status: {response_personality.status_code}")
    if response_personality.ok:
        result_personality = response_personality.json()
        print(f"Response length: {len(result_personality['response'])}")
        print(f"Context items used: {result_personality['context_items_used']}")
        print(f"Response preview: {result_personality['response'][:200]}...")
    else:
        print(f"Error: {response_personality.text}")

if __name__ == "__main__":
    test_personality_only()