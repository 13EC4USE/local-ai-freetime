# Local AI Freetime

Simple distributed AI platform built with Python and FastAPI.

It includes:
- a master API for workers and task management
- a worker node that registers, sends heartbeats, pulls tasks, executes them, and returns results
- a Streamlit UI for submitting tasks and monitoring the system

---

## Project Layout

```text
.
├── LICENSE
├── MIGRATION.md
├── README.md
├── master.py
├── requirements.txt
├── ui.py
└── worker.py
```

---

## What Each File Does

- `master.py` - FastAPI master node with worker registration, heartbeat, task queue, and result collection
- `worker.py` - FastAPI worker node with polling, execution, and Ollama integration
- `ui.py` - Streamlit dashboard for submitting tasks and viewing system status
- `requirements.txt` - Python dependencies for the project
- `MIGRATION.md` - step-by-step migration guide for moving this project to another machine
- `LICENSE` - MIT license

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the master

```bash
python master.py
```

Master API default:

- `http://0.0.0.0:8000`

### 3. Start the worker

```bash
python worker.py
```

Worker defaults:

- `MASTER_URL=http://192.168.1.249:8000`
- `WORKER_HOST=0.0.0.0`
- `WORKER_PORT=9000`

### 4. Start the UI

```bash
streamlit run ui.py
```

### 5. Launch everything with one command on Windows

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\deploy.ps1
```

This opens separate windows for:
- `master.py`
- `worker.py`
- `ui.py`

If port `9001` is busy, use a different worker port:

```powershell
.\deploy.ps1 -WorkerPort 9002
```

---

## Main Endpoints

### Master

- `POST /workers/register`
- `POST /workers/heartbeat`
- `GET /workers/{worker_id}/tasks/next`
- `POST /tasks/{task_id}/result`
- `POST /tasks/submit`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `GET /workers`

### Worker

- `GET /health`
- `POST /tasks/execute`

---

## Task Format

Example task:

```json
{
  "task_id": "task-123",
  "task_type": "generate_code",
  "payload": {
    "prompt": "Write a Python hello world",
    "model": "qwen2.5-coder:1.5b",
    "system_prompt": "You are a helpful Python coding assistant."
  }
}
```

Supported task types in `worker.py`:

- `echo`
- `add`
- `sleep`
- `reverse_text`
- `generate_code`

---

## Ollama Setup

The worker uses local Ollama for `generate_code` tasks.

Check installed models:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 6
```

Pull a model:

```powershell
ollama pull qwen2.5-coder:1.5b
```

---

## Notes

- Keep `master.py` running before you start the worker.
- If port `9000` is busy, set `WORKER_PORT` to another free port.
- If `generate_code` returns an Ollama error, confirm the model is installed locally.

For a full migration checklist, see `MIGRATION.md`.
