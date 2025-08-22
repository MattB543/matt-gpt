"""
Conversation History Service for Matt-GPT
Handles retrieval and formatting of conversation history across API requests
"""

from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import uuid
import logging
from pydantic import BaseModel

from models import QueryLog

# Configure logging
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Represents a single message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    query_id: uuid.UUID


class ConversationHistoryService:
    """Service for managing conversation history and context"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_conversation_history(self, conversation_id: uuid.UUID) -> List[ChatMessage]:
        """
        Retrieve full conversation history ordered chronologically
        
        Args:
            conversation_id: UUID of the conversation to retrieve
            
        Returns:
            List of ChatMessage objects representing the conversation
        """
        logger.debug(f"Retrieving conversation history for {conversation_id}")
        
        # Query all logs for this conversation, ordered by creation time
        query = (
            select(QueryLog)
            .where(QueryLog.conversation_id == conversation_id)
            .order_by(QueryLog.created_at)
        )
        
        logs = self.session.exec(query).all()
        logger.info(f"Found {len(logs)} query logs for conversation {conversation_id}")
        
        history = []
        for log in logs:
            # Add user message
            history.append(ChatMessage(
                role="user",
                content=log.query_text,
                timestamp=log.created_at,
                query_id=log.id
            ))
            
            # Add assistant response
            history.append(ChatMessage(
                role="assistant", 
                content=log.response_text,
                timestamp=log.created_at,
                query_id=log.id
            ))
        
        logger.debug(f"Formatted {len(history)} messages from {len(logs)} query logs")
        return history
    
    def format_history_for_llm(self, history: List[ChatMessage], max_messages: int = 10) -> str:
        """
        Format conversation history for inclusion in LLM context
        
        Args:
            history: List of ChatMessage objects
            max_messages: Maximum number of recent messages to include
            
        Returns:
            Formatted string suitable for LLM context
        """
        if not history:
            return ""
        
        # Take the most recent messages to stay within context limits
        recent_history = history[-max_messages:] if len(history) > max_messages else history
        
        formatted_messages = []
        for msg in recent_history:
            timestamp_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            formatted_messages.append(f"[{timestamp_str}] {msg.role}: {msg.content}")
        
        context_str = "\n".join(formatted_messages)
        
        logger.debug(f"Formatted {len(recent_history)} messages for LLM context ({len(context_str)} chars)")
        
        return context_str
    
    def conversation_exists(self, conversation_id: uuid.UUID) -> bool:
        """
        Check if a conversation exists in the database
        
        Args:
            conversation_id: UUID to check
            
        Returns:
            True if conversation exists, False otherwise
        """
        query = (
            select(QueryLog.id)
            .where(QueryLog.conversation_id == conversation_id)
            .limit(1)
        )
        
        result = self.session.exec(query).first()
        exists = result is not None
        
        logger.debug(f"Conversation {conversation_id} exists: {exists}")
        return exists
    
    def get_conversation_summary(self, conversation_id: uuid.UUID) -> dict:
        """
        Get summary statistics for a conversation
        
        Args:
            conversation_id: UUID of the conversation
            
        Returns:
            Dictionary with conversation metadata
        """
        query = (
            select(QueryLog)
            .where(QueryLog.conversation_id == conversation_id)
            .order_by(QueryLog.created_at)
        )
        
        logs = self.session.exec(query).all()
        
        if not logs:
            return {
                "exists": False,
                "message_count": 0,
                "first_message_at": None,
                "last_message_at": None,
                "total_tokens": 0
            }
        
        summary = {
            "exists": True,
            "message_count": len(logs),
            "first_message_at": logs[0].created_at,
            "last_message_at": logs[-1].created_at,
            "total_tokens": sum(log.tokens_used for log in logs if log.tokens_used),
            "models_used": list(set(log.model_used for log in logs)),
            "avg_latency_ms": sum(log.latency_ms for log in logs) / len(logs)
        }
        
        logger.debug(f"Conversation {conversation_id} summary: {summary['message_count']} messages")
        return summary