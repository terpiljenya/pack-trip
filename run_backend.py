import uvicorn
import os

if __name__ == "__main__":
    # Set up the environment
    os.environ["PYTHONPATH"] = "."
    
    # Run the FastAPI application
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )