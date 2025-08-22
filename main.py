from fastapi import FastAPI, BackgroundTasks, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
import time
import uuid
import logging
import os
import asyncio
from datetime import datetime

from database import init_db, get_session
from models import QueryLog
from matt_gpt import setup_dspy
from conversation_history import ConversationHistoryService, ChatMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication setup
security = HTTPBearer()

def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the bearer token for API access"""
    expected_token = os.getenv("MATT_GPT_BEARER_TOKEN")
    if not expected_token:
        logger.error("MATT_GPT_BEARER_TOKEN not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured"
        )
    
    if credentials.credentials != expected_token:
        logger.warning(f"Invalid bearer token attempt from request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug("Bearer token validated successfully")
    return credentials.credentials


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Matt-GPT API server...")
    
    logger.info("Initializing database...")
    init_db()
    logger.info("Setting up MattGPT DSPy system...")
    app.state.matt_gpt = setup_dspy()
    logger.info("Matt-GPT API startup complete")
    yield
    # Shutdown
    logger.info("Shutting down Matt-GPT API...")


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
    openrouter_api_key: str  # User must provide their own API key
    conversation_id: Optional[uuid.UUID] = None  # NEW: Continue existing conversation or start new
    context: Optional[dict] = {}
    model: Optional[str] = "anthropic/claude-3.5-sonnet"


class ChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID  # NEW: Always returned for conversation continuity
    query_id: str
    history: List[ChatMessage]  # NEW: Complete conversation history
    ok: bool = True
    error_details: Optional[str] = None
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
    conversation_id: uuid.UUID,  # NEW: Track conversation continuity
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
            id=uuid.UUID(query_id),  # Convert string to UUID
            conversation_id=conversation_id,  # NEW: Store conversation ID
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


def run_with_logging(matt_gpt, question, api_key, conversation_history=""):
    """Wrapper to add console logging to matt_gpt processing"""
    
    # === REQUEST LOGGING ===
    logger.info("=" * 80)
    logger.info("NEW CHAT REQUEST RECEIVED")
    logger.info("=" * 80)
    logger.info(f"USER QUESTION: {question}")
    logger.info(f"API KEY (truncated): {api_key[:20]}...")
    logger.info(f"MODEL: anthropic/claude-3.5-sonnet")
    if conversation_history:
        logger.info(f"CONVERSATION HISTORY: {len(conversation_history)} characters")
    logger.info("=" * 80)
    
    try:
        # Call the forward method with user's API key and conversation history
        result = matt_gpt.forward(
            question=question,
            user_openrouter_key=api_key,
            conversation_history=conversation_history
        )
        
        response_text = result.response
        context_used = result.context_used
        
        # === RESPONSE LOGGING ===
        logger.info("=" * 80)
        logger.info("CHAT REQUEST COMPLETED")
        logger.info("=" * 80)
        logger.info(f"RESPONSE LENGTH: {len(response_text)} characters")
        logger.info(f"CONTEXT ITEMS USED: {len(context_used)} items")
        logger.info(f"FINAL RESPONSE:\n{response_text}")
        logger.info("=" * 80)
        
        # Return result object
        return type('Result', (), {
            'response': response_text,
            'context_used': context_used
        })()
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("CHAT REQUEST FAILED")
        logger.error("=" * 80)
        logger.error(f"ERROR: {e}", exc_info=True)
        logger.error("=" * 80)
        raise


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    client_info: dict = Depends(get_client_info),
    token: str = Depends(verify_bearer_token)
):
    """Main chat endpoint with Matt-GPT DSPy implementation and conversation continuity"""
    
    # Very basic console logging
    print("*** CHAT ENDPOINT HIT! ***")
    print(f"Query: {request.message}")
    print(f"From IP: {client_info.get('ip', 'unknown')}")
    if request.conversation_id:
        print(f"Continuing conversation: {request.conversation_id}")
    
    logger.info(f"Authenticated chat request from {client_info.get('ip', 'unknown')}")
    logger.debug(f"Message: {request.message[:50]}...")
    
    # Validate user's OpenRouter API key format
    if not request.openrouter_api_key.startswith('sk-or-v1-'):
        logger.warning("Invalid OpenRouter API key format provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenRouter API key format. Must start with 'sk-or-v1-'"
        )
    
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    # Handle conversation continuity
    conversation_id = request.conversation_id or uuid.uuid4()
    
    # Log the API request details
    logger.info(f"API Request to /chat endpoint")
    logger.info(f"Model: {request.model}")
    logger.info(f"Message length: {len(request.message)} chars")
    logger.info(f"Conversation ID: {conversation_id}")
    logger.info(f"Client IP: {client_info.get('ip', 'unknown')}")
    logger.info(f"User API key: {request.openrouter_api_key[:20]}...")
    
    # Retrieve conversation history and handle conversation logic
    history = []  # Initialize history for all code paths
    history_for_llm = ""
    
    with get_session() as session:
        history_service = ConversationHistoryService(session)
        
        # Get conversation history if continuing conversation
        if request.conversation_id:
            logger.info(f"Retrieving history for conversation {request.conversation_id}")
            # Validate conversation exists
            if not history_service.conversation_exists(request.conversation_id):
                logger.warning(f"Conversation {request.conversation_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {request.conversation_id} not found"
                )
            
            history = history_service.get_conversation_history(request.conversation_id)
            history_for_llm = history_service.format_history_for_llm(history)
            logger.info(f"Retrieved {len(history)} messages from conversation history")
        else:
            logger.info(f"Starting new conversation with ID {conversation_id}")
    
    try:
        # Run MattGPT with logging and conversation history
        def run_matt_gpt_with_logging():
            return run_with_logging(
                app.state.matt_gpt,
                request.message,
                request.openrouter_api_key,
                history_for_llm
            )
        
        # Run in thread pool with timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(run_matt_gpt_with_logging),
            timeout=30.0
        )
        
        response_text = result.response
        context_used = result.context_used
        
        # Log successful response
        logger.info(f"Response generated successfully")
        logger.info(f"Response length: {len(response_text)} chars")
        logger.info(f"Context items used: {len(context_used)}")
        logger.info(f"Response preview: {response_text[:200]}...")
        
        error_details = None
        is_error = False
        
    except asyncio.TimeoutError:
        logger.error("MattGPT generation timed out after 30 seconds")
        response_text = "Sorry, the request timed out. The system is experiencing slow response times."
        error_details = "Request timeout (30s)"
        context_used = []
        is_error = True
        
    except Exception as e:
        import traceback as tb
        logger.error(f"MattGPT generation failed with detailed error: {e}")
        logger.error(f"Full traceback: {tb.format_exc()}")
        
        response_text = f"Sorry, I encountered an error processing your message."
        error_details = str(e)
        context_used = []
        is_error = True
    
    latency_ms = (time.time() - start_time) * 1000
    logger.info(f"Generated response in {latency_ms:.2f}ms")
    
    # Build complete conversation history for response
    current_exchange = [
        ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow(),
            query_id=uuid.UUID(query_id)
        ),
        ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow(),
            query_id=uuid.UUID(query_id)
        )
    ]
    full_history = history + current_exchange
    logger.info(f"Built full conversation history with {len(full_history)} messages")
    
    # Schedule background logging with conversation_id
    background_tasks.add_task(
        log_query,
        query_id=query_id,
        conversation_id=conversation_id,  # NEW: Include conversation ID
        query_text=request.message,
        response_text=response_text,
        model=request.model,
        context_used={
            "passages": context_used[:10] if 'context_used' in locals() else [],
            "used_user_key": bool(request.openrouter_api_key),
            "context_count": len(context_used) if 'context_used' in locals() else 0,
            "conversation_history_length": len(history_for_llm) if history_for_llm else 0
        },
        latency_ms=latency_ms,
        client_info=client_info
    )
    
    logger.debug(f"Query {query_id} logged for analytics")
    
    # Very basic completion logging
    print(f"*** CHAT COMPLETE! Response: {response_text[:50]}...")
    print(f"*** Took: {latency_ms:.2f}ms")
    
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,  # NEW: Always return conversation ID
        query_id=query_id,
        history=full_history,  # NEW: Return complete conversation history
        ok=not is_error,
        error_details=error_details,
        latency_ms=latency_ms,
        context_items_used=len(context_used) if 'context_used' in locals() else 0
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "healthy", "timestamp": datetime.utcnow()}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30
    )