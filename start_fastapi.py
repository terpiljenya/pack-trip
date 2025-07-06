#!/usr/bin/env python3
import os
import sys

# Ensure the backend module is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,  # Using port 8000 to avoid conflict with Express on 5000
        reload=True,
        log_level="info"
    )