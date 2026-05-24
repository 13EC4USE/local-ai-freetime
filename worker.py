"""Simple FastAPI worker node for a distributed AI platform.

Features:
1) Register worker to master node
2) Send heartbeat every 30 seconds
3) Receive tasks (pull + push)
4) Execute simple tasks
5) Return results to master
"""

from __future__ import annotations

import asyncio
import os
import socket
import time
import uuid
import requests
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel, Field


# -----------------------------
# Configuration (edit if needed)
# -----------------------------
MASTER_URL = os.getenv("MASTER_URL", "http://192.168.1.249:8000").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
WORKER_ID = os.getenv("WORKER_ID", f"worker-{socket.gethostname()}-{uuid.uuid4().hex[:8]}")
WORKER_HOST = os.getenv("WORKER_HOST", "0.0.0.0")
WORKER_PORT = int(os.getenv("WORKER_PORT", "9000"))
HEARTBEAT_SECONDS = 30
POLL_SECONDS = 5


# -----------------------------
# Data models
# -----------------------------
class TaskIn(BaseModel):
    task_id: str
    task_type: str = Field(description="echo | add | sleep | reverse_text")
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    task_id: str
    worker_id: str
    status: str
    result: Any | None = None
    error: str | None = None
    finished_at: float = Field(default_factory=lambda: time.time())


class WorkerState:
    def __init__(self) -> None:
        self.is_registered = False
        self.is_busy = False
        self.last_heartbeat_at: float | None = None
        self.last_error: str | None = None
        self.lock = asyncio.Lock()


state = WorkerState()


# -----------------------------
# Master communication helpers
# -----------------------------
async def register_to_master() -> bool:
    payload = {
        "worker_id": WORKER_ID,
        "host": WORKER_HOST,
        "port": WORKER_PORT,
        "capabilities": ["echo", "add", "sleep", "generate_code", "reverse_text"],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{MASTER_URL}/workers/register", json=payload)
        if response.status_code in (200, 201):
            state.is_registered = True
            state.last_error = None
            print(f"[REGISTER] Success -> {WORKER_ID}")
            return True

        state.last_error = f"Register failed with status {response.status_code}"
        print(f"[REGISTER] {state.last_error}")
        return False
    except Exception as exc:  # beginner-friendly broad catch
        state.last_error = f"Register error: {exc}"
        print(f"[REGISTER] {state.last_error}")
        return False


async def send_heartbeat() -> bool:
    payload = {
        "worker_id": WORKER_ID,
        "status": "busy" if state.is_busy else "idle",
        "timestamp": time.time(),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{MASTER_URL}/workers/heartbeat", json=payload)
        ok = response.status_code in (200, 201)
        if ok:
            state.last_heartbeat_at = time.time()
            state.last_error = None
        else:
            state.last_error = f"Heartbeat failed with status {response.status_code}"
        return ok
    except Exception as exc:  # beginner-friendly broad catch
        state.last_error = f"Heartbeat error: {exc}"
        return False


async def fetch_task_from_master() -> TaskIn | None:
    """Pull one task from master.

    Expected master endpoint:
    GET /workers/{worker_id}/tasks/next
    - 200 + JSON task -> new task
    - 204 -> no task
    """
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{MASTER_URL}/workers/{WORKER_ID}/tasks/next")

        if response.status_code == 204:
            return None
        if response.status_code == 200:
            return TaskIn.model_validate(response.json())

        state.last_error = f"Fetch task failed with status {response.status_code}"
        return None
    except Exception as exc:
        state.last_error = f"Fetch task error: {exc}"
        return None


async def send_result_to_master(task_result: TaskResult) -> None:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{MASTER_URL}/tasks/{task_result.task_id}/result",
                json=task_result.model_dump(),
            )

        if response.status_code not in (200, 201):
            print(f"[RESULT] Failed for {task_result.task_id}: status={response.status_code}")
        else:
            print(f"[RESULT] Sent for task={task_result.task_id}")
    except Exception as exc:
        print(f"[RESULT] Error for task={task_result.task_id}: {exc}")


# -----------------------------
# Task execution
# -----------------------------
def execute_task_logic(task: TaskIn) -> Any:
    """Beginner-friendly task executor.

    Supported task types:
    - echo: payload = {"text": "hello"}
    - add: payload = {"numbers": [1, 2, 3]}
    - sleep: payload = {"seconds": 2}
    - reverse_text: payload = {"text": "abc"}
    """
    if task.task_type == "echo":
        return task.payload.get("text", "")

    if task.task_type == "add":
        numbers = task.payload.get("numbers", [])
        return sum(float(x) for x in numbers)

    if task.task_type == "sleep":
        seconds = int(task.payload.get("seconds", 1))
        seconds = max(0, min(seconds, 60))  # safety limit
        time.sleep(seconds)
        return f"Slept for {seconds} seconds"

    if task.task_type == "reverse_text":
        text = str(task.payload.get("text", ""))
        return text[::-1]
    if task.task_type == "generate_code":
        prompt = task.payload.get("prompt", "Write a simple hello world in Python")
        model_name = task.payload.get("model", "qwen2.5-coder:1.5b")
        system_prompt = task.payload.get("system_prompt", "You are a helpful coding assistant.")
        
        print(f"\n🧠 [AI ENGINE] Sending prompt to Local Ollama ({model_name})...")
        print(f"   System Prompt: {system_prompt}")
        print(f"   User Prompt: {prompt}")
        
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model_name,
                    "system": system_prompt,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            ai_text = response.json().get("response", "Error: No response from model")
            return ai_text
        except Exception as e:
            raise RuntimeError(f"Worker AI Error: {str(e)}") from e

    raise ValueError(f"Unsupported task_type: {task.task_type}")


async def run_task_and_report(task: TaskIn) -> None:
    async with state.lock:
        state.is_busy = True
        try:
            result_value = await asyncio.to_thread(execute_task_logic, task)
            task_result = TaskResult(
                task_id=task.task_id,
                worker_id=WORKER_ID,
                status="success",
                result=result_value,
            )
        except Exception as exc:
            task_result = TaskResult(
                task_id=task.task_id,
                worker_id=WORKER_ID,
                status="failed",
                error=str(exc),
            )
        finally:
            state.is_busy = False

    await send_result_to_master(task_result)


# -----------------------------
# Background loops
# -----------------------------
async def register_loop() -> None:
    while not state.is_registered:
        ok = await register_to_master()
        if ok:
            return
        await asyncio.sleep(5)


async def heartbeat_loop() -> None:
    while True:
        if not state.is_registered:
            await register_loop()

        ok = await send_heartbeat()
        if not ok:
            state.is_registered = False
        await asyncio.sleep(HEARTBEAT_SECONDS)


async def task_polling_loop() -> None:
    while True:
        if state.is_registered and not state.is_busy:
            task = await fetch_task_from_master()
            if task is not None:
                print(f"[TASK] Pulled task={task.task_id} type={task.task_type}")
                await run_task_and_report(task)
        await asyncio.sleep(POLL_SECONDS)


# -----------------------------
# FastAPI app
# -----------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    print(f"[START] Worker starting with id={WORKER_ID}")
    print(f"[START] Master URL: {MASTER_URL}")

    asyncio.create_task(register_loop())
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(task_polling_loop())

    yield


app = FastAPI(title="Simple Worker Node", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "worker_id": WORKER_ID,
        "registered": state.is_registered,
        "busy": state.is_busy,
        "last_heartbeat_at": state.last_heartbeat_at,
        "last_error": state.last_error,
    }


@app.post("/tasks/execute")
async def receive_task(task: TaskIn, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Optional push-mode endpoint.

    Master can POST a task directly to worker:
    POST /tasks/execute
    """
    if state.is_busy:
        return {"accepted": False, "reason": "worker is busy"}

    print(f"[TASK] Pushed task={task.task_id} type={task.task_type}")
    background_tasks.add_task(run_task_and_report, task)
    return {"accepted": True, "task_id": task.task_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=WORKER_HOST, port=WORKER_PORT)