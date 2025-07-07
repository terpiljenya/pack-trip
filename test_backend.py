import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
# Test database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "")
print(f"Testing connection to: {DATABASE_URL[:50]}...")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Database connection successful!")
        
    # Test if we can import the models
    from backend.models import Base, User, Trip
    print("Models imported successfully!")
    
    # Try to create tables
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()