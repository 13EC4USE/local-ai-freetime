import streamlit as st
import requests
import time
from datetime import datetime

# ชี้ไปที่ Master Node (ThinkPad)
MASTER_URL = "http://192.168.1.249:8000"
REQUEST_TIMEOUT = 20

st.set_page_config(page_title="My AI Platform", page_icon="🤖", layout="wide")
st.title("🤖 My Personal AI Orchestrator")


def api_get(path: str):
    return requests.get(f"{MASTER_URL}{path}", timeout=REQUEST_TIMEOUT)


def api_post(path: str, payload: dict):
    return requests.post(f"{MASTER_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT)


def format_timestamp(ts: float) -> str:
    if ts is None:
        return "Never"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def get_worker_status_icon(status: str) -> str:
    return "🟢" if status == "idle" else "🔴" if status == "busy" else "⚫"



# ======== TAB LAYOUT ========
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🚀 Submit Task", "📋 Task History"])

# ======== TAB 1: DASHBOARD ========
with tab1:
    st.subheader("System Overview")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🖥️ Workers")
        try:
            workers_res = api_get("/workers")
            if workers_res.status_code == 200:
                workers_data = workers_res.json().get("items", [])
                st.metric("Total Workers", len(workers_data))
                
                if workers_data:
                    worker_table = []
                    for w in workers_data:
                        worker_table.append({
                            "Status": get_worker_status_icon(w.get("status", "unknown")),
                            "Worker ID": w.get("worker_id", "N/A")[:20],
                            "Port": w.get("port", "N/A"),
                            "Capabilities": ", ".join(w.get("capabilities", [])),
                            "Last Heartbeat": format_timestamp(w.get("last_heartbeat_at"))
                        })
                    st.dataframe(worker_table, use_container_width=True, hide_index=True)
                else:
                    st.warning("No workers registered.")
            else:
                st.error("Failed to fetch workers.")
        except Exception as e:
            st.error(f"Error loading workers: {e}")
    
    with col2:
        st.markdown("#### 📦 Tasks")
        try:
            tasks_res = api_get("/tasks")
            if tasks_res.status_code == 200:
                tasks_data = tasks_res.json().get("items", [])
                st.metric("Total Tasks", len(tasks_data))
                
                status_counts = {}
                for t in tasks_data:
                    status = t.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                for status, count in status_counts.items():
                    st.write(f"{status.upper()}: {count}")
            else:
                st.error("Failed to fetch tasks.")
        except Exception as e:
            st.error(f"Error loading tasks: {e}")

# ======== TAB 2: SUBMIT TASK ========
with tab2:
    st.subheader("🚀 Submit a New Task")
    with st.form("task_form"):
        prompt = st.text_area(
            "Enter your prompt for the AI:",
            "Write a python script to check odd/even numbers.",
            height=150
        )
        col1, col2 = st.columns(2)
        with col1:
            model = st.selectbox("Select Model", ["qwen2.5-coder:1.5b", "qwen2.5-coder:7b"])
        with col2:
            system_prompt = st.text_input(
                "System Prompt (optional)",
                "You are a helpful Python coding assistant."
            )
        
        submitted = st.form_submit_button("🚀 Submit Task", use_container_width=True)
        
        if submitted:
            payload = {
                "task_type": "generate_code",
                "payload": {
                    "prompt": prompt,
                    "model": model,
                    "system_prompt": system_prompt
                }
            }
            try:
                res = api_post("/tasks/submit", payload)
                if res.status_code == 200:
                    task_id = res.json().get("task_id")
                    st.success(f"✅ Task submitted successfully! (ID: {task_id})")
                    st.session_state['last_task_id'] = task_id
                else:
                    st.error("Failed to submit task.")
            except Exception as e:
                st.error(f"Cannot connect to Master Node: {e}")

# ======== TAB 3: TASK HISTORY ========
with tab3:
    st.subheader("📋 Task History")
    col1, col2 = st.columns([3, 1])
    with col1:
        task_filter = st.selectbox(
            "Filter by status",
            ["all", "queued", "in_progress", "done", "failed"]
        )
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    try:
        tasks_res = api_get("/tasks")
        if tasks_res.status_code == 200:
            all_tasks = tasks_res.json().get("items", [])
            
            if task_filter != "all":
                tasks = [t for t in all_tasks if t.get("status") == task_filter]
            else:
                tasks = all_tasks
            
            tasks = sorted(tasks, key=lambda x: x.get("created_at", 0), reverse=True)
            
            if tasks:
                for task in tasks:
                    with st.expander(f"📌 {task.get('task_id')} - {task.get('status').upper()}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Type:** {task.get('task_type')}")
                            st.write(f"**Status:** {task.get('status')}")
                        with col2:
                            st.write(f"**Created:** {format_timestamp(task.get('created_at'))}")
                            st.write(f"**Worker:** {task.get('assigned_worker_id', 'N/A')}")
                        with col3:
                            if task.get('finished_at'):
                                st.write(f"**Finished:** {format_timestamp(task.get('finished_at'))}")
                        
                        st.markdown("---")
                        st.write("**Prompt:**")
                        st.text(task.get('payload', {}).get('prompt', 'N/A'))
                        
                        if task.get('status') == 'done':
                            st.success("✅ Completed")
                            result = task.get('result', '')
                            if isinstance(result, str) and result.strip():
                                st.markdown("**Result:**")
                                st.code(result, language="python")
                        elif task.get('status') == 'failed':
                            st.error(f"❌ Failed: {task.get('error')}")
                        else:
                            st.info(f"⏳ {task.get('status')}")
            else:
                st.info(f"No tasks with status '{task_filter}'.")
        else:
            st.error("Failed to fetch tasks.")
    except Exception as e:
        st.error(f"Error loading task history: {e}")