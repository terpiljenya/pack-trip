import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from .models import Base

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Create engine with proper connection pooling and SSL handling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Enables connection health checks
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 30,
    }
)

# Add connection event listeners for better error handling
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection parameters for PostgreSQL"""
    pass

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Test connection when checked out from pool"""
    pass

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session with proper error handling
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Utility function to retry database operations
def retry_db_operation(func, max_retries=3, delay=1):
    """Retry database operations with exponential backoff"""
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay * (2 ** attempt))  # Exponential backoff
    return None