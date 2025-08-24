#!/usr/bin/env python3
"""Quick test of the Matt-GPT API call format"""

import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

# Test a single API call
api_url = "http://127.0.0.1:9005/chat"
bearer_token = os.getenv('MATT_GPT_BEARER_TOKEN')
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')

headers = {
    'Authorization': f'Bearer {bearer_token}',
    'Content-Type': 'application/json'
}

payload = {
    'message': "Test message: What do you think about pizza?",
    'openrouter_api_key': openrouter_api_key,
    'other_conversation_context': False
}

print("Testing API call...")
print(f"URL: {api_url}")
print(f"Headers: {headers}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(api_url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    response.raise_for_status()
    result = response.json()
    print(f"Success! Response: {result.get('response', 'No response field')}")
except Exception as e:
    print(f"Error: {e}")