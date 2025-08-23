#!/usr/bin/env python3
"""Process personality documents from inputs/ folder and store in database with summary embeddings."""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to Python path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from database import get_session
from models import PersonalityDoc
from llm_client import OpenRouterClient
from sqlmodel import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_personality_inputs(overwrite_existing: bool = False):
    """Process all markdown files from inputs/ folder"""
    
    inputs_folder = Path("inputs")
    if not inputs_folder.exists():
        raise FileNotFoundError(f"Inputs folder not found: {inputs_folder}")
    
    # Get list of markdown files
    md_files = list(inputs_folder.glob("*.md"))
    if not md_files:
        logger.warning("No markdown files found in inputs/ folder")
        return
    
    logger.info(f"Found {len(md_files)} markdown files to process")
    
    # Initialize OpenRouter client
    try:
        client = OpenRouterClient()
        logger.info("OpenRouter client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenRouter client: {e}")
        raise
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    with get_session() as session:
        for md_file in md_files:
            logger.info(f"\nProcessing: {md_file.name}")
            
            # Generate doc_type from filename
            doc_type = md_file.stem.lower().replace(' ', '_').replace('&', 'and')
            
            # Check if already processed (unless overwrite is requested)
            if not overwrite_existing:
                existing = session.exec(select(PersonalityDoc).where(PersonalityDoc.doc_type == doc_type)).first()
                if existing:
                    logger.info(f"  Document already exists (doc_type: {doc_type}), skipping...")
                    skipped_count += 1
                    continue
            
            try:
                # Read the markdown content
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    logger.warning(f"  File is empty, skipping...")
                    error_count += 1
                    continue
                
                logger.info(f"  Content length: {len(content)} characters")
                
                # Generate AI summary with tags
                logger.info(f"  Generating summary with tags...")
                summary = generate_summary_with_tags(client, content, md_file.stem)
                
                if not summary:
                    logger.error(f"  Failed to generate summary, skipping...")
                    error_count += 1
                    continue
                
                logger.info(f"  Summary length: {len(summary)} characters")
                
                # Generate embedding of the summary (not the full content)
                logger.info(f"  Generating embedding for summary...")
                summary_embedding = client.generate_embedding(summary)
                
                if not summary_embedding:
                    logger.error(f"  Failed to generate embedding, skipping...")
                    error_count += 1
                    continue
                
                logger.info(f"  Generated embedding with {len(summary_embedding)} dimensions")
                
                # If overwriting, delete existing document first
                if overwrite_existing:
                    existing = session.exec(select(PersonalityDoc).where(PersonalityDoc.doc_type == doc_type)).first()
                    if existing:
                        session.delete(existing)
                        logger.info(f"  Deleted existing document")
                
                # Store in database
                doc = PersonalityDoc(
                    doc_type=doc_type,
                    title=md_file.stem,
                    content=content,  # Full markdown
                    summary=summary,  # Tags and brief description
                    embedding=summary_embedding,  # Embedding of summary, not content
                    meta_data={
                        "source": "inputs_folder", 
                        "processed_date": str(datetime.utcnow()),
                        "file_name": md_file.name,
                        "content_length": len(content),
                        "summary_length": len(summary)
                    }
                )
                
                session.add(doc)
                logger.info(f"  Added to database (doc_type: {doc_type})")
                processed_count += 1
                
            except Exception as e:
                logger.error(f"  Error processing {md_file.name}: {e}")
                error_count += 1
                continue
        
        # Commit all changes
        try:
            session.commit()
            logger.info(f"\nSuccessfully committed all changes to database!")
            logger.info(f"Summary: {processed_count} processed, {skipped_count} skipped, {error_count} errors")
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            session.rollback()
            raise


def generate_summary_with_tags(client, content: str, title: str) -> str:
    """Generate a summary focused on searchable tags and keywords"""
    
    # Truncate content if too long (to avoid token limits)
    max_content_length = 8000  # Conservative limit
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n[Content truncated for summary generation...]"
    
    prompt = f"""Please create a focused summary for this personality document about Matt. The summary will be used for semantic search to determine when this document is relevant to a query.

The summary should include:
1. 8-12 specific tags/keywords that capture the main themes and concepts
2. 2-3 sentences describing what this document covers
3. Key situations or questions this document would help answer

Be specific and use terms that someone might actually search for.

Title: {title}

Content:
{content}

Please format your response as:
TAGS: tag1, tag2, tag3, tag4, tag5, etc.
DESCRIPTION: Brief 2-3 sentence description
RELEVANT FOR: Situations/questions this would help answer"""

    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="anthropic/claude-sonnet-4",
            temperature=0.3  # Lower temperature for more focused summaries
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return None


def check_existing_docs():
    """Check what personality documents already exist in the database"""
    logger.info("Checking existing personality documents...")
    
    with get_session() as session:
        docs = session.exec(select(PersonalityDoc)).all()
        
        if not docs:
            logger.info("No personality documents found in database")
            return
        
        logger.info(f"Found {len(docs)} existing personality documents:")
        for doc in docs:
            logger.info(f"  - {doc.doc_type} ({doc.title}) - {len(doc.content)} chars")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process personality documents from inputs/ folder")
    parser.add_argument("--overwrite", action="store_true", 
                       help="Overwrite existing documents in database")
    parser.add_argument("--check", action="store_true",
                       help="Check existing documents without processing")
    
    args = parser.parse_args()
    
    if args.check:
        check_existing_docs()
    else:
        logger.info("Starting personality document processing...")
        try:
            process_personality_inputs(overwrite_existing=args.overwrite)
            logger.info("Processing completed successfully!")
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            sys.exit(1)