#!/usr/bin/env python3
import subprocess
import sys
import os
import signal
import time
from dotenv import load_dotenv

load_dotenv()

# Handle Ctrl+C gracefully
def signal_handler(sig, frame):
    print('\nShutting down servers...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    # Set environment
    os.environ["PYTHONPATH"] = "."
    os.environ["NODE_ENV"] = "development"

    # Start Vite in a subprocess
    print("Starting Vite frontend on port 5173...")
    vite_process = subprocess.Popen(
        ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"],
        env=os.environ
    )

    # Give Vite a moment to start
    time.sleep(2)

    # Start FastAPI in the main thread
    print("Starting FastAPI backend on port 5001...")
    import uvicorn

    try:
        uvicorn.run(
            "backend.main:app",
            host="0.0.0.0",
            port=5001,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        vite_process.terminate()
        vite_process.wait()
        print("Servers stopped.")