# Chat History Implementation Plan

## Executive Summary

Implement conversation continuity by tracking chat history across API requests. Each conversation gets a unique ID that clients can reference to maintain context across multiple exchanges.

## Problem Statement

Currently, each API request to Matt-GPT is stateless. Users cannot build ongoing conversations or reference previous exchanges. This limits the system's ability to:
- Maintain context across multi-turn conversations
- Reference previous topics or decisions
- Provide coherent long-form discussions
- Build rapport over time

## Solution Overview

Add conversation tracking to the existing query_logs system by:
1. Introducing a `conversation_id` concept
2. Modifying API requests/responses to handle conversation continuity
3. Building conversation history into LLM context
4. Returning conversation history to clients

## Technical Design

### 1. Database Schema Changes

#### Add conversation_id to query_logs table
```sql
ALTER TABLE query_logs ADD COLUMN conversation_id UUID;
CREATE INDEX idx_query_logs_conversation_id ON query_logs(conversation_id);
CREATE INDEX idx_query_logs_conversation_created ON query_logs(conversation_id, created_at);
```

#### Updated QueryLog Model
```python
class QueryLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: UUID = Field(index=True)  # NEW FIELD
    query_text: str
    response_text: str
    model_used: str
    context_used: dict = Field(sa_column=Column(JSON))
    tokens_used: int
    latency_ms: float
    ip_address: Optional[str]
    user_agent: Optional[str]
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

### 2. API Interface Changes

#### Updated Request Model
```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None  # NEW FIELD - if None, start new conversation
    context: Optional[dict] = {}
    model: Optional[str] = "anthropic/claude-3.5-sonnet"
```

#### Updated Response Model
```python
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    query_id: UUID

class ChatResponse(BaseModel):
    response: str
    conversation_id: UUID  # NEW FIELD - always returned
    query_id: UUID
    history: List[ChatMessage]  # NEW FIELD - full conversation history
    tokens_used: Optional[int] = None
    latency_ms: float
    context_items_used: int
```

### 3. History Retrieval Service

#### ConversationHistoryService
```python
class ConversationHistoryService:
    def __init__(self, session: Session):
        self.session = session
    
    def get_conversation_history(self, conversation_id: UUID) -> List[ChatMessage]:
        """Retrieve full conversation history ordered chronologically"""
        query = (
            select(QueryLog)
            .where(QueryLog.conversation_id == conversation_id)
            .order_by(QueryLog.created_at)
        )
        logs = self.session.exec(query).all()
        
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
        
        return history
    
    def format_history_for_llm(self, history: List[ChatMessage]) -> str:
        """Format conversation history for inclusion in LLM context"""
        formatted_messages = []
        for msg in history[-10:]:  # Include last 10 messages to manage context size
            timestamp_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            formatted_messages.append(f"[{timestamp_str}] {msg.role}: {msg.content}")
        
        return "\n".join(formatted_messages)
```

### 4. DSPy Integration Updates

#### Enhanced MattGPT Module
```python
class MattResponseWithHistory(dspy.Signature):
    """Generate a response as Matt would, considering conversation history and context."""
    
    conversation_history = dspy.InputField(
        desc="Previous messages in this conversation, chronologically ordered"
    )
    context = dspy.InputField(
        desc="Matt's relevant messages and personality information from RAG"
    )
    question = dspy.InputField(
        desc="The current query or prompt to respond to"
    )
    response = dspy.OutputField(
        desc="Response in Matt's authentic voice, considering conversation flow"
    )

class MattGPT(dspy.Module):
    def __init__(self, retriever):
        super().__init__()
        self.retrieve = retriever
        self.generate = dspy.ChainOfThought(MattResponseWithHistory)

    def forward(self, question: str, conversation_history: str = ""):
        # Retrieve relevant context (existing logic)
        context = self.retrieve(question).passages
        context_str = "\n\n".join(context[:50])
        
        # Generate response with history
        prediction = self.generate(
            conversation_history=conversation_history,
            context=context_str,
            question=question
        )

        return dspy.Prediction(
            response=prediction.response,
            context_used=context
        )
```

### 5. Updated API Endpoint

#### Enhanced Chat Endpoint Logic
```python
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    client_info: dict = Depends(get_client_info)
):
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    # Handle conversation continuity
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    with get_session() as session:
        history_service = ConversationHistoryService(session)
        
        # Get conversation history if continuing conversation
        history = []
        history_for_llm = ""
        if request.conversation_id:
            history = history_service.get_conversation_history(request.conversation_id)
            history_for_llm = history_service.format_history_for_llm(history)
        
        # Get Matt-GPT response with history context
        result = app.state.matt_gpt(request.message, conversation_history=history_for_llm)
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Add current exchange to history for response
        current_exchange = [
            ChatMessage(
                role="user",
                content=request.message,
                timestamp=datetime.utcnow(),
                query_id=UUID(query_id)
            ),
            ChatMessage(
                role="assistant",
                content=result.response,
                timestamp=datetime.utcnow(),
                query_id=UUID(query_id)
            )
        ]
        full_history = history + current_exchange
        
        # Schedule background logging with conversation_id
        background_tasks.add_task(
            log_query,
            query_id=UUID(query_id),
            conversation_id=UUID(conversation_id),  # NEW PARAMETER
            query_text=request.message,
            response_text=result.response,
            model=request.model,
            context_used={"passages": result.context_used[:10]},
            latency_ms=latency_ms,
            client_info=client_info
        )
        
        return ChatResponse(
            response=result.response,
            conversation_id=UUID(conversation_id),
            query_id=UUID(query_id),
            history=full_history,  # NEW FIELD
            latency_ms=latency_ms,
            context_items_used=len(result.context_used)
        )
```

## Implementation Steps

### Phase 1: Database Schema Update (30 minutes)
1. **Create migration script** to add conversation_id column and indexes
2. **Update QueryLog model** in models.py
3. **Test database changes** with sample data

### Phase 2: Core Service Implementation (45 minutes)
1. **Create ConversationHistoryService** class
2. **Implement history retrieval logic**
3. **Implement LLM context formatting**
4. **Add unit tests** for history service

### Phase 3: API Interface Updates (30 minutes)
1. **Update request/response models** in main.py
2. **Add ChatMessage model** for history representation
3. **Update API documentation** (auto-generated OpenAPI)

### Phase 4: DSPy Integration (30 minutes)
1. **Create new signature** with conversation history
2. **Update MattGPT module** to accept history parameter
3. **Test DSPy integration** with sample conversations

### Phase 5: Endpoint Implementation (45 minutes)
1. **Update chat endpoint** with conversation logic
2. **Update background logging** to include conversation_id
3. **Add error handling** for invalid conversation_ids
4. **Test end-to-end functionality**

### Phase 6: Testing & Validation (30 minutes)
1. **Test new conversation flow** (no conversation_id provided)
2. **Test conversation continuation** (valid conversation_id provided)
3. **Test edge cases** (invalid conversation_id, malformed requests)
4. **Validate response format** and history accuracy

## Quality Assurance

### Test Cases
1. **New Conversation**: Request without conversation_id should start new conversation
2. **Continue Conversation**: Request with valid conversation_id should include history
3. **Invalid Conversation ID**: Should handle gracefully (404 or start new)
4. **History Formatting**: Verify correct chronological ordering and role assignment
5. **Context Integration**: Ensure history improves response relevance
6. **Performance**: Verify minimal latency impact from history retrieval

### Performance Considerations
- **Database Indexing**: Ensure conversation_id queries are optimized
- **History Limits**: Cap history size to prevent token limit issues
- **Memory Usage**: Monitor impact of storing full conversations
- **Cache Strategy**: Consider caching recent conversation history

### Security Considerations
- **Conversation Isolation**: Ensure users cannot access others' conversations
- **Data Retention**: Implement conversation cleanup policies
- **Input Validation**: Validate conversation_id format and existence

## Risk Mitigation

### Technical Risks
| Risk | Impact | Mitigation |
|------|---------|------------|
| Database performance degradation | Medium | Proper indexing, query optimization |
| Token limit exceeded with long histories | High | History truncation, intelligent summarization |
| DSPy prompt optimization affected | Medium | A/B testing, fallback to current approach |

### Business Risks
| Risk | Impact | Mitigation |
|------|---------|------------|
| Breaking changes to API | High | Maintain backward compatibility |
| Increased API response times | Medium | Performance monitoring, optimization |
| Storage cost increase | Low | Conversation cleanup policies |

## Success Metrics

### Functional Metrics
- ✅ API returns conversation_id in all responses
- ✅ Conversation history correctly retrieved and formatted
- ✅ LLM responses show improved contextual awareness
- ✅ Full conversation history available in API responses

### Performance Metrics
- History retrieval: <50ms (95th percentile)
- End-to-end latency increase: <10% from baseline
- Database query efficiency: indexed conversation lookups

### Quality Metrics
- Response relevance improvement: measurable via evaluation
- Conversation coherence: qualitative assessment
- Error rate: <1% for conversation operations

## Future Enhancements

### Phase 2 Features
1. **Conversation Summarization**: Compress old history to maintain context
2. **Conversation Branching**: Support multiple conversation threads
3. **Conversation Metadata**: Tags, topics, participant information
4. **Conversation Search**: Find conversations by content or metadata
5. **Conversation Export**: Allow users to download conversation history

### Integration Possibilities
1. **WebSocket Support**: Real-time conversation streaming
2. **Multi-User Conversations**: Group chat functionality
3. **Conversation Analytics**: Usage patterns, topic analysis
4. **Conversation Recommendations**: Suggest related conversations

## Conclusion

This implementation provides a clean, scalable foundation for conversation continuity while maintaining the existing system's simplicity and performance. The approach is backward-compatible and provides immediate value for users wanting to build ongoing conversations with Matt-GPT.