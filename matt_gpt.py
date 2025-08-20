import dspy
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


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
        # Don't create ChainOfThought here to avoid LM binding issues
        logger.info("MattGPT module initialized with retriever")

    def forward(self, question: str, user_openrouter_key: Optional[str] = None):
        logger.info(f"Processing question: {question[:100]}...")
        
        # Retrieve relevant context
        logger.debug("Retrieving relevant context...")
        context_result = self.retrieve(question)
        context = context_result.passages
        logger.info(f"Retrieved {len(context)} context passages")

        # Format context for generation
        context_str = "\n\n".join(context[:50])  # Limit context size
        logger.debug(f"Context formatted, total length: {len(context_str)} characters")

        # Bypass DSPy contexts and use direct LM calls for now
        if user_openrouter_key:
            logger.info("Using user-provided OpenRouter API key for generation")
            logger.debug(f"User API key in matt_gpt: {user_openrouter_key[:20]}...")
            
            from llm_client import OpenRouterClient
            
            # Use direct OpenRouter client call as fallback
            logger.debug("Generating response with user's OpenRouter key via direct client...")
            try:
                logger.debug("Creating OpenRouterClient with user key...")
                user_client = OpenRouterClient(api_key=user_openrouter_key)
                logger.debug("OpenRouterClient created successfully")
                
                # Format prompt manually
                prompt = f"""You are Matt, responding authentically based on your communication style and experiences.

Context from Matt's messages and personality:
{context_str}

User question: {question}

Respond as Matt would, using his voice and communication style:"""

                logger.debug("Calling chat_completion...")
                messages = [{"role": "user", "content": prompt}]
                response = user_client.chat_completion(messages=messages, max_tokens=1000)
                logger.debug("chat_completion returned successfully")
                
                response_text = response.choices[0].message.content
                logger.debug(f"Response text extracted: {response_text[:50]}...")
                
                # Create mock DSPy prediction object
                prediction = type('Prediction', (), {'response': response_text})()
                logger.info("Response generated successfully with user's key via direct client")
                
            except Exception as e:
                import traceback
                logger.error(f"Direct client generation failed: {e}")
                logger.error(f"Direct client traceback: {traceback.format_exc()}")
                raise
        else:
            # Use default environment key with ChainOfThought
            logger.debug("Generating response with environment OpenRouter key...")
            generate = dspy.ChainOfThought(MattResponse)
            prediction = generate(
                context=context_str,
                question=question
            )
            logger.info("Response generated successfully with environment key")

        return dspy.Prediction(
            response=prediction.response,
            context_used=context
        )


def setup_dspy():
    """Configure DSPy to use OpenRouter"""
    logger.info("Setting up DSPy with OpenRouter...")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    database_url = os.getenv("DATABASE_URL")
    
    if not openrouter_key:
        logger.error("OPENROUTER_API_KEY not found in environment")
        raise ValueError("OPENROUTER_API_KEY required for DSPy setup")
    
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        raise ValueError("DATABASE_URL required for retriever setup")

    logger.debug("Configuring DSPy language model...")
    # Use LiteLLM through DSPy for OpenRouter compatibility
    lm = dspy.LM(
        model="openrouter/anthropic/claude-3.5-sonnet",
        api_key=openrouter_key,
        api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=1000
    )
    logger.info("DSPy language model configured: anthropic/claude-3.5-sonnet")

    logger.debug("Configuring PostgreSQL vector retriever...")
    # Configure retriever
    from retrievers import PostgreSQLVectorRetriever
    retriever = PostgreSQLVectorRetriever(
        connection_string=database_url,
        k=20
    )
    logger.info("PostgreSQL vector retriever configured with k=20")

    logger.debug("Configuring DSPy settings...")
    dspy.settings.configure(lm=lm, rm=retriever)
    logger.info("DSPy settings configured successfully")

    logger.info("Creating MattGPT instance...")
    matt_gpt = MattGPT(retriever)
    logger.info("MattGPT setup complete!")

    return matt_gpt


def test_dspy_setup():
    """Test DSPy setup without making API calls"""
    logger.info("Testing DSPy setup...")
    
    try:
        matt_gpt = setup_dspy()
        logger.info("+ DSPy setup successful")
        return matt_gpt
    except Exception as e:
        logger.error(f"- DSPy setup failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(level=logging.INFO)
    
    print("=== Testing DSPy Setup ===")
    try:
        matt_gpt = test_dspy_setup()
        print("+ DSPy MattGPT module created successfully")
        print("+ Ready for integration with FastAPI")
    except Exception as e:
        print(f"- DSPy setup failed: {e}")