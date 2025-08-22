from sqlmodel import Field, SQLModel, Column, JSON
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import Optional
import uuid


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source: str = Field(index=True)  # 'slack' or 'text'
    thread_id: Optional[str] = Field(index=True)
    message_text: str
    timestamp: datetime = Field(index=True)
    sent: bool = Field(index=True)  # True if Matt sent it, False if received
    embedding: Optional[list[float]] = Field(
        default=None, sa_column=Column(Vector(1536))  # OpenAI text-embedding-3-small
    )
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PersonalityDoc(SQLModel, table=True):
    __tablename__ = "personality_docs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doc_type: str = Field(index=True)
    title: str
    content: str
    summary: Optional[str]
    embedding: Optional[list[float]] = Field(
        default=None, sa_column=Column(Vector(1536))
    )
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QueryLog(SQLModel, table=True):
    """Track all queries and responses for analysis"""
    __tablename__ = "query_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(index=True)  # NEW: Track conversation continuity
    query_text: str
    response_text: str
    model_used: str
    context_used: dict = Field(sa_column=Column(JSON))  # Store RAG results
    tokens_used: int
    latency_ms: float
    ip_address: Optional[str]
    user_agent: Optional[str]
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)