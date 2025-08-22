#!/usr/bin/env python3

import json
import logging
from process_text_messages import TextMessageProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_first_line():
    """Debug the first line that's causing errors"""
    file_path = "raw_data/texts/messages.ndjson"
    
    logger.info("Testing first line of NDJSON file...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline()
            
        logger.info(f"First line length: {len(first_line)}")
        logger.info(f"First line preview: {first_line[:200]}...")
        
        # Try to parse JSON
        try:
            message_data = json.loads(first_line.strip())
            logger.info("✅ JSON parsing successful")
            logger.info(f"Keys in JSON: {list(message_data.keys())}")
            
            # Test message extraction
            processor = TextMessageProcessor()
            logger.info("Testing message extraction...")
            
            result = processor._extract_message_data(message_data)
            
            if result:
                logger.info("✅ Message extraction successful!")
                logger.info(f"Extracted keys: {list(result.keys())}")
                logger.info(f"Message text: {result['message_text'][:50]}...")
                logger.info(f"Meta_data keys: {list(result['meta_data'].keys())}")
            else:
                logger.error("❌ Message extraction failed - returned None")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
        except Exception as e:
            logger.error(f"❌ Error in message extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
    except Exception as e:
        logger.error(f"❌ Failed to read file: {e}")

if __name__ == "__main__":
    debug_first_line()