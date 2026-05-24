"""Simple FastAPI master node for worker.py compatibility.

This server provides the exact endpoints that the worker calls:
- POST /workers/register
- POST /workers/heartbeat
- GET /workers/{worker_id}/tasks/next
- POST /tasks/{task_id}/result

Extra helper endpoints for testing:
- POST /tasks/submit
- GET /tasks
- GET /workers
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Simple Master Node", version="1.0.0")


# -----------------------------
# Data models
# -----------------------------
class WorkerRegisterIn(BaseModel):
    worker_id: str
    host: str
    port: int
    capabilities: list[str] = Field(default_factory=list)


class WorkerHeartbeatIn(BaseModel):
    worker_id: str
    status: Literal["idle", "busy"]
    timestamp: float


class TaskSubmitIn(BaseModel):
    task_type: str = Field(description="echo | add | sleep | reverse_text | generate_code")
    payload: dict[str, Any] = Field(default_factory=dict)
    preferred_worker_id: str | None = None


class TaskRecord(BaseModel):
    task_id: str
    task_type: str
    payload: dict[str, Any]
    status: Literal["queued", "in_progress", "done", "failed"] = "queued"
    assigned_worker_id: str | None = None
    result: Any | None = None
    error: str | None = None
    created_at: float = Field(default_factory=lambda: time.time())
    finished_at: float | None = None


class TaskResultIn(BaseModel):
    task_id: str
    worker_id: str
    status: Literal["success", "failed"]
    result: Any | None = None
    error: str | None = None
    finished_at: float = Field(default_factory=lambda: time.time())


# -----------------------------
# In-memory storage (beginner friendly)
# -----------------------------
workers: dict[str, dict[str, Any]] = {}

tasks: dict[str, TaskRecord] = {}


# -----------------------------
# Worker endpoints (required by worker.py)
# -----------------------------
@app.post("/workers/register")
def register_worker(data: WorkerRegisterIn) -> dict[str, Any]:
    workers[data.worker_id] = {
        "worker_id": data.worker_id,
        "host": data.host,
        "port": data.port,
        "capabilities": data.capabilities,
        "status": "idle",
        "last_heartbeat_at": time.time(),
    }
    return {"ok": True, "message": "worker registered", "worker_id": data.worker_id}


@app.post("/workers/heartbeat")
def worker_heartbeat(data: WorkerHeartbeatIn) -> dict[str, Any]:
    worker = workers.get(data.worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="worker not registered")

    worker["status"] = data.status
    worker["last_heartbeat_at"] = data.timestamp
    return {"ok": True, "message": "heartbeat received"}


@app.get("/workers/{worker_id}/tasks/next")
def get_next_task(worker_id: str):
    if worker_id not in workers:
        raise HTTPException(status_code=404, detail="worker not registered")

    for task in tasks.values():
        if task.status != "queued":
            continue

        # If task is targeted to a specific worker, only that worker can pull it.
        if task.assigned_worker_id is not None and task.assigned_worker_id != worker_id:
            continue

        task.status = "in_progress"
        task.assigned_worker_id = worker_id
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "payload": task.payload,
        }

    # No task available
    return Response(status_code=204)


@app.post("/tasks/{task_id}/result")
def receive_task_result(task_id: str, data: TaskResultIn) -> dict[str, Any]:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    if data.status == "success":
        task.status = "done"
        task.result = data.result
        task.error = None
    else:
        task.status = "failed"
        task.result = None
        task.error = data.error or "unknown error"

    task.finished_at = data.finished_at
    return {"ok": True, "message": "result received", "task_id": task_id}


# -----------------------------
# Helper endpoints (optional)
# -----------------------------
@app.post("/tasks/submit")
def submit_task(data: TaskSubmitIn) -> dict[str, Any]:
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    task = TaskRecord(
        task_id=task_id,
        task_type=data.task_type,
        payload=data.payload,
        assigned_worker_id=data.preferred_worker_id,
    )
    tasks[task_id] = task
    return {"ok": True, "task_id": task_id}


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task.model_dump()


@app.get("/tasks")
def list_tasks() -> dict[str, Any]:
    return {"count": len(tasks), "items": [t.model_dump() for t in tasks.values()]}


@app.get("/workers")
def list_workers() -> dict[str, Any]:
    return {"count": len(workers), "items": list(workers.values())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
