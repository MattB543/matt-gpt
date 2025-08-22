#!/usr/bin/env python3

import json
import logging
from datetime import datetime, timezone
from process_text_messages import TextMessageProcessor
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_sample():
    """Create a small test sample from the first few lines"""
    source_file = os.path.join("raw_data", "texts", "messages.ndjson")
    test_file = "test_messages_sample.ndjson"
    
    logger.info("Creating test sample from first 10 lines...")
    
    try:
        with open(source_file, 'r', encoding='utf-8') as infile:
            with open(test_file, 'w', encoding='utf-8') as outfile:
                for i, line in enumerate(infile):
                    if i >= 10:  # Only take first 10 lines
                        break
                    outfile.write(line)
        
        logger.info(f"Test sample created: {test_file}")
        return test_file
    
    except Exception as e:
        logger.error(f"Failed to create test sample: {e}")
        return None

def test_message_extraction():
    """Test the message extraction logic with sample data"""
    logger.info("Testing message extraction logic...")
    
    processor = TextMessageProcessor()
    
    # Test with the first message from our earlier examination
    test_message = {
        "_id": "72125",
        "thread_id": "2789", 
        "address": "+18584295259",
        "date": "1755099536162",  # This should be after 2021
        "body": "Oh, and I'll stick to the morning time if that's okay.",
        "type": "1",
        "__display_name": "Test Contact"
    }
    
    logger.info("Testing message extraction...")
    result = processor._extract_message_data(test_message)
    
    if result:
        logger.info("✅ Message extraction successful!")
        logger.info(f"Message text: {result['message_text']}")
        logger.info(f"Timestamp: {result['timestamp']}")
        logger.info(f"Thread ID: {result['thread_id']}")
        logger.info(f"Metadata keys: {list(result['meta_data'].keys())}")
        logger.info(f"Phone number: {result['meta_data']['phone_number']}")
        logger.info(f"Is sent: {result['meta_data']['is_sent']}")
        
        # Check date filter
        cutoff_date = datetime(2021, 1, 1, tzinfo=timezone.utc)
        if result['timestamp'] >= cutoff_date:
            logger.info("✅ Message passes date filter (2021+)")
        else:
            logger.info("❌ Message would be filtered out (before 2021)")
        
        return True
    else:
        logger.error("❌ Message extraction failed")
        return False

def test_processor_sample():
    """Test the full processor with a small sample"""
    logger.info("Testing full processor with sample data...")
    
    test_file = create_test_sample()
    if not test_file:
        return False
    
    try:
        processor = TextMessageProcessor(batch_size=5)
        stats = processor.process_ndjson_file(test_file)
        
        logger.info("Sample processing completed!")
        logger.info(f"Stats: {stats}")
        
        # Clean up test file
        os.remove(test_file)
        logger.info("Test file cleaned up")
        
        return stats["processed_messages"] > 0
        
    except Exception as e:
        logger.error(f"Sample processing failed: {e}")
        # Clean up test file on error
        if os.path.exists(test_file):
            os.remove(test_file)
        return False

def main():
    """Run all tests"""
    logger.info("=== TESTING TEXT MESSAGE PROCESSOR ===")
    
    # Test 1: Message extraction
    logger.info("\n--- Test 1: Message Extraction ---")
    test1_pass = test_message_extraction()
    
    # Test 2: Sample processing
    logger.info("\n--- Test 2: Sample Processing ---")
    test2_pass = test_processor_sample()
    
    # Summary
    logger.info("\n=== TEST RESULTS ===")
    logger.info(f"Message extraction: {'✅ PASS' if test1_pass else '❌ FAIL'}")
    logger.info(f"Sample processing: {'✅ PASS' if test2_pass else '❌ FAIL'}")
    
    overall_pass = test1_pass and test2_pass
    logger.info(f"Overall: {'✅ ALL TESTS PASSED' if overall_pass else '❌ SOME TESTS FAILED'}")
    
    return overall_pass

if __name__ == "__main__":
    main()