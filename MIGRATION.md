# ย้ายโปรเจคไปเครื่องหลัก — เอกสารสรุปและขั้นตอน (Migration)

เอกสารนี้สรุปการคุยและเป็นคู่มือแบบทีละขั้นตอนสำหรับย้ายโปรเจค "Simple Python Worker (FastAPI)" จากเครื่องปัจจุบันไปยังเครื่องหลักของคุณ (หรือเครื่องอื่น)

---

## สรุปการคุยสั้น ๆ
- เราสร้างระบบต้นแบบ Distributed AI Platform ประกอบด้วย:
  - `master.py` — simple FastAPI master node (รันที่ ThinkPad/Server)
  - `worker.py` — FastAPI worker node (รันที่ MSI / เครื่องที่เป็น worker)
  - `ui.py` — Streamlit UI เพื่อส่งงานและดูสถานะ
  - `requirements.txt`, `README.md` — เอกสาร + dependencies
- ฟีเจอร์หลักที่ทำแล้ว:
  - Worker ลงทะเบียนกับ master (`/workers/register`) และส่ง heartbeat (`/workers/heartbeat`)
  - Master ให้ worker ดึงงาน (`GET /workers/{worker_id}/tasks/next`) และรับผลกลับ (`POST /tasks/{task_id}/result`)
  - Streamlit UI (3 tabs): Dashboard, Submit Task (มี `system_prompt`), Task History
  - Worker สามารถเรียก Ollama local API เพื่อ `generate` (task_type: `generate_code`) — ต้องมีโมเดลติดตั้งใน Ollama

---

## ไฟล์ที่ต้องคัดลอกไปเครื่องหลัก
คัดลอกโฟลเดอร์โปรเจคทั้งหมด (แนะนำใช้ Git หรือ zip/rsync/scp)

- `master.py`  — Master API
- `worker.py`  — Worker node
- `ui.py`      — Streamlit UI
- `requirements.txt` — Python dependencies
- `README.md`  — คู่มือสั้น
- `MIGRATION.md` — (ไฟล์นี้)

อย่า: ไม่จำเป็นต้องก็อปไดเรคทอรี virtualenv (`.venv`) — ให้สร้าง venv ใหม่บนเครื่องปลายทาง

ถ้าต้องการเก็บประวัติการพัฒนา: ให้สร้าง Git repo แล้ว push/pull ระหว่างเครื่อง

---

## เตรียมเครื่องหลัก (ทั่วไป)
ต่อไปนี้มีคำสั่งตัวอย่างสำหรับ Windows (PowerShell) และ Linux (Ubuntu). ปรับตาม OS ของเครื่องหลัก

1) สร้างโฟลเดอร์โปรเจค และคัดลอกไฟล์เข้า

Windows (PowerShell):
```powershell
mkdir C:\dev\ai-project
# คัดลอกไฟล์ (ตัวอย่างจาก USB หรือ network share)
# Copy-Item -Path "D:\backup\ai\*" -Destination "C:\dev\ai-project" -Recurse
cd C:\dev\ai-project
```

Linux (Ubuntu):
```bash
mkdir -p ~/ai-project
# ถ้าคัดลอกจากเครื่องอื่นผ่าน scp:
# scp -r user@source:/path/to/ai/* ~/ai-project/
cd ~/ai-project
```

2) สร้าง Virtual Environment และติดตั้ง dependencies

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3) (ถ้าใช้ Ollama บนเครื่อง worker เดียวกัน) ให้ติดตั้ง/รัน Ollama ตามเอกสารของ Ollama และติดตั้ง/ดาวน์โหลดโมเดลที่ต้องการ

ตัวอย่างคำสั่ง (บนเครื่องที่มี `ollama` CLI):
```powershell
# ตัวอย่าง Windows PowerShell
# Pull model qwen2.5-coder:1.5b
ollama pull qwen2.5-coder:1.5b
# ตรวจสอบโมเดล
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 6
```

หรือบน Linux:
```bash
ollama pull qwen2.5-coder:1.5b
curl http://localhost:11434/api/tags
```

> หมายเหตุ: หากไม่ได้ใช้ Ollama local ให้ตั้งค่า `OLLAMA_URL` เป็น endpoint ของโมเดลที่ใช้ (เช่น remote API)

---

## ตั้งค่า environment variables ที่สำคัญ
- `MASTER_URL` — URL ของ master (เช่น `http://192.168.1.249:8000`) (worker ใช้ค่านี้เพื่อ register/heartbeat)
- `WORKER_PORT` — พอร์ตที่ worker จะรัน (default 9000)
- `WORKER_HOST` — host bind (default `0.0.0.0`)
- `OLLAMA_URL` — (optional) `http://localhost:11434` หรือ endpoint ของ Ollama instance

ตัวอย่าง (Windows PowerShell):
```powershell
$env:MASTER_URL = "http://192.168.1.249:8000"
$env:WORKER_PORT = '9001'   # เลือกพอร์ตที่ว่าง
$env:OLLAMA_URL = 'http://localhost:11434'
```

ตัวอย่าง (Linux):
```bash
export MASTER_URL=http://192.168.1.249:8000
export WORKER_PORT=9001
export OLLAMA_URL=http://localhost:11434
```

---

## รันแต่ละส่วน (order)
1) รัน Master (บนเครื่องที่จะเป็น controller)
```bash
python master.py
# คาดว่าจะรันที่ http://0.0.0.0:8000
```

2) รัน Worker (บนเครื่อง worker — ถ้าเป็นเครื่องหลักที่คุณกำลังย้ายมาด้วย ให้รันบนเครื่องนั้น)
```powershell
# ถ้าใช้ PowerShell และต้องการพอร์ตเฉพาะ
$env:WORKER_PORT='9001'
python worker.py
```
หรือ Linux:
```bash
WORKER_PORT=9001 python worker.py
```

3) รัน UI (Streamlit)
```bash
streamlit run ui.py
# UI จะเปิดที่ http://localhost:8501
```

---

## ตรวจสอบหลังย้าย (Verification)
- ตรวจสอบ master running:
```bash
curl http://127.0.0.1:8000/openapi.json
```
- ตรวจสอบ worker ลงทะเบียนกับ master:
```bash
curl http://<MASTER_HOST>:8000/workers
# ควรเห็น worker_id, status, last_heartbeat_at
```
- ตรวจสอบ task flow (submit + check):
```bash
# ส่งงานทดสอบ (echo)
curl -X POST http://<MASTER_HOST>:8000/tasks/submit -H "Content-Type: application/json" -d '{"task_type":"echo","payload":{"text":"hello"}}'
# ดูงานทั้งหมด
curl http://<MASTER_HOST>:8000/tasks
```
- ตรวจสอบ Ollama local (ถ้าใช้):
```bash
curl http://localhost:11434/api/tags
# ควรเห็น models
```
- ทดสอบ generate endpoint ต่อโมเดล:
```bash
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model":"qwen2.5-coder:1.5b","prompt":"Hello","stream":false}'
```

---

## ปัญหาที่อาจเจอและการแก้ไขเบื้องต้น
- พอร์ตชน: ถ้า `Address already in use` ให้เปลี่ยน `WORKER_PORT` หรือปิด process ที่ใช้พอร์ตนั้น
- Ollama 404: แปลว่ายังไม่มีโมเดลหรือ endpoint path ต่างจากที่โค้ดเรียก — ตรวจ `OLLAMA_URL` และ `ollama pull <model>`
- Worker ไม่ลงทะเบียน: ตรวจว่า `MASTER_URL` ถูกต้อง และ master รันอยู่และเข้าถึงได้จากเครื่อง worker

---

## ตัวเลือกการย้าย (ง่าย → เชิงปฏิบัติ)
1. คัดลอกไฟล์โดยตรง (USB / network) — เหมาะถ้าไม่มีการเปลี่ยนบ่อย
2. ใช้ `scp` / `rsync` ระหว่างเครื่อง — ดีกว่าสำหรับการทำ remote copy
3. ใช้ Git — แนะนำถ้าคุณจะพัฒนาและย้ายหลายครั้ง:
```bash
git init
git add .
git commit -m "initial"
# push ไป remote repo หรือ clone บนเครื่องปลายทาง
```

---

## บันทึกการคุย (Conversation log summary)
- เริ่มจากโค้ดตัวอย่าง worker และ master แบบง่าย
- ผมช่วยสร้าง `worker.py` ที่ใช้ FastAPI, heartbeat, registration, task pull/execute/report
- ผมสร้าง `master.py` ที่มี in-memory task queue และ endpoints ที่ worker ต้องการ
- เพิ่ม Streamlit UI (`ui.py`) เพื่อส่งงานและดูสถานะ
- แก้ไขให้รองรับ `generate_code` โดยเรียก Ollama local API; พบว่าเครื่อง worker มี Ollama ติดตั้งแต่ยังไม่มีโมเดล จึงแนะนำ `ollama pull ...`
- ปรับปรุง UI ให้สวยขึ้น (Dashboard, Task History, System Prompt)

---

## ถ้าต้องการให้ผมช่วยบนเครื่องหลัก (ตัวเลือก)
- ผมสามารถรันคำสั่งบนเครื่องนี้ให้ (ถ้าคุณต้องการผมรัน `ollama pull` หรือทดสอบ) — แจ้งได้ว่าต้องการให้ผมรันคำสั่งไหน
- หรือผมจะออกคำสั่งทีละขั้นให้คุณคัดลอกไปวางบนเครื่องหลักก็ได้

---

ถ้าต้องการ ผมจะสร้าง `deploy.sh` / `deploy.ps1` สำหรับ run แบบสคริปต์อัตโนมัติ หรือช่วยตั้งค่า Git repo ให้ด้วย แจ้งมาครับว่าชอบวิธีไหน
