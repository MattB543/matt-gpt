from fastapi import FastAPI, BackgroundTasks, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import time
import uuid
import logging
import os
import asyncio
from datetime import datetime

from database import init_db, get_session
from models import QueryLog
from matt_gpt import setup_dspy

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
    context: Optional[dict] = {}
    model: Optional[str] = "anthropic/claude-3.5-sonnet"


class ChatResponse(BaseModel):
    response: str
    query_id: str
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
    client_info: dict = Depends(get_client_info),
    token: str = Depends(verify_bearer_token)
):
    """Main chat endpoint with Matt-GPT DSPy implementation"""
    
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
    
    try:
        # Use Matt-GPT to generate response with user's API key
        logger.debug("Calling MattGPT system with user's OpenRouter key...")
        logger.info(f"User API key starts with: {request.openrouter_api_key[:20]}...")
        
        # Add application-level timeout (30 seconds)
        async def run_matt_gpt():
            return app.state.matt_gpt(request.message, user_openrouter_key=request.openrouter_api_key)
        
        result = await asyncio.wait_for(
            asyncio.create_task(asyncio.to_thread(run_matt_gpt)), 
            timeout=30.0
        )
        
        response_text = result.response
        context_used = result.context_used
        logger.info(f"MattGPT response generated successfully with user's key")
        
    except asyncio.TimeoutError:
        logger.error("MattGPT generation timed out after 30 seconds")
        response_text = "Sorry, the request timed out. The system is experiencing slow response times."
        error_details = "Request timeout (30s)"
        context_used = []
        is_error = True
    except Exception as e:
        import traceback
        logger.error(f"MattGPT generation failed with detailed error: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Return the actual error for debugging
        response_text = f"Sorry, I encountered an error processing your message."
        error_details = str(e)
        context_used = []
        is_error = True
    else:
        error_details = None
        is_error = False
    
    latency_ms = (time.time() - start_time) * 1000
    logger.info(f"Generated response in {latency_ms:.2f}ms")
    
    # Schedule background logging
    background_tasks.add_task(
        log_query,
        query_id=query_id,
        query_text=request.message,
        response_text=response_text,
        model=request.model,
        context_used={
            "passages": context_used[:10] if 'context_used' in locals() else [],
            "used_user_key": bool(request.openrouter_api_key),
            "context_count": len(context_used) if 'context_used' in locals() else 0
        },
        latency_ms=latency_ms,
        client_info=client_info
    )
    
    logger.debug(f"Query {query_id} logged for analytics")
    
    return ChatResponse(
        response=response_text,
        query_id=query_id,
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
        timeout_keep_alive=30,  # Increase keep-alive timeout
        timeout_graceful_shutdown=30  # Increase graceful shutdown timeout
    )