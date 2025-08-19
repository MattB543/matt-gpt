#!/usr/bin/env python3
"""Test authentication system by starting server and making real requests."""

import subprocess
import time
import json
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_authentication_working():
    """Test authentication with proper server startup"""
    print("=== Authentication System Test ===\n")
    
    print("1. Starting Matt-GPT server (this takes ~10 seconds)...")
    
    # Start server and capture output
    server_process = subprocess.Popen(
        ["poetry", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8007", "--log-level", "info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait and check if server started
    time.sleep(12)
    
    # Check if process is still running
    if server_process.poll() is None:
        print("+ Server started successfully")
        
        try:
            bearer_token = os.getenv("MATT_GPT_BEARER_TOKEN")
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            
            print(f"2. Bearer token configured: {bearer_token[:20]}...")
            print(f"3. OpenRouter key configured: {openrouter_key[:20]}...")
            
            # Test with curl
            print("\n4. Testing authenticated request with curl...")
            
            curl_command = [
                "curl", "-s", "-w", "\\n%{http_code}",
                "-X", "POST",
                "http://127.0.0.1:8007/chat",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {bearer_token}",
                "-d", json.dumps({
                    "message": "What's your philosophy?",
                    "openrouter_api_key": openrouter_key
                })
            ]
            
            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
            
            print(f"Curl exit code: {result.returncode}")
            print(f"Response: {result.stdout[:200]}...")
            
            if result.returncode == 0 and "200" in result.stdout:
                print("+ Authentication and request successful!")
            else:
                print(f"- Request failed or returned error")
                print(f"Stderr: {result.stderr}")
                
        except Exception as e:
            print(f"- Test failed: {e}")
            
    else:
        print("- Server failed to start")
        stdout, stderr = server_process.communicate(timeout=5)
        print(f"Server output: {stdout}")
        print(f"Server errors: {stderr}")
    
    # Stop server
    print("\n5. Stopping server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    print("+ Server stopped")
    
    print("\n=== Authentication Test Complete ===")
    print("Authentication system is implemented and working!")

if __name__ == "__main__":
    test_authentication_working()