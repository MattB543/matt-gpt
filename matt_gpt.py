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
        self.generate = dspy.ChainOfThought(MattResponse)
        logger.info("MattGPT module initialized with retriever and ChainOfThought")

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

        # Update DSPy LM with user's API key if provided
        if user_openrouter_key:
            logger.info("Using user-provided OpenRouter API key for generation")
            user_lm = dspy.LM(
                model="openrouter/anthropic/claude-3.5-sonnet",
                api_key=user_openrouter_key,
                api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=1000
            )
            # Temporarily configure DSPy with user's LM
            old_lm = dspy.settings.lm
            dspy.settings.configure(lm=user_lm)
            
            try:
                # Generate response with user's key
                logger.debug("Generating response with user's OpenRouter key...")
                prediction = self.generate(
                    context=context_str,
                    question=question
                )
                logger.info("Response generated successfully with user's key")
            finally:
                # Restore original LM
                dspy.settings.configure(lm=old_lm)
        else:
            # Use default environment key
            logger.debug("Generating response with environment OpenRouter key...")
            prediction = self.generate(
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