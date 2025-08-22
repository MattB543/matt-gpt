#!/usr/bin/env python3
"""
Test script to verify enhanced logging functionality.
Runs a simple test to show all RAG results and prompt inputs/outputs.
"""

import logging
import os
from dotenv import load_dotenv

# Configure logging to show all levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

def test_enhanced_logging():
    """Test the enhanced logging functionality"""
    print("=" * 80)
    print("TESTING ENHANCED LOGGING FOR RAG AND PROMPTS")
    print("=" * 80)
    
    try:
        # Import after logging is configured
        from matt_gpt import setup_dspy
        
        print("Setting up MattGPT...")
        matt_gpt = setup_dspy()
        
        print("\nTesting with a simple question...")
        print("This should show:")
        print("1. RAG retrieval results")
        print("2. Raw prompt inputs")  
        print("3. Raw prompt outputs")
        print("4. Complete request/response cycle")
        
        # Test question
        test_question = "What's your approach to building software products?"
        
        # Use environment key for testing (no user key needed)
        result = matt_gpt.forward(test_question)
        
        print("\n" + "=" * 80)
        print("LOGGING TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"Response received: {len(result.response)} characters")
        print(f"Context items: {len(result.context_used)}")
        
    except Exception as e:
        print(f"\nLOGGING TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_logging()