#!/usr/bin/env python3

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

def test_api():
    """Test the API with a simple request"""
    
    # API configuration
    url = "http://127.0.0.1:9000/chat"
    bearer_token = os.getenv("MATT_GPT_BEARER_TOKEN")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if not bearer_token:
        print("ERROR: MATT_GPT_BEARER_TOKEN not found in environment")
        return False
    
    if not openrouter_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment")
        return False
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "How do you approach product development?",
        "openrouter_api_key": openrouter_key,
        "model": "anthropic/claude-3.5-sonnet"
    }
    
    print("Testing Matt-GPT API...")
    print(f"URL: {url}")
    print(f"Bearer token: {bearer_token[:20]}...")
    print(f"OpenRouter key: {openrouter_key[:20]}...")
    print(f"Message: {payload['message']}")
    
    start_time = time.time()
    
    try:
        print("\nSending request...")
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        
        print(f"Response received in {duration:.2f}ms")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS!")
            print(f"Response: {data.get('response', 'No response')[:200]}...")
            print(f"Query ID: {data.get('query_id')}")
            print(f"API Latency: {data.get('latency_ms', 0):.2f}ms")
            print(f"Context Items: {data.get('context_items_used', 0)}")
            return True
        else:
            print(f"ERROR {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out after 45 seconds")
        return False
    except Exception as e:
        print(f"ERROR: Request failed: {e}")
        return False

if __name__ == "__main__":
    test_api()