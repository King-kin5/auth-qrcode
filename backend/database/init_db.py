# src/infrastructure/database/init_db.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import database_exists, create_database
import logging
from typing import Generator

logger = logging.getLogger(__name__)

# You should move this to a config file
DATABASE_URL = "postgresql://username:password@localhost:5432/webintel"

# Create declarative base instance
Base = declarative_base()

def get_engine(url=DATABASE_URL):
    """Create SQLAlchemy engine"""
    return create_engine(url, pool_pre_ping=True)

def init_db() -> None:
    """Initialize database"""
    engine = get_engine()
    
    # Create database if it doesn't exist
    if not database_exists(engine.url):
        create_database(engine.url)
        logger.info(f"Created database {engine.url.database}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Created all database tables")
    
    # Initialize PostgreSQL extensions and functions
    with engine.connect() as conn:
        # Create extensions
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm;'))
        
        # Create full-text search functions
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

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

def init_session_factory(engine=None):
    """Initialize session factory"""
    if engine is None:
        engine = get_engine()
    SessionLocal.configure(bind=engine)

def get_db() -> Generator:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_all():
    """Initialize everything database related"""
    engine = get_engine()
    init_db()
    init_session_factory(engine)
    logger.info("Database initialization complete")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_all()