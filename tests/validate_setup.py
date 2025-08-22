#!/usr/bin/env python3
"""Comprehensive validation of Phase 0 setup."""

import sys
import importlib
import os
from datetime import datetime

def test_imports():
    """Test that all required modules can be imported"""
    print("=== Testing Imports ===")
    
    modules_to_test = [
        "fastapi",
        "uvicorn", 
        "pgvector",
        "psycopg2",
        "sqlmodel",
        "openai",
        "dspy",
        "dotenv",
        "pydantic_settings",
        "httpx"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print(f"+ {module}")
        except ImportError as e:
            print(f"- {module}: {e}")
            failed_imports.append(module)
            
    if failed_imports:
        print(f"\nFailed imports: {failed_imports}")
        return False
    else:
        print("+ All required modules imported successfully")
        return True

def test_environment():
    """Test environment configuration"""
    print("\n=== Testing Environment ===")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["DATABASE_URL", "OPENROUTER_API_KEY", "OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"+ {var} configured")
        else:
            print(f"- {var} missing")
            missing_vars.append(var)
            
    if missing_vars:
        print(f"\nMissing environment variables: {missing_vars}")
        return False
    else:
        print("+ All environment variables configured")
        return True

def test_database_connection():
    """Test database connectivity"""
    print("\n=== Testing Database Connection ===")
    
    try:
        from database import get_session, engine
        from models import Message, PersonalityDoc, QueryLog
        
        # Test basic connection
        with get_session() as session:
            print("+ Database connection established")
            
        # Test table existence
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["messages", "personality_docs", "query_logs"]
        for table in expected_tables:
            if table in tables:
                print(f"+ Table '{table}' exists")
            else:
                print(f"- Table '{table}' missing")
                return False
                
        print("+ All required tables exist")
        return True
        
    except Exception as e:
        print(f"- Database connection failed: {e}")
        return False

def test_api_models():
    """Test API model definitions"""
    print("\n=== Testing API Models ===")
    
    try:
        from main import ChatRequest, ChatResponse
        
        # Test request model
        test_request = ChatRequest(message="test", openrouter_api_key="sk-or-v1-test")
        print("+ ChatRequest model working")
        
        # Test response model
        test_response = ChatResponse(
            response="test",
            query_id="test-id",
            latency_ms=100.0,
            context_items_used=0
        )
        print("+ ChatResponse model working")
        return True
        
    except Exception as e:
        print(f"- API model test failed: {e}")
        return False

def test_application_startup():
    """Test FastAPI application can be created"""
    print("\n=== Testing Application Startup ===")
    
    try:
        from main import app
        print("+ FastAPI application created successfully")
        
        # Check routes
        routes = [route.path for route in app.routes]
        expected_routes = ["/chat", "/health"]
        
        for route in expected_routes:
            if route in routes:
                print(f"+ Route '{route}' registered")
            else:
                print(f"- Route '{route}' missing")
                return False
                
        return True
        
    except Exception as e:
        print(f"- Application startup test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print(f"Matt-GPT Phase 0 Validation - {datetime.now()}")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Environment Test", test_environment), 
        ("Database Test", test_database_connection),
        ("API Models Test", test_api_models),
        ("Application Test", test_application_startup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"- {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY:")
    
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("+ ALL TESTS PASSED - Phase 0 setup is complete and working!")
        return 0
    else:
        print("- SOME TESTS FAILED - Please fix issues before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())