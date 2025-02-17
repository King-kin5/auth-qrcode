# src/infrastructure/database/base.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy_utils import database_exists, create_database
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)

# Create Base class for models
Base = declarative_base()

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db_extensions():
    """Initialize database with required extensions and functions"""
    try:
        # Create database if it doesn't exist
        if not database_exists(engine.url):
            create_database(engine.url)
            logger.info(f"Created database {engine.url.database}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Created all database tables")
        
        with engine.connect() as conn:
            # Create extensions
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm;'))
            
            # Create full-text search function
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION tsvector_update_trigger() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector =
                        setweight(to_tsvector('pg_catalog.english', COALESCE(NEW.title, '')), 'A') ||
                        setweight(to_tsvector('pg_catalog.english', COALESCE(NEW.content, '')), 'B');
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))
            
            conn.commit()
            logger.info("Initialized PostgreSQL extensions and functions")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
