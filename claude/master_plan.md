# Matt-GPT Master Plan

## Executive Summary

### Project Vision
Matt-GPT is a **personal AI avatar system** that authentically represents Matt in digital conversations and decision-making processes. Unlike generic AI assistants, this system creates a highly personalized "digital twin" that captures not just what Matt might say, but _how_ he communicates, his values, decision-making patterns, and unique perspectives.

### Key Objectives
- **Authentic Representation**: Maintain Matt's communication style, humor, and personality across all interactions
- **Scalable Presence**: Enable Matt to participate in multiple conversations/processes simultaneously
- **Context-Aware Intelligence**: Retrieve and utilize relevant historical context for nuanced responses
- **Continuous Improvement**: Learn and adapt based on feedback and new interactions

### Critical Success Metrics
- **Response Authenticity**: >80% similarity to actual Matt responses (measured via embedding similarity)
- **Context Relevance**: Retrieved context matches query intent in >90% of cases
- **System Performance**: <2s response latency, 99.9% uptime
- **User Satisfaction**: Validated through A/B testing with real conversation transcripts

### Core Problems Solved
1. **Time Scarcity**: Matt can't participate in every valuable conversation
2. **Consistency**: Ensuring accurate representation of values across contexts
3. **Information Processing**: Intelligent filtering of high-volume content streams
4. **Scalability**: Supporting multiple simultaneous AI-mediated processes

### Key Assumptions & Constraints
- **Data Quality**: 5000+ text/Slack messages provide sufficient training data
- **Technical Infrastructure**: PostgreSQL with pgvector can handle production load
- **API Costs**: OpenRouter provides cost-effective model access
- **Privacy**: All data remains in controlled environment

## System Architecture

### High-Level Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │  Content APIs   │    │  Admin Tools    │
│  (Web, Mobile)  │    │  (Twitter, etc) │    │  (Monitoring)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     FastAPI Gateway     │
                    │   (Authentication &     │
                    │    Request Routing)     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │      Matt-GPT Core      │
                    │    (DSPy + RAG)         │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────┴───────┐    ┌─────────┴───────┐    ┌─────────┴───────┐
│   PostgreSQL    │    │   OpenRouter    │    │   Monitoring    │
│  (Data + Vector │    │   (LLM API)     │    │   & Logging     │
│   Embeddings)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow Architecture

1. **Query Processing Pipeline**
   - Input sanitization and validation
   - Query embedding generation
   - Context retrieval from vector database
   - Response generation via DSPy-optimized prompts
   - Response post-processing and logging

2. **Context Retrieval Strategy**
   - **Message Context**: Retrieve conversation threads (±10 messages around matches)
   - **Personality Context**: Pull relevant personality documents
   - **Temporal Context**: Weight recent interactions more heavily
   - **Semantic Similarity**: Use cosine similarity with HNSW indexing

### Technology Stack Justification

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Database** | PostgreSQL + pgvector | Single database for relational + vector data, mature ecosystem |
| **Vector Search** | HNSW indexing | Superior performance over IVFFlat for similarity search |
| **Web Framework** | FastAPI | Async support, automatic OpenAPI docs, type safety |
| **AI Framework** | DSPy | Systematic prompt optimization vs manual prompt engineering |
| **LLM Provider** | OpenRouter | Model flexibility, cost optimization, no vendor lock-in |
| **Embeddings** | OpenAI text-embedding-3-small | Best price/performance ratio, 1536 dimensions |

### Integration Points & APIs

- **External APIs**: OpenRouter, OpenAI Embeddings, Twitter API (future)
- **Internal APIs**: RESTful endpoints for chat, admin functions, health checks
- **Database Interfaces**: SQLModel for type-safe ORM, direct SQL for complex vector queries
- **Monitoring Interfaces**: Structured logging, query metrics, performance telemetry

## The Three Primary Use Cases

#### 1. **AI-Assisted Negotiation/Decision-Making/Mediation**

- **Scenario**: Imagine a future where AI mediates complex multi-party negotiations or helps groups reach consensus
- **Matt-GPT's Role**: Represents Matt's interests, values, and negotiation style without him being present
- **Example**: A team is using an AI tool to decide on project priorities. Matt-GPT can advocate for his preferences (like preferring iterative development over waterfall) based on his documented work style
- **Real Test Case**: Matt already has transcripts from an AI-assisted consensus-building exercise he participated in - perfect for validating if Matt-GPT would respond similarly

#### 2. **Agent-Based Simulations and Debates**

- **Scenario**: Running "what-if" scenarios or exploring ideas through simulated conversations
- **Matt-GPT's Role**: Engage in debates or discussions as Matt would, surfacing his unique perspectives
- **Example**:
  - Test how Matt might react to different business proposals
  - Simulate conversations between Matt-GPT and other people's AI agents to identify areas of alignment or conflict before real meetings
  - Run 100 different conversation paths to find the most productive discussion points

#### 3. **Intelligent Content Filtering (Recommender System)**

- **Scenario**: The Twitter feed problem - too much content, not enough time
- **Matt-GPT's Role**: Acts as a personalized filter that truly understands Matt's interests
- **Example**:
  - Scan through Matt's Twitter timeline
  - Like/retweet only the content Matt would genuinely find valuable
  - Surface the "best of" based on deep understanding of his interests, not just keyword matching

### **What Makes This Different**

This isn't just another chatbot. Here's what makes Matt-GPT unique:

#### **1. Deep Personalization Through Actual History**

- **5,000+ real text messages**: Captures Matt's casual communication style, humor, abbreviations
- **5,000+ Slack messages**: Shows professional communication, technical discussions, team dynamics
- **Personality assessments**: Formal documentation of values, work styles, political views, etc.

#### **2. Context-Aware Responses**

Traditional chatbots might match keywords. Matt-GPT understands context:

- If asked about politics, it doesn't just find messages with "politics"
- It retrieves entire conversation threads (10 messages before/after) to understand the nuance
- It combines this with Matt's formal political philosophy document

#### **3. Authentic Voice Preservation**

- Not trying to be perfect or formal
- Maintains Matt's actual writing style, including:
  - His typical response length
  - Use of specific phrases or expressions
  - Technical vs casual tone switching

### **The Technical Innovation**

#### **Why This Architecture?**

1. **RAG (Retrieval-Augmented Generation)**: Instead of fine-tuning an LLM (expensive, static), Matt-GPT dynamically retrieves relevant context for each query

2. **DSPy Optimization**: Rather than manually crafting prompts, the system learns optimal prompts through evaluation against real Matt responses

3. **PostgreSQL + pgvector**: Keeps everything in one database - no need for separate vector databases, maintaining simplicity

4. **OpenRouter Flexibility**: Can switch between models (GPT-4, Claude, etc.) without code changes, optimizing for cost/quality

---

## Implementation Phases

### Phase 0: Foundation & Planning (4-6 hours)
**Timeline**: Week 1
**Dependencies**: None
**Critical Path**: Yes

#### Deliverables
- [ ] Environment setup and dependency management
- [ ] Database schema design and validation  
- [ ] Development workflow establishment
- [ ] Data audit and preparation strategy

#### Success Criteria
- All dependencies installed and tested
- Database connects and basic queries work
- Sample data processing pipeline validated
- Development environment reproducible

#### Risk Mitigation
- **Risk**: Dependency conflicts between DSPy and other packages
- **Mitigation**: Use Poetry for isolated dependency management
- **Risk**: PostgreSQL pgvector compatibility issues
- **Mitigation**: Test with Docker container first, validate version compatibility

### Phase 1: Core Infrastructure (6-8 hours)
**Timeline**: Week 1-2
**Dependencies**: Phase 0
**Critical Path**: Yes

#### Deliverables
- [ ] PostgreSQL database with pgvector extension
- [ ] Connection pooling and session management
- [ ] Database models and migrations
- [ ] OpenRouter integration client
- [ ] Basic FastAPI application structure

#### Success Criteria
- Database performs vector similarity searches <100ms
- API responds to health checks
- OpenRouter client successfully makes test calls
- All database tables created with proper indexes

#### Risk Mitigation
- **Risk**: Vector search performance issues
- **Mitigation**: Implement HNSW indexing, test with sample data
- **Risk**: OpenRouter API limits or failures  
- **Mitigation**: Implement retry logic, fallback to direct OpenAI

#### Implementation Details

##### 1.1 PostgreSQL with pgvector v0.8.0

```bash
# Option A: Docker (for local dev)
docker run -d \
  --name matt-gpt-db \
  -e POSTGRES_USER=matt \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=matt_gpt \
  -p 5432:5432 \
  pgvector/pgvector:pg17

# Option B: DigitalOcean Managed Database
# Use their UI to create PostgreSQL 17 with pgvector extension
```

**Best Practice Notes:**

- pgvector v0.8.0 is the latest stable version
- Use HNSW indexes for better performance over IVFFlat for similarity search
- Set appropriate list sizes (rows/1000) for optimal performance

#### 1.2 Python Environment Setup

```bash
# Use Poetry for dependency management (2025 best practice)
pip install poetry
poetry new matt-gpt
cd matt-gpt

# Core dependencies
poetry add fastapi uvicorn[standard]
poetry add pgvector psycopg[binary,pool]
poetry add sqlmodel  # Better than raw SQLAlchemy for FastAPI
poetry add openai    # For OpenRouter compatibility
poetry add dspy-ai
poetry add python-dotenv
poetry add pydantic-settings
poetry add python-multipart  # For file uploads
poetry add httpx  # For async HTTP
```

#### 1.3 Environment Configuration

```python
# .env file
POSTGRES_URL=postgresql://matt:password@localhost:5432/matt_gpt
OPENROUTER_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # For embeddings
LOG_LEVEL=INFO
```

### Phase 2: RAG System & DSPy Integration (8-10 hours)
**Timeline**: Week 2-3
**Dependencies**: Phase 1
**Critical Path**: Yes

#### Deliverables
- [ ] Custom PostgreSQL vector retriever for DSPy
- [ ] Message context retrieval with thread awareness
- [ ] Personality document integration
- [ ] DSPy program structure with optimization hooks
- [ ] Basic chat endpoint with context logging

#### Success Criteria
- Retriever returns relevant context within 500ms
- DSPy program generates coherent responses
- Context relevance validated with sample queries
- System handles concurrent requests

#### Risk Mitigation
- **Risk**: Poor context retrieval relevance
- **Mitigation**: A/B test different retrieval strategies, tune similarity thresholds
- **Risk**: DSPy optimization takes too long
- **Mitigation**: Start with basic CoT, optimize incrementally

### Phase 3: Data Processing & Optimization (6-8 hours)
**Timeline**: Week 3-4
**Dependencies**: Phase 2
**Critical Path**: No

#### Deliverables
- [ ] Bulk message processing pipeline
- [ ] Embedding generation for all historical data
- [ ] DSPy optimization with validation dataset
- [ ] Performance benchmarking and tuning

#### Success Criteria
- All 10k+ messages processed and embedded
- Optimized model shows >80% similarity to ground truth
- System handles expected production load
- Response quality meets acceptance criteria

### Phase 4: Production Hardening (4-6 hours)
**Timeline**: Week 4
**Dependencies**: Phase 3
**Critical Path**: Yes

#### Deliverables
- [ ] Comprehensive error handling and logging
- [ ] Rate limiting and authentication
- [ ] Health checks and monitoring
- [ ] Docker containerization
- [ ] Deployment automation

#### Success Criteria
- System recovers gracefully from failures
- All interactions logged for analysis
- Monitoring alerts on performance degradation
- One-command deployment process

## Component Specifications

### Core Components

#### 1. PostgreSQL Vector Retriever
**Purpose**: Custom DSPy retriever for context-aware message and personality document retrieval

**Interface**:
```python
class PostgreSQLVectorRetriever(dspy.Retrieve):
    def forward(query: str) -> dspy.Prediction[passages: List[str]]
```

**Key Features**:
- HNSW vector indexing for <100ms similarity search
- Thread-aware context retrieval (±10 messages around matches)
- Weighted combination of message history and personality documents
- Configurable similarity thresholds and result limits

**State Management**: Stateless with connection pooling

#### 2. Matt-GPT DSPy Module
**Purpose**: Main conversation engine combining retrieval and generation

**Interface**:
```python
class MattGPT(dspy.Module):
    def forward(question: str) -> dspy.Prediction[response: str, context_used: List[str]]
```

**Key Features**:
- Chain-of-thought reasoning with context integration
- Optimizable prompt structure via DSPy compilation
- Context windowing to manage token limits
- Response style consistency enforcement

**State Management**: Stateless computation with cached model connections

#### 3. FastAPI Gateway
**Purpose**: HTTP API layer with authentication, rate limiting, and logging

**Interface**:
- `POST /chat`: Main conversation endpoint
- `GET /health`: System health and readiness checks
- `POST /admin/optimize`: Trigger DSPy recompilation
- `GET /admin/metrics`: Performance and usage statistics

**Key Features**:
- JWT-based authentication
- Request/response logging to QueryLog table
- Background task processing for non-blocking operations
- CORS and security header management

**State Management**: Application state for DSPy model, database connections via dependency injection

### Data Models

#### Message Schema
```python
class Message(SQLModel, table=True):
    id: UUID (Primary Key)
    source: str (Index: 'slack', 'text', 'personality')
    thread_id: Optional[str] (Index: Groups related messages)
    message_text: str (Core content)
    timestamp: datetime (Index: Temporal relevance)
    embedding: List[float] (Vector: 1536 dimensions)
    meta_data: dict (JSON: Source-specific data)
```

#### QueryLog Schema
```python
class QueryLog(SQLModel, table=True):
    id: UUID (Primary Key)
    query_text: str (Input query)
    response_text: str (Generated response)
    model_used: str (OpenRouter model identifier)
    context_used: dict (JSON: Retrieved passages)
    tokens_used: int (For cost tracking)
    latency_ms: float (Performance monitoring)
    created_at: datetime (Index: Time series analysis)
```

### Security & Compliance

#### Authentication Strategy
- API key-based authentication for programmatic access
- Rate limiting: 100 requests/minute per key
- IP-based blocking for abuse prevention

#### Data Privacy
- All personal data encrypted at rest
- No data sharing with external services beyond OpenRouter/OpenAI
- Audit logging for all data access

#### Compliance Considerations
- GDPR: Right to deletion implemented via cascade deletes
- Data retention: Configurable TTL for query logs
- Access controls: Admin vs user permission levels

### Performance Specifications

#### Latency Targets
- Vector similarity search: <100ms (95th percentile)
- End-to-end response: <2s (95th percentile)
- Database connection establishment: <50ms

#### Throughput Targets  
- Concurrent requests: 50 requests/second
- Message processing: 1000 messages/minute during bulk import
- Embedding generation: 100 texts/minute

#### Scalability Considerations
- Horizontal scaling via multiple FastAPI instances
- Database connection pooling (20 connections per instance)
- Vector index performance degrades gracefully with data size

## Quality & Testing Strategy

### Testing Framework
- **Unit Testing**: pytest with async support for individual components
- **Integration Testing**: End-to-end API and database validation  
- **Performance Testing**: Load testing with realistic query patterns
- **Security Testing**: Authentication, input validation, vulnerability scanning

### Performance Benchmarks
- **Response Latency**: <2s end-to-end (95th percentile)
- **Vector Search**: <100ms similarity queries
- **Context Accuracy**: >85% relevance on validation dataset
- **Response Authenticity**: >80% similarity to actual Matt responses

### Security Audit Points
- [ ] Database encryption and access controls
- [ ] API authentication and rate limiting
- [ ] Input sanitization and validation
- [ ] Personal data protection compliance

### Monitoring & Observability
- **Metrics**: Request rates, latency, error rates, token usage
- **Logging**: Structured JSON logs with query/response tracking
- **Alerting**: Performance degradation and system failures
- **Health Checks**: Database, API connectivity, resource usage

## Deployment & Operations

### Deployment Strategy

#### Environment Configuration
```yaml
# Production Environment
- Database: Managed PostgreSQL with pgvector
- Compute: Containerized FastAPI on cloud platform  
- Load Balancer: HTTPS termination with rate limiting
- Monitoring: Centralized logging and metrics collection
```

#### Container Strategy
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry export -f requirements.txt --output requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Deployment Environments
- **Development**: Local Docker with sample data
- **Staging**: Cloud deployment with production-like data
- **Production**: Fully managed with backup and monitoring

### Rollback Procedures

#### Automated Rollback Triggers
- Health check failures for >5 minutes
- Error rate exceeding 10% of requests
- Response latency degradation >3x baseline

#### Manual Rollback Process
1. **Immediate**: Revert to previous container image
2. **Database**: Restore from point-in-time backup if needed
3. **Verification**: Confirm system health and performance
4. **Communication**: Update stakeholders on incident status

### Maintenance & Update Processes

#### Regular Maintenance Tasks
- **Weekly**: Performance review and optimization tuning
- **Monthly**: Security patches and dependency updates
- **Quarterly**: Full system backup testing and disaster recovery validation

#### Update Procedures
1. **Development**: Feature development and testing
2. **Staging**: Integration testing with production data
3. **Blue/Green Deploy**: Zero-downtime production updates
4. **Monitoring**: Post-deployment validation and rollback if needed

#### Data Management
- **Backup Strategy**: Automated daily backups with 30-day retention
- **Data Retention**: Query logs purged after 90 days
- **Privacy Compliance**: GDPR deletion procedures implemented

### Documentation Requirements

#### Technical Documentation
- [ ] API documentation (auto-generated OpenAPI)
- [ ] Database schema and migration procedures
- [ ] Deployment and operations runbook
- [ ] Security and compliance procedures

#### User Documentation  
- [ ] API usage examples and best practices
- [ ] Authentication and rate limiting guidelines
- [ ] Response format and error handling
- [ ] Integration patterns and SDKs

#### Operational Documentation
- [ ] Monitoring and alerting setup
- [ ] Incident response procedures
- [ ] Performance tuning guidelines
- [ ] Backup and recovery procedures

### Risk Mitigation & Validation

#### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|---------|-------------|------------|
| Vector search performance degradation | High | Medium | HNSW indexing, query optimization |
| DSPy optimization fails to improve responses | High | Low | Baseline fallback, manual prompt tuning |
| OpenRouter API rate limits/costs | Medium | Medium | Multi-provider setup, usage monitoring |
| Database scaling limitations | Medium | Low | Connection pooling, read replicas |

#### Business Risks  
| Risk | Impact | Probability | Mitigation |
|------|---------|-------------|------------|
| Response quality below expectations | High | Medium | Validation dataset, A/B testing |
| Privacy/security compliance issues | High | Low | Security audit, compliance review |
| Cost overruns from API usage | Medium | Medium | Usage monitoring, budget alerts |
| Data loss or corruption | High | Low | Automated backups, disaster recovery |

### Validation Checklist

#### Pre-Launch Validation
- [ ] All user requirements addressed and tested
- [ ] Technical feasibility validated with prototypes
- [ ] Dependencies mapped and contingencies planned
- [ ] Risk mitigation strategies implemented and tested
- [ ] System architecture supports planned scalability
- [ ] Success criteria defined and measurable
- [ ] Timeline realistic with appropriate buffers
- [ ] Stakeholder concerns addressed and documented

#### Post-Launch Validation
- [ ] Performance metrics meet defined targets
- [ ] User feedback indicates successful Matt representation
- [ ] System operates reliably under expected load
- [ ] Cost projections align with actual usage
- [ ] Security posture validated through testing
- [ ] Documentation complete and accessible
- [ ] Team trained on operations and maintenance
- [ ] Continuous improvement process established

### Original Technical Implementation

#### Database Schema with Logging

#### 2.1 Enhanced Database Schema with Query Logging

```python
# models.py
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
    embedding: Optional[list[float]] = Field(
        sa_column=Column(Vector(1536))  # OpenAI text-embedding-3-small
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
        sa_column=Column(Vector(1536))
    )
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QueryLog(SQLModel, table=True):
    """Track all queries and responses for analysis"""
    __tablename__ = "query_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    query_text: str
    response_text: str
    model_used: str
    context_used: dict = Field(sa_column=Column(JSON))  # Store RAG results
    tokens_used: int
    latency_ms: float
    ip_address: Optional[str]
    user_agent: Optional[str]
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### 2.2 Database Connection Pool

```python
# database.py
from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.pool import NullPool
import os
from contextlib import contextmanager

# Best practice: Use connection pooling
engine = create_engine(
    os.getenv("POSTGRES_URL"),
    pool_pre_ping=True,  # Verify connections before using
    pool_size=20,
    max_overflow=0
)

def init_db():
    """Initialize database with pgvector extension"""
    with engine.connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    """Context manager for database sessions"""
    with Session(engine) as session:
        yield session
```

### **Phase 3: OpenRouter Integration (1 hour)**

#### 3.1 OpenRouter Client Setup

```python
# llm_client.py
from openai import OpenAI
import os
from typing import Optional

class OpenRouterClient:
    """Wrapper for OpenRouter API using OpenAI SDK"""

    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                "HTTP-Referer": "https://matt-gpt.app",
                "X-Title": "Matt-GPT",
            }
        )

    def chat_completion(
        self,
        messages: list,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        """Get chat completion from OpenRouter"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings using OpenAI directly"""
        # Use OpenAI client for embeddings (more reliable)
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=1536
        )
        return response.data[0].embedding
```

### **Phase 4: Custom DSPy RAG Implementation (3-4 hours)**

#### 4.1 PostgreSQL Vector Retriever for DSPy

```python
# retrievers.py
import dspy
from typing import List, Dict, Any
import numpy as np
from pgvector.psycopg import register_vector
import psycopg
from datetime import datetime, timedelta

class PostgreSQLVectorRetriever(dspy.Retrieve):
    """Custom retriever using PostgreSQL with pgvector"""

    def __init__(self, connection_string: str, k: int = 20):
        super().__init__(k=k)
        self.conn_string = connection_string
        self.k = k

    def forward(self, query: str, **kwargs) -> dspy.Prediction:
        """Retrieve relevant passages from PostgreSQL"""

        # Generate query embedding
        from llm_client import OpenRouterClient
        client = OpenRouterClient()
        query_embedding = client.generate_embedding(query)

        results = []

        with psycopg.connect(self.conn_string) as conn:
            register_vector(conn)

            # 1. Find relevant messages with context
            messages = self._retrieve_messages_with_context(
                conn, query_embedding, limit=10, context_window=10
            )
            results.extend(messages)

            # 2. Find relevant personality docs
            docs = self._retrieve_personality_docs(
                conn, query_embedding, limit=5
            )
            results.extend(docs)

        return dspy.Prediction(passages=results)

    def _retrieve_messages_with_context(
        self, conn, embedding: list, limit: int = 10, context_window: int = 10
    ) -> List[str]:
        """Retrieve messages with surrounding context"""

        # Use HNSW index with cosine similarity (best practice for normalized vectors)
        query = """
        WITH relevant_messages AS (
            SELECT
                id, thread_id, message_text, timestamp,
                (embedding <=> %s::vector) as distance
            FROM messages
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        )
        SELECT DISTINCT m.message_text, m.timestamp
        FROM messages m
        INNER JOIN relevant_messages rm ON m.thread_id = rm.thread_id
        WHERE m.timestamp BETWEEN rm.timestamp - interval '%s minutes'
              AND rm.timestamp + interval '%s minutes'
        ORDER BY m.timestamp;
        """

        with conn.cursor() as cur:
            cur.execute(query, (embedding, embedding, limit,
                              context_window, context_window))
            results = cur.fetchall()

        # Format as conversational context
        formatted = []
        for text, timestamp in results:
            formatted.append(f"[{timestamp}] {text}")

        return formatted

    def _retrieve_personality_docs(
        self, conn, embedding: list, limit: int = 5
    ) -> List[str]:
        """Retrieve relevant personality documents"""

        query = """
        SELECT title, content
        FROM personality_docs
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """

        with conn.cursor() as cur:
            cur.execute(query, (embedding, limit))
            results = cur.fetchall()

        formatted = []
        for title, content in results:
            formatted.append(f"=== {title} ===\n{content}")

        return formatted
```

#### 4.2 DSPy Program with Optimization

```python
# matt_gpt.py
import dspy
from typing import List
import os

class MattResponse(dspy.Signature):
    """Generate a response as Matt would, based on his history and personality."""

    context = dspy.InputField(
        desc="Matt's relevant messages and personality information"
    )
    question = dspy.InputField(
        desc="The query or prompt to respond to"
    )
    response = dspy.OutputField(
        desc="Response in Matt's authentic voice and style"
    )

class MattGPT(dspy.Module):
    def __init__(self, retriever):
        super().__init__()
        self.retrieve = retriever
        self.generate = dspy.ChainOfThought(MattResponse)

    def forward(self, question: str):
        # Retrieve relevant context
        context = self.retrieve(question).passages

        # Format context for generation
        context_str = "\n\n".join(context[:50])  # Limit context size

        # Generate response
        prediction = self.generate(
            context=context_str,
            question=question
        )

        return dspy.Prediction(
            response=prediction.response,
            context_used=context
        )

# Configure DSPy with OpenRouter
def setup_dspy():
    """Configure DSPy to use OpenRouter"""

    # Use OpenRouter through DSPy's OpenAI compatibility
    lm = dspy.OpenAI(
        model="anthropic/claude-3.5-sonnet",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=1000
    )

    # Configure retriever
    retriever = PostgreSQLVectorRetriever(
        connection_string=os.getenv("POSTGRES_URL"),
        k=20
    )

    dspy.settings.configure(lm=lm, rm=retriever)

    return MattGPT(retriever)
```

### **Phase 5: FastAPI Service with Logging (2-3 hours)**

#### 5.1 FastAPI Application with Best Practices

```python
# main.py
from fastapi import FastAPI, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import time
import uuid
from datetime import datetime

from database import init_db, get_session
from models import QueryLog
from matt_gpt import setup_dspy

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    app.state.matt_gpt = setup_dspy()
    yield
    # Shutdown
    # Cleanup if needed

app = FastAPI(
    title="Matt-GPT API",
    version="1.0.0",
    lifespan=lifespan
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = {}
    model: Optional[str] = "anthropic/claude-3.5-sonnet"

class ChatResponse(BaseModel):
    response: str
    query_id: str
    tokens_used: Optional[int] = None
    latency_ms: float
    context_items_used: int

# Dependency for getting client info
def get_client_info(request: Request):
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    }

# Background task for logging
async def log_query(
    query_id: str,
    query_text: str,
    response_text: str,
    model: str,
    context_used: dict,
    latency_ms: float,
    client_info: dict
):
    """Log query asynchronously to not block response"""
    with get_session() as session:
        log_entry = QueryLog(
            id=query_id,
            query_text=query_text,
            response_text=response_text,
            model_used=model,
            context_used=context_used,
            tokens_used=len(response_text.split()),  # Rough estimate
            latency_ms=latency_ms,
            ip_address=client_info.get("ip"),
            user_agent=client_info.get("user_agent"),
            meta_data={"version": "1.0.0"}
        )
        session.add(log_entry)
        session.commit()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    client_info: dict = Depends(get_client_info)
):
    """Main chat endpoint"""

    start_time = time.time()
    query_id = str(uuid.uuid4())

    # Get Matt-GPT response
    result = app.state.matt_gpt(request.message)

    latency_ms = (time.time() - start_time) * 1000

    # Schedule background logging
    background_tasks.add_task(
        log_query,
        query_id=query_id,
        query_text=request.message,
        response_text=result.response,
        model=request.model,
        context_used={"passages": result.context_used[:10]},  # Sample
        latency_ms=latency_ms,
        client_info=client_info
    )

    return ChatResponse(
        response=result.response,
        query_id=query_id,
        latency_ms=latency_ms,
        context_items_used=len(result.context_used)
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

### **Phase 6: Data Processing Scripts (2 hours)**

#### 6.1 Message Processing Pipeline

```python
# process_data.py
import json
import csv
from typing import List, Dict
from datetime import datetime
from database import get_session
from models import Message, PersonalityDoc
from llm_client import OpenRouterClient
import asyncio
from tqdm import tqdm

class DataProcessor:
    def __init__(self):
        self.client = OpenRouterClient()

    async def process_messages_batch(self, messages: List[Dict], source: str):
        """Process messages in batches for efficiency"""

        batch_size = 100

        with get_session() as session:
            for i in tqdm(range(0, len(messages), batch_size)):
                batch = messages[i:i+batch_size]

                # Generate embeddings for batch
                embeddings = []
                for msg in batch:
                    embedding = self.client.generate_embedding(msg['text'])
                    embeddings.append(embedding)

                # Insert batch into database
                for msg, embedding in zip(batch, embeddings):
                    db_message = Message(
                        source=source,
                        thread_id=msg.get('thread_id'),
                        message_text=msg['text'],
                        timestamp=msg['timestamp'],
                        embedding=embedding,
                        meta_data=msg.get('metadata', {})
                    )
                    session.add(db_message)

                session.commit()

    def process_slack_export(self, file_path: str):
        """Process Slack JSON export"""
        with open(file_path, 'r') as f:
            data = json.load(f)

        messages = []
        for channel in data:
            for msg in channel.get('messages', []):
                if msg.get('type') == 'message' and msg.get('text'):
                    messages.append({
                        'text': msg['text'],
                        'timestamp': datetime.fromtimestamp(float(msg['ts'])),
                        'thread_id': channel['name'],
                        'metadata': {'user': msg.get('user')}
                    })

        asyncio.run(self.process_messages_batch(messages, 'slack'))

    def process_personality_docs(self, docs_folder: str):
        """Process personality documents"""
        import os
        import markdown

        with get_session() as session:
            for filename in os.listdir(docs_folder):
                if filename.endswith('.md'):
                    with open(os.path.join(docs_folder, filename), 'r') as f:
                        content = f.read()

                    # Generate embedding
                    embedding = self.client.generate_embedding(content)

                    doc = PersonalityDoc(
                        doc_type=filename.replace('.md', ''),
                        title=filename,
                        content=content,
                        embedding=embedding
                    )
                    session.add(doc)

            session.commit()
```

### **Phase 7: DSPy Optimization & Evaluation (1-2 hours)**

#### 7.1 Optimization with Test Data

```python
# optimize.py
import dspy
from dspy.teleprompt import BootstrapFewShotWithRandomSearch
from typing import List
import json

def load_test_data(file_path: str):
    """Load consensus-building transcript for evaluation"""
    with open(file_path, 'r') as f:
        data = json.load(f)

    examples = []
    for item in data:
        examples.append(
            dspy.Example(
                question=item['question'],
                response=item['matt_response']
            ).with_inputs('question')
        )

    return examples

def similarity_metric(example, pred, trace=None):
    """Evaluate similarity between predicted and actual response"""

    # Simple semantic similarity using embeddings
    from llm_client import OpenRouterClient
    client = OpenRouterClient()

    actual_embedding = client.generate_embedding(example.response)
    pred_embedding = client.generate_embedding(pred.response)

    # Cosine similarity
    import numpy as np
    similarity = np.dot(actual_embedding, pred_embedding) / (
        np.linalg.norm(actual_embedding) * np.linalg.norm(pred_embedding)
    )

    return similarity > 0.8  # Threshold for success

def optimize_matt_gpt():
    """Optimize Matt-GPT using DSPy"""

    # Load data
    examples = load_test_data('consensus_transcript.json')
    trainset = examples[:20]
    devset = examples[20:40]

    # Setup Matt-GPT
    from matt_gpt import setup_dspy
    matt_gpt = setup_dspy()

    # Optimize
    optimizer = BootstrapFewShotWithRandomSearch(
        metric=similarity_metric,
        max_bootstrapped_demos=4,
        num_candidate_programs=10,
        num_threads=4
    )

    compiled_matt_gpt = optimizer.compile(
        matt_gpt,
        trainset=trainset,
        valset=devset
    )

    # Save optimized program
    compiled_matt_gpt.save('matt_gpt_optimized.json')

    return compiled_matt_gpt
```

### **Phase 8: Production Deployment (1 hour)**

#### 8.1 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY . .

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 8.2 Production Runner Script

```python
# run.py
import uvicorn
from main import app
import logging
from logging.handlers import RotatingFileHandler
import json

# Configure JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage()
        }
        return json.dumps(log_obj)

# Setup rotating file handler
handler = RotatingFileHandler(
    "matt_gpt.log",
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
handler.setFormatter(JSONFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()]
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
        }
    )
```
