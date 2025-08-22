#!/usr/bin/env python3

import logging
from process_text_messages import TextMessageProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_5_messages():
    """Test processing just 5 messages"""
    source_file = "raw_data/texts/messages.ndjson"
    test_file = "test_5_messages.ndjson"
    
    logger.info("Creating test file with 5 messages...")
    
    try:
        with open(source_file, 'r', encoding='utf-8') as infile:
            with open(test_file, 'w', encoding='utf-8') as outfile:
                for i, line in enumerate(infile):
                    if i >= 5:
                        break
                    outfile.write(line)
        
        logger.info(f"Test file created: {test_file}")
        
        # Process the test file
        processor = TextMessageProcessor(batch_size=5, skip_existing=False)
        stats = processor.process_ndjson_file(test_file)
        
        logger.info(f"Processing completed! Stats: {stats}")
        
        # Clean up
        import os
        os.remove(test_file)
        logger.info("Test file cleaned up")
        
        return stats["processed_messages"] > 0
        
    except Exception as e:
        import traceback
        logger.error(f"Test failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_5_messages()
    print(f"Test result: {'✅ SUCCESS' if success else '❌ FAILED'}")