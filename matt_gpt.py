import dspy
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class MattResponse(dspy.Signature):
    """Generate a response as Matt would, based on his history, personality, and conversation context."""

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
        desc="Response in Matt's authentic voice, considering conversation flow and context"
    )


class MattGPT(dspy.Module):
    def __init__(self, retriever):
        super().__init__()
        self.retrieve = retriever
        # Don't create ChainOfThought here to avoid LM binding issues
        logger.info("MattGPT module initialized with retriever")

    def forward(self, question: str, user_openrouter_key: Optional[str] = None, conversation_history: str = ""):
        logger.info(f"Processing question: {question[:100]}...")
        if conversation_history:
            logger.info(f"Including conversation history: {len(conversation_history)} characters")
        
        # Retrieve relevant context
        logger.debug("Retrieving relevant context...")
        context_result = self.retrieve(question)
        context = context_result.passages
        logger.info(f"Retrieved {len(context)} context passages")

        # === RAG RESULTS LOGGING ===
        logger.info("=" * 60)
        logger.info("RAG RETRIEVAL RESULTS:")
        logger.info("=" * 60)
        for i, passage in enumerate(context[:10]):  # Log first 10 passages
            logger.info(f"PASSAGE {i+1}:")
            logger.info(f"  Content: {passage[:200]}...")
            if len(passage) > 200:
                logger.info(f"  (truncated from {len(passage)} chars)")
            logger.info("-" * 40)
        if len(context) > 10:
            logger.info(f"... and {len(context) - 10} more passages")
        logger.info("=" * 60)

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
                
                # Load context files dynamically
                def load_context_files():
                    try:
                        context_files = {}
                        
                        # Read personality and preferences
                        with open('context/distilled_personality_and_preferences.md', 'r', encoding='utf-8') as f:
                            context_files['distilled_personality_and_preferences.md'] = f.read()
                        
                        # Read personality report
                        with open('context/personality_report.md', 'r', encoding='utf-8') as f:
                            context_files['personality_report.md'] = f.read()
                        
                        # Read writing style
                        with open('context/writing_style.md', 'r', encoding='utf-8') as f:
                            context_files['writing_style.md'] = f.read()
                        
                        return context_files
                    except Exception as e:
                        logger.warning(f"Could not load context files: {e}")
                        return {}
                
                context_files = load_context_files()
                
                # Format prompt with context files
                project_context = ""
                if context_files:
                    project_context = f"""
<matt_distilled_personality_and_preferences>
{context_files.get('distilled_personality_and_preferences.md', '')}
</matt_distilled_personality_and_preferences>

<matt_personality_report>
{context_files.get('personality_report.md', '')}
</matt_personality_report>

<matt_writing_style>
{context_files.get('writing_style.md', '')}
</matt_writing_style>

"""

                # Format conversation history section
                conversation_section = ""
                if conversation_history:
                    conversation_section = f"""
**CONVERSATION HISTORY:**
(Previous messages in this conversation - use this to maintain context and conversational flow)
{conversation_history}

"""

                # Format prompt manually with enhanced context
                prompt = f"""You are Matt's AI avatar, designed to authentically represent him in digital conversations. Your core purpose is to respond as Matt would, drawing from his extensive message history, personality documents, and communication patterns.

**CRITICAL IDENTITY REQUIREMENTS:**
- Respond as Matt himself, not as an AI describing Matt
- Maintain his authentic voice: communication style, humor, tone, perspective, preferences, value system, and personality
- Draw from the below retrieved context to inform your responses, but don't explicitly reference it directly
- Preserve his typical response length and conversational patterns
- Use his actual phrases, expressions, and way of thinking
- Consider the conversation history to maintain context and natural flow

Here is the context of Matt's personality and preferences:
{project_context}

{conversation_section}**RETRIEVED CONTEXT FROM MATT'S MESSAGE HISTORY:**
(the context may or may not be relevant to the current question/conversation, so you must use your judgement to determine if it is relevant)
{context_str}

**CURRENT QUESTION/CONVERSATION:**
{question}

**RESPONSE INSTRUCTIONS:**
- Respond directly to the CURRENT QUESTION/CONVERSATION as Matt would respond
- Use the conversation history to maintain context and natural conversational flow
- Use the retrieved context to inform your response but don't explicitly reference it
- Maintain authenticity over perfection
- Match Matt's communication style from the retrieved messages and by following the rules in the matt_writing_style context
- Keep responses conversational and natural to his voice
- Include no other text than the response to the question/conversation
- Do not hallucinate or make up information or preferences that you are not very sure Matt would say
- If you're very unsure about something, just say you don't know in a way that is consistent with Matt's personality
"""

                # === PROMPT INPUT LOGGING ===
                logger.info("=" * 60)
                logger.info("RAW PROMPT INPUT (User OpenRouter Key):")
                logger.info("=" * 60)
                logger.info(f"FULL PROMPT:\n{prompt}")
                logger.info("=" * 60)

                logger.debug("Calling chat_completion...")
                messages = [{"role": "user", "content": prompt}]
                response = user_client.chat_completion(messages=messages)
                logger.debug("chat_completion returned successfully")
                
                response_text = response.choices[0].message.content
                logger.debug(f"Response text extracted: {response_text[:50]}...")

                # === PROMPT OUTPUT LOGGING ===
                logger.info("=" * 60)
                logger.info("RAW PROMPT OUTPUT (User OpenRouter Key):")
                logger.info("=" * 60)
                logger.info(f"FULL RESPONSE:\n{response_text}")
                logger.info("=" * 60)
                
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
            
            # === PROMPT INPUT LOGGING (Environment Key) ===
            logger.info("=" * 60)
            logger.info("RAW PROMPT INPUT (Environment OpenRouter Key):")
            logger.info("=" * 60)
            if conversation_history:
                logger.info(f"CONVERSATION HISTORY:\n{conversation_history}")
                logger.info("-" * 40)
            logger.info(f"CONTEXT:\n{context_str}")
            logger.info("-" * 40)
            logger.info(f"QUESTION: {question}")
            logger.info("=" * 60)
            
            generate = dspy.ChainOfThought(MattResponse)
            prediction = generate(
                conversation_history=conversation_history,
                context=context_str,
                question=question
            )
            
            # === PROMPT OUTPUT LOGGING (Environment Key) ===
            logger.info("=" * 60)
            logger.info("RAW PROMPT OUTPUT (Environment OpenRouter Key):")
            logger.info("=" * 60)
            logger.info(f"FULL RESPONSE:\n{prediction.response}")
            logger.info("=" * 60)
            
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
        temperature=0.4
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