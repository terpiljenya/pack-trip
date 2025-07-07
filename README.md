# PackTrip AI

## Installing Python dependencies

After cloning the repository, run the following from the project root to install everything declared in **pyproject.toml**:

```bash
uv pip install -e .
```

`uv` will automatically create (or reuse) an isolated virtual environment and install all required packages.

---

## Installing JavaScript / Node dependencies

This repository also includes a Node.js codebase (Express server and React/Vite frontend). Install its packages with:

```bash
npm install
```

Make sure you have **Node.js 18+** (or the current active LTS) installed.

---

## Running the application

Start the development server with hot-reload:

```bash
uv run run_dev.py
```

By default this will launch the FastAPI backend on **http://localhost:8000** and the Vite/React frontend on **http://localhost:5173** (proxied via the backend during development).

That's it – happy hacking! 🎉 