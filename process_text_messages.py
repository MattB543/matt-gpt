#!/usr/bin/env python3

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from database import get_session
from models import Message
from llm_client import OpenRouterClient
from sqlmodel import select
from tqdm import tqdm
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextMessageProcessor:
    """Process text messages from NDJSON format with date filtering and meta extraction"""
    
    def __init__(self, batch_size: int = 50, skip_existing: bool = False):
        self.batch_size = batch_size
        self.client = OpenRouterClient()
        self.cutoff_date = datetime(2021, 1, 1, tzinfo=timezone.utc)
        self.skip_existing = skip_existing
        self.existing_message_ids = set()
        
        logger.info(f"Text message processor initialized with batch_size={batch_size}")
        logger.info(f"Date filter: Only processing messages from {self.cutoff_date.strftime('%Y-%m-%d')} onwards")
        logger.info(f"Skip existing messages: {skip_existing}")
        
        # Load existing message IDs to avoid duplicates
        if skip_existing:
            self._load_existing_message_ids()
    
    def _load_existing_message_ids(self):
        """Load existing message IDs from database to avoid duplicates"""
        logger.info("Loading existing message IDs to avoid duplicates...")
        
        with get_session() as session:
            existing_messages = session.exec(
                select(Message)
                .where(Message.source == 'text')
                .where(Message.meta_data.isnot(None))
            ).all()
            
            for msg in existing_messages:
                if msg.meta_data and 'message_id' in msg.meta_data:
                    self.existing_message_ids.add(msg.meta_data['message_id'])
        
        logger.info(f"Found {len(self.existing_message_ids)} existing text message IDs")

    def process_ndjson_file(self, file_path: str) -> Dict[str, int]:
        """Process the text messages NDJSON file with streaming"""
        logger.info(f"Starting to process text messages from: {file_path}")
        
        stats = {
            "total_lines": 0,
            "valid_messages": 0,
            "filtered_by_date": 0,
            "skipped_duplicates": 0,
            "processed_messages": 0,
            "batch_count": 0,
            "errors": 0
        }
        
        batch = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                logger.info("Reading NDJSON file line by line...")
                
                for line_num, line in enumerate(file, 1):
                    stats["total_lines"] += 1
                    
                    if line_num % 1000 == 0:
                        logger.info(f"Processed {line_num} lines, found {stats['valid_messages']} valid messages")
                    
                    try:
                        # Parse JSON line
                        message_data = json.loads(line.strip())
                        
                        # Extract and validate message
                        processed_message = self._extract_message_data(message_data)
                        if not processed_message:
                            continue
                        
                        stats["valid_messages"] += 1
                        
                        # Apply date filter
                        if processed_message["timestamp"] < self.cutoff_date:
                            stats["filtered_by_date"] += 1
                            continue
                        
                        # Check for duplicates
                        message_id = processed_message["meta_data"].get("message_id")
                        if self.skip_existing and message_id in self.existing_message_ids:
                            stats["skipped_duplicates"] += 1
                            continue
                        
                        # Add to batch
                        batch.append(processed_message)
                        
                        # Process batch when full
                        if len(batch) >= self.batch_size:
                            success_count = self._process_batch(batch)
                            stats["processed_messages"] += success_count
                            stats["batch_count"] += 1
                            batch = []
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num}: {e}")
                        stats["errors"] += 1
                        continue
                    except Exception as e:
                        logger.error(f"Error processing line {line_num}: {e}")
                        stats["errors"] += 1
                        continue
                
                # Process remaining batch
                if batch:
                    success_count = self._process_batch(batch)
                    stats["processed_messages"] += success_count
                    stats["batch_count"] += 1
                
        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            raise
        
        logger.info("Text message processing completed!")
        self._log_final_stats(stats)
        return stats

    def _extract_message_data(self, raw_data: Dict) -> Optional[Dict]:
        """Extract relevant data from raw text message JSON"""
        try:
            # Get message text
            body = raw_data.get("body", "").strip()
            if not body:
                return None
            
            # Convert timestamp from milliseconds to datetime
            date_ms = raw_data.get("date")
            if not date_ms:
                return None
            
            try:
                timestamp = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
            except (ValueError, OverflowError):
                logger.warning(f"Invalid timestamp: {date_ms}")
                return None
            
            # Extract meta
            phone_number = raw_data.get("address", "")
            thread_id = raw_data.get("thread_id", "")
            message_id = raw_data.get("_id", "")
            message_type = raw_data.get("type", "")  # 1=received, 2=sent
            display_name = raw_data.get("__display_name", "")
            
            # Determine if this is sent or received
            is_sent = message_type == "2"
            
            # Create comprehensive meta
            meta = {
                "message_id": message_id,
                "phone_number": phone_number,
                "display_name": display_name,
                "message_type": message_type,
                "is_sent": is_sent,
                "read_status": raw_data.get("read", ""),
                "protocol": raw_data.get("protocol", ""),
                "service_center": raw_data.get("service_center", ""),
                "date_sent": raw_data.get("date_sent", ""),
                "raw_address": phone_number
            }
            
            return {
                "message_text": body,
                "timestamp": timestamp,
                "thread_id": thread_id,
                "meta_data": meta
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract message data: {e}")
            return None

    def _process_batch(self, batch: List[Dict]) -> int:
        """Process a batch of messages with embeddings and database storage"""
        logger.info(f"Processing batch of {len(batch)} messages...")
        
        success_count = 0
        
        try:
            with get_session() as session:
                for message_data in batch:
                    try:
                        # Generate embedding
                        logger.debug(f"Generating embedding for: {message_data['message_text'][:50]}...")
                        embedding = self.client.generate_embedding(message_data["message_text"])
                        
                        # Debug: show what keys are available
                        logger.debug(f"Available keys in message_data: {list(message_data.keys())}")
                        
                        # Create Message object
                        db_message = Message(
                            source="text",
                            thread_id=message_data["thread_id"],
                            message_text=message_data["message_text"],
                            timestamp=message_data["timestamp"],
                            embedding=embedding,
                            meta_data=message_data["meta_data"]
                        )
                        
                        session.add(db_message)
                        success_count += 1
                        
                    except Exception as e:
                        import traceback
                        logger.error(f"Failed to process message: {e}")
                        logger.error(f"Full traceback: {traceback.format_exc()}")
                        continue
                
                # Commit the batch
                session.commit()
                logger.info(f"Successfully committed {success_count}/{len(batch)} messages to database")
                
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
        
        return success_count

    
    def _log_final_stats(self, stats: Dict[str, int]):
        """Log comprehensive processing statistics"""
        logger.info("=== TEXT MESSAGE PROCESSING STATISTICS ===")
        logger.info(f"Total lines read: {stats['total_lines']:,}")
        logger.info(f"Valid messages found: {stats['valid_messages']:,}")
        logger.info(f"Filtered by date (before 2021-01-01): {stats['filtered_by_date']:,}")
        logger.info(f"Skipped duplicates: {stats['skipped_duplicates']:,}")
        logger.info(f"Successfully processed: {stats['processed_messages']:,}")
        logger.info(f"Total batches: {stats['batch_count']:,}")
        logger.info(f"Errors encountered: {stats['errors']:,}")
        
        if stats["valid_messages"] > 0:
            success_rate = (stats["processed_messages"] / (stats["valid_messages"] - stats["skipped_duplicates"] - stats["filtered_by_date"])) * 100
            logger.info(f"Processing success rate: {success_rate:.1f}%")
        
        logger.info("===========================================")


def main():
    """Main processing function"""
    file_path = os.path.join("raw_data", "texts", "messages.ndjson")
    
    if not os.path.exists(file_path):
        logger.error(f"Text messages file not found: {file_path}")
        return False
    
    logger.info(f"Text message file found: {file_path}")
    logger.info(f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")
    
    processor = TextMessageProcessor(batch_size=50)
    
    try:
        stats = processor.process_ndjson_file(file_path)
        
        if stats["processed_messages"] > 0:
            logger.info("✅ Text message processing completed successfully!")
            return True
        else:
            logger.warning("⚠️ No messages were processed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Text message processing failed: {e}")
        return False


if __name__ == "__main__":
    main()