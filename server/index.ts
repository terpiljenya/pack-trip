// This is a wrapper script to start the Python backend
import { spawn } from 'child_process';

console.log("Starting Python FastAPI backend...");

// Start the Python backend directly without reload to avoid multiprocessing issues
const pythonProcess = spawn('python3', ['-c', `
import sys
sys.path.insert(0, '.')
import os
os.environ["PYTHONPATH"] = "."
os.environ["NODE_ENV"] = "development"
from dotenv import load_dotenv
load_dotenv()

# Start Vite
import subprocess
print("Starting Vite frontend on port 5173...")
vite = subprocess.Popen(["npx", "vite", "--host", "0.0.0.0", "--port", "5173"])

# Start FastAPI without reload
print("Starting FastAPI backend on port 5001...")
import uvicorn
uvicorn.run("backend.main:app", host="0.0.0.0", port=5001, log_level="info")
`], {
  stdio: 'inherit',
  cwd: process.cwd()
});

pythonProcess.on('error', (err) => {
  console.error('Failed to start Python backend:', err);
  process.exit(1);
});

pythonProcess.on('exit', (code) => {
  process.exit(code || 0);
});