#!/usr/bin/env python3
"""Test LLM client initialization and configuration."""

import os
from llm_client import OpenRouterClient

def test_llm_client():
    """Test LLM client setup"""
    print("Testing LLM client initialization...")
    
    # Test client initialization (will warn about missing keys)
    try:
        client = OpenRouterClient()
        print("+ OpenRouter client created successfully")
        
        # Check if API keys are configured
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if openrouter_key:
            print("+ OPENROUTER_API_KEY is configured")
        else:
            print("- OPENROUTER_API_KEY not found (will need for chat completions)")
            
        if openai_key:
            print("+ OPENAI_API_KEY is configured")
        else:
            print("- OPENAI_API_KEY not found (will need for embeddings)")
            
    except Exception as e:
        print(f"- LLM client initialization failed: {e}")
        return False
        
    print("+ LLM client test completed")
    return True

if __name__ == "__main__":
    test_llm_client()