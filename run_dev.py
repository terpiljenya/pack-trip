#!/usr/bin/env python3
import subprocess
import sys
import os
import signal
import time

# Handle Ctrl+C gracefully
def signal_handler(sig, frame):
    print('\nShutting down servers...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Start the FastAPI backend
print("Starting FastAPI backend on port 5000...")
backend_process = subprocess.Popen(
    [sys.executable, "run_backend.py"],
    env={**os.environ}
)

# Give the backend a moment to start
time.sleep(2)

# Start the Vite frontend dev server
print("Starting Vite frontend on port 5173...")
frontend_process = subprocess.Popen(
    ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"],
    env={**os.environ}
)

try:
    # Wait for both processes
    backend_process.wait()
    frontend_process.wait()
except KeyboardInterrupt:
    # Gracefully terminate both processes
    backend_process.terminate()
    frontend_process.terminate()
    backend_process.wait()
    frontend_process.wait()
    print("Servers stopped.")