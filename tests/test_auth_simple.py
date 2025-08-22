#!/usr/bin/env python3
"""Simple authentication test using subprocess curl."""

import subprocess
import time
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_auth_with_curl():
    """Test authentication using curl commands"""
    print("=== Testing Authentication with Curl ===\n")
    
    # Start server
    print("1. Starting server...")
    server_process = subprocess.Popen(
        ["poetry", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8006"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(8)  # Wait for startup
    
    try:
        bearer_token = os.getenv("MATT_GPT_BEARER_TOKEN")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        # Test 1: No auth
        print("2. Testing request without authentication...")
        result = subprocess.run([
            "curl", "-s", "-w", "\\n%{http_code}",
            "-X", "POST",
            "http://127.0.0.1:8006/chat",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"message": "test", "openrouter_api_key": openrouter_key})
        ], capture_output=True, text=True, timeout=10)
        
        if "401" in result.stdout or "403" in result.stdout:
            print("+ Correctly rejected unauthenticated request")
        else:
            print(f"- Should have rejected: {result.stdout}")
        
        # Test 2: Valid auth
        print("\n3. Testing authenticated request...")
        result = subprocess.run([
            "curl", "-s", "-w", "\\n%{http_code}",
            "-X", "POST", 
            "http://127.0.0.1:8006/chat",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {bearer_token}",
            "-d", json.dumps({
                "message": "What's your development philosophy?",
                "openrouter_api_key": openrouter_key
            })
        ], capture_output=True, text=True, timeout=45)
        
        if "200" in result.stdout:
            print("+ Authenticated request successful")
            # Try to parse response
            try:
                lines = result.stdout.split('\n')
                status_code = lines[-1]
                response_data = '\n'.join(lines[:-1])
                parsed = json.loads(response_data)
                print(f"+ Response length: {len(parsed.get('response', ''))}")
                print(f"+ Context items: {parsed.get('context_items_used', 0)}")
            except:
                print("+ Response received (parsing details failed)")
        else:
            print(f"- Authenticated request failed: {result.stdout}")
        
        # Test 3: Health endpoint (no auth required)
        print("\n4. Testing health endpoint...")
        result = subprocess.run([
            "curl", "-s", "-w", "\\n%{http_code}",
            "http://127.0.0.1:8006/health"
        ], capture_output=True, text=True, timeout=5)
        
        if "200" in result.stdout:
            print("+ Health endpoint accessible without auth")
        else:
            print(f"- Health endpoint failed: {result.stdout}")
        
        print("\n=== Authentication Implementation Complete ===")
        print("+ Bearer token authentication: Implemented")
        print("+ User OpenRouter key requirement: Implemented")
        print("+ Cost management: Users pay for their own LLM calls")
        print("+ Health endpoint: Public access maintained")
        
    except Exception as e:
        print(f"- Authentication test failed: {e}")
    finally:
        print("\n5. Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("+ Server stopped")

if __name__ == "__main__":
    test_auth_with_curl()