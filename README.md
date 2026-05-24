# Simple Python Worker (FastAPI)

This project is a **beginner-friendly worker node** for your distributed AI platform.

It does exactly what you requested:
1. Registers itself to the master node.
2. Sends heartbeat every 30 seconds.
3. Receives tasks from the master (pull + optional push).
4. Executes tasks.
5. Returns results.

---

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

---

## 2) Run the master

Start master first:

```bash
python master.py
```

Master API runs on:

`http://0.0.0.0:8000`

---

## 3) Run the worker

Default master URL is already set to:

`http://192.168.1.249:8000`

Start worker:

```bash
python worker.py
```

Worker FastAPI server starts on:

`http://0.0.0.0:9000`

Health endpoint:

`GET /health`

---

## 4) Environment variables (optional)

You can override defaults:

- `MASTER_URL` (default: `http://192.168.1.249:8000`)
- `WORKER_ID` (default: auto-generated)
- `WORKER_HOST` (default: `0.0.0.0`)
- `WORKER_PORT` (default: `9000`)

Example (PowerShell):

```powershell
$env:MASTER_URL="http://192.168.1.249:8000"
$env:WORKER_PORT="9000"
python worker.py
```

---

## 5) Master endpoints expected by worker

The worker calls these endpoints on master:

- `POST /workers/register`
- `POST /workers/heartbeat`
- `GET /workers/{worker_id}/tasks/next`
- `POST /tasks/{task_id}/result`

If your master uses different paths, just update URL paths inside `worker.py`.

---

## 6) Task format

Worker expects task JSON like:

```json
{
  "task_id": "task-123",
  "task_type": "add",
  "payload": {
    "numbers": [1, 2, 3]
  }
}
```

Supported `task_type` in this starter worker:

- `echo` → returns `payload.text`
- `add` → sums `payload.numbers`
- `sleep` → sleeps `payload.seconds` (max 60)
- `reverse_text` → reverses `payload.text`

---

## 7) Optional push mode

Master can send task directly to worker:

- `POST /tasks/execute` on worker node

Worker accepts task and processes in background.

---

## 8) Files explanation

### `master.py`
Main master service.

Contains:
- worker register endpoint (`/workers/register`)
- worker heartbeat endpoint (`/workers/heartbeat`)
- pull-task endpoint (`/workers/{worker_id}/tasks/next`)
- task result endpoint (`/tasks/{task_id}/result`)
- helper endpoints for testing (`/tasks/submit`, `/tasks`, `/workers`)
- in-memory worker/task storage (simple starter design)

### `worker.py`
Main worker service.

Contains:
- FastAPI app
- registration loop
- heartbeat loop (30s)
- task polling loop
- task execution logic
- result callback to master
- health endpoint
- push-task endpoint (`/tasks/execute`)

### `requirements.txt`
Python dependencies needed to run worker:
- FastAPI for API server
- Uvicorn for ASGI runtime
- HTTPX for calling master API
- Pydantic for request/response models

### `README.md`
Setup guide + architecture summary + endpoint contracts.

---

## 9) Notes for beginners

- Start simple with `echo` and `add` tasks first.
- Check worker logs for register/heartbeat status.
- Use `GET /health` to verify worker state.
- Once stable, you can add more `task_type` cases in `execute_task_logic()`.
