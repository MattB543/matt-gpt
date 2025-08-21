#!/usr/bin/env python3
"""Integration test for the entire Matt-GPT system."""

import requests
import time
import json
from database import get_session
from models import QueryLog
from sqlmodel import select
from test_server_manager import test_server

def test_integration():
    """Test the complete system integration"""
    print("=== Matt-GPT Integration Test ===\n")
    
    with test_server(8001) as server:
        print("+ Server started and ready")
        
        try:
            # Test health endpoint
            print("\n1. Testing health endpoint...")
            health_response = requests.get("http://127.0.0.1:8001/health", timeout=5)
            if health_response.status_code == 200:
                print("+ Health endpoint working")
                print(f"  Response: {health_response.json()}")
            else:
                print(f"- Health endpoint failed: {health_response.status_code}")
                
            # Test chat endpoint
            print("\n2. Testing chat endpoint...")
            chat_payload = {
                "message": "Hello, this is a test message",
                "model": "anthropic/claude-3.5-sonnet"
            }
            
            chat_response = requests.post(
                "http://127.0.0.1:8001/chat", 
                json=chat_payload,
                timeout=10
            )
            
            if chat_response.status_code == 200:
                print("+ Chat endpoint working")
                response_data = chat_response.json()
                print(f"  Query ID: {response_data['query_id']}")
                print(f"  Latency: {response_data['latency_ms']:.2f}ms")
                print(f"  Response: {response_data['response'][:100]}...")
            else:
                print(f"- Chat endpoint failed: {chat_response.status_code}")
                print(f"  Error: {chat_response.text}")
                
            # Wait for background logging to complete
            time.sleep(1)
            
            # Test query logging
            print("\n3. Testing query logging...")
            with get_session() as session:
                recent_logs = session.exec(
                    select(QueryLog).order_by(QueryLog.created_at.desc()).limit(1)
                ).all()
                
                if recent_logs:
                    log = recent_logs[0]
                    print("+ Query logging working")
                    print(f"  Logged query: {log.query_text[:50]}...")
                    print(f"  Model used: {log.model_used}")
                    print(f"  Latency: {log.latency_ms:.2f}ms")
                else:
                    print("- No query logs found")
                    
        except requests.exceptions.RequestException as e:
            print(f"- Request failed: {e}")
        except Exception as e:
            print(f"- Integration test failed: {e}")
            
    print("\n4. Server automatically stopped")
    print("\n=== Integration Test Complete ===")

if __name__ == "__main__":
    test_integration()