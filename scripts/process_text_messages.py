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

    def _identify_participating_threads(self, file_path: str) -> set:
        """First pass: Identify threads where Matt sent at least one message"""
        logger.info("First pass: Identifying threads where Matt participates...")
        
        participating_threads = set()
        lines_scanned = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                lines_scanned += 1
                
                if line_num % 10000 == 0:
                    logger.info(f"Scanned {line_num:,} lines, found {len(participating_threads)} participating threads")
                
                try:
                    message_data = json.loads(line.strip())
                    
                    # Check if Matt sent this message (type == "2")
                    if message_data.get("type") == "2":
                        thread_id = message_data.get("thread_id")
                        if thread_id:
                            participating_threads.add(thread_id)
                            
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
        
        logger.info(f"Thread identification complete: {lines_scanned:,} lines scanned")
        logger.info(f"Found {len(participating_threads)} threads where Matt participates")
        return participating_threads

    def process_ndjson_file(self, file_path: str) -> Dict[str, int]:
        """Process the text messages NDJSON file with smart thread filtering"""
        logger.info(f"Starting to process text messages from: {file_path}")
        
        # First pass: Identify participating threads
        participating_threads = self._identify_participating_threads(file_path)
        
        stats = {
            "total_lines": 0,
            "valid_messages": 0,
            "filtered_by_date": 0,
            "filtered_by_thread": 0,
            "skipped_duplicates": 0,
            "processed_messages": 0,
            "messages_with_embeddings": 0,
            "short_messages_no_embedding": 0,
            "batch_count": 0,
            "errors": 0,
            "participating_threads": len(participating_threads)
        }
        
        batch = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                logger.info("Second pass: Processing messages from participating threads...")
                
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
                        
                        # Apply thread participation filter
                        if processed_message["thread_id"] not in participating_threads:
                            stats["filtered_by_thread"] += 1
                            continue
                        
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
                            batch_stats = self._process_batch(batch)
                            stats["processed_messages"] += batch_stats["processed"]
                            stats["messages_with_embeddings"] += batch_stats["with_embeddings"]
                            stats["short_messages_no_embedding"] += batch_stats["no_embeddings"]
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
                    batch_stats = self._process_batch(batch)
                    stats["processed_messages"] += batch_stats["processed"]
                    stats["messages_with_embeddings"] += batch_stats["with_embeddings"]
                    stats["short_messages_no_embedding"] += batch_stats["no_embeddings"]
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
                "sent": is_sent,
                "meta_data": meta
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract message data: {e}")
            return None

    def _process_batch(self, batch: List[Dict]) -> Dict[str, int]:
        """Process a batch of messages with embeddings and database storage"""
        logger.info(f"Processing batch of {len(batch)} messages...")
        
        success_count = 0
        embedding_count = 0
        short_message_count = 0
        
        try:
            with get_session() as session:
                for message_data in batch:
                    try:
                        message_text = message_data["message_text"]
                        
                        # Check message length - skip embedding for very short messages
                        if len(message_text.strip()) <= 5:
                            logger.debug(f"Skipping embedding for short message: '{message_text}'")
                            embedding = None
                            short_message_count += 1
                        else:
                            # Generate embedding for longer messages
                            logger.debug(f"Generating embedding for: {message_text[:50]}...")
                            embedding = self.client.generate_embedding(message_text)
                            embedding_count += 1
                        
                        # Create Message object
                        db_message = Message(
                            source="text",
                            thread_id=message_data["thread_id"],
                            message_text=message_text,
                            timestamp=message_data["timestamp"],
                            sent=message_data["sent"],
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
                logger.info(f"  - {embedding_count} messages with embeddings")
                logger.info(f"  - {short_message_count} short messages (no embedding)")
                
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
        
        return {
            "processed": success_count,
            "with_embeddings": embedding_count,
            "no_embeddings": short_message_count
        }

    
    def _log_final_stats(self, stats: Dict[str, int]):
        """Log comprehensive processing statistics"""
        logger.info("=== TEXT MESSAGE PROCESSING STATISTICS ===")
        logger.info(f"Total lines read: {stats['total_lines']:,}")
        logger.info(f"Valid messages found: {stats['valid_messages']:,}")
        logger.info(f"Participating threads found: {stats['participating_threads']:,}")
        logger.info(f"Filtered by thread (Matt not participating): {stats['filtered_by_thread']:,}")
        logger.info(f"Filtered by date (before 2021-01-01): {stats['filtered_by_date']:,}")
        logger.info(f"Skipped duplicates: {stats['skipped_duplicates']:,}")
        logger.info(f"Successfully processed: {stats['processed_messages']:,}")
        logger.info(f"  - With embeddings: {stats['messages_with_embeddings']:,}")
        logger.info(f"  - Short messages (no embedding): {stats['short_messages_no_embedding']:,}")
        logger.info(f"Total batches: {stats['batch_count']:,}")
        logger.info(f"Errors encountered: {stats['errors']:,}")
        
        if stats["valid_messages"] > 0:
            remaining_after_filters = (stats["valid_messages"] - stats["skipped_duplicates"] - 
                                     stats["filtered_by_date"] - stats["filtered_by_thread"])
            if remaining_after_filters > 0:
                success_rate = (stats["processed_messages"] / remaining_after_filters) * 100
                logger.info(f"Processing success rate: {success_rate:.1f}%")
        
        if stats["processed_messages"] > 0:
            embedding_percentage = (stats["messages_with_embeddings"] / stats["processed_messages"]) * 100
            logger.info(f"Messages with embeddings: {embedding_percentage:.1f}%")
            
            # Estimate API cost savings from short message filtering
            embedding_savings = stats["short_messages_no_embedding"] * 0.00002  # Rough OpenAI embedding cost
            logger.info(f"API cost saved (short messages): ~${embedding_savings:.2f} ({stats['short_messages_no_embedding']:,} avoided calls)")
            
            # Additional savings from thread filtering
            thread_savings = stats["filtered_by_thread"] * 0.00002
            total_savings = embedding_savings + thread_savings
            logger.info(f"API cost saved (thread filtering): ~${thread_savings:.2f} ({stats['filtered_by_thread']:,} avoided calls)")
            logger.info(f"TOTAL API cost savings: ~${total_savings:.2f}")
            
            # Thread filtering efficiency
            if stats["valid_messages"] > 0:
                filter_efficiency = (stats["filtered_by_thread"] / stats["valid_messages"]) * 100
                logger.info(f"Thread filtering efficiency: {filter_efficiency:.1f}% of messages avoided")
        
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