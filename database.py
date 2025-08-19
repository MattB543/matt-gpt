from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import text
from contextlib import contextmanager
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

logger.info("Loading database configuration...")
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable not set")

logger.info(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")

# Best practice: Use connection pooling
engine = create_engine(
    database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=20,
    max_overflow=0,
    echo=False  # Set to True for SQL query logging
)

logger.info("Database engine created with connection pooling (size=20)")


def init_db():
    """Initialize database with pgvector extension"""
    logger.info("Initializing database...")
    
    try:
        with engine.connect() as conn:
            logger.info("Creating pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension created successfully")
        
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
        # Create HNSW indexes for optimal vector performance
        logger.info("Creating HNSW vector indexes...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS messages_embedding_idx
                ON messages USING hnsw (embedding vector_cosine_ops);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS personality_docs_embedding_idx
                ON personality_docs USING hnsw (embedding vector_cosine_ops);
            """))
            
            conn.commit()
            logger.info("HNSW vector indexes created successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


@contextmanager
def get_session():
    """Context manager for database sessions"""
    logger.debug("Creating database session...")
    try:
        with Session(engine) as session:
            logger.debug("Database session created successfully")
            yield session
            logger.debug("Database session closed")
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise