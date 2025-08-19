#!/usr/bin/env python3
"""Test database connection and basic operations."""

from database import get_session
from models import Message, PersonalityDoc, QueryLog
from datetime import datetime
from sqlmodel import select
import uuid

def test_database():
    """Test basic database operations"""
    
    print("Testing database connection...")
    
    # Test basic connection
    with get_session() as session:
        print("+ Database connection successful")
        
        # Test inserting a sample message
        test_message = Message(
            source="test",
            thread_id="test_thread",
            message_text="This is a test message",
            timestamp=datetime.utcnow(),
            meta_data={"test": True}
        )
        
        session.add(test_message)
        session.commit()
        print("+ Message insertion successful")
        
        # Test querying
        messages = session.exec(select(Message).where(Message.source == "test")).all()
        print(f"+ Message query successful: {len(messages)} test messages found")
        
        # Test personality doc
        test_doc = PersonalityDoc(
            doc_type="test",
            title="Test Document",
            content="This is test content for personality",
            meta_data={"test": True}
        )
        
        session.add(test_doc)
        session.commit()
        print("+ Personality document insertion successful")
        
        # Test query log
        test_log = QueryLog(
            query_text="test query",
            response_text="test response",
            model_used="test_model",
            context_used={"test": "context"},
            tokens_used=10,
            latency_ms=100.0
        )
        
        session.add(test_log)
        session.commit()
        print("+ Query log insertion successful")
        
        # Clean up test data
        # Clean up test data
        test_messages = session.exec(select(Message).where(Message.source == "test")).all()
        for msg in test_messages:
            session.delete(msg)
        
        test_docs = session.exec(select(PersonalityDoc).where(PersonalityDoc.doc_type == "test")).all()
        for doc in test_docs:
            session.delete(doc)
            
        test_logs = session.exec(select(QueryLog).where(QueryLog.model_used == "test_model")).all()
        for log in test_logs:
            session.delete(log)
        session.commit()
        print("+ Test data cleanup successful")
        
    print("\n+ All database tests passed!")

if __name__ == "__main__":
    test_database()