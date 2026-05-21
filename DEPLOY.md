# Deployment Guide — CU Quiz App on Windows Server

## Overview

The CU Quiz App runs **natively on Windows** — no WSL required. Two Python services:

| Service | Port | Purpose |
|---------|------|---------|
| **FastAPI (Uvicorn)** | `8000` | Quiz API, admin panel, hint generation |
| **CatSooP (Cheroot)** | `7667` | Course content pages, authentication |

## Prerequisites

- Windows Server 2019/2022 (or Windows 10/11 Pro)
- Python 3.12+ (from [python.org](https://python.org), check **Add to PATH**)
- Admin access (for service registration)

## Step 1 — Copy the project

Place the project folder anywhere on the server, e.g.:

```
C:\Users\Admin\catsoop-quiz\
```

## Step 2 — Set up the Python environment

Open **PowerShell as Administrator**:

```powershell
cd C:\Users\Admin\catsoop-quiz
python -m venv venv
.\venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy httpx websockets catsoop
```

## Step 3 — Configure the server address

Set the machine's IP so the admin panel and quiz pages know where the API lives:

```powershell
[System.Environment]::SetEnvironmentVariable(
    'CU_QUIZ_BASE_URL',
    'http://<your-server-ip>:8000',
    'Machine'
)
```

> **Skip this step if accessing only via `http://localhost:8000`** — the default works out of the box.

### Other optional env vars

| Variable | Default | Purpose |
|----------|---------|---------|
| `CU_QUIZ_HOST` | `0.0.0.0` | FastAPI bind address |
| `CU_QUIZ_PORT` | `8000` | FastAPI port |
| `CU_QUIZ_BASE_URL` | `http://localhost:8000` | URL browsers use to reach the API |
| `CATSOOP_COURSES_DIR` | `<project>\courses` | Override courses directory |
| `LIVE_FILES_DIR` | `<project>\_live_files` | Override live files directory |

## Step 4 — Configure CatSooP

CatSooP needs a config at `%APPDATA%\catsoop\config.py`. Create it:

```powershell
$configDir = "$env:APPDATA\catsoop"
New-Item -ItemType Directory -Force -Path $configDir

@"
# CU Quiz App — CatSooP Configuration
cs_data_root = r'C:\Users\Admin\catsoop-quiz'
cs_wsgi_server_port = 7667
cs_url_root = 'http://localhost:7667'
cs_auth_type = 'login'
cs_view_without_auth = False
cs_allow_registration = True
cs_require_confirm_email = False
cs_registration_requires_approval = False
cs_debug = True
cs_title = "GATES"
cs_header = "CU QUIZ APP"
cs_footer = "Osele Kenechukwu Alexander"
cs_base_color = "#2572F5"
cs_upload_management = "file"
cs_password_storage = "bcrypt"
cs_session_cookie_lifetime = 86400
"@ | Out-File -FilePath "$configDir\config.py" -Encoding utf8
```

## Step 5 — Test manually

### Start FastAPI
```powershell
cd C:\Users\Admin\catsoop-quiz
.\venv\Scripts\python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/admin` — you should see the admin panel.

### Start CatSooP (in a separate terminal)
```powershell
cd C:\Users\Admin\catsoop-quiz
.\venv\Scripts\python -m catsoop start
```

Open `http://localhost:7667` — you should see the CU Quiz App homepage.

Press **Ctrl+C** to stop both after confirming they work.

## Step 6 — Register as Windows services (auto-start on boot)

### Option A — nssm (recommended)

Download [nssm](https://nssm.cc/download), unzip to `C:\nssm\`.

```powershell
# FastAPI service
C:\nssm\win64\nssm.exe install CUQuizAPI

# CatSooP service
C:\nssm\win64\nssm.exe install CUQuizCatsoop
```

For each service, fill in:
- **Application Path**: `C:\Users\Admin\catsoop-quiz\venv\Scripts\python.exe`
- **Arguments**: `-m uvicorn api.main:app --host 0.0.0.0 --port 8000` (FastAPI)
  or: `-m catsoop start` (CatSooP)
- **Startup directory**: `C:\Users\Admin\catsoop-quiz`

Then start them:
```powershell
Start-Service CUQuizAPI
Start-Service CUQuizCatsoop
Get-Service CUQuiz*   # Verify both are Running
```

### Option B — Task Scheduler (no extra downloads)

```powershell
# FastAPI
$action1 = New-ScheduledTaskAction -Execute "C:\Users\Admin\catsoop-quiz\venv\Scripts\python.exe" `
  -Argument "-m uvicorn api.main:app --host 0.0.0.0 --port 8000" `
  -WorkingDirectory "C:\Users\Admin\catsoop-quiz"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "CUQuizAPI" -Action $action1 -Trigger $trigger -RunLevel Highest

# CatSooP
$action2 = New-ScheduledTaskAction -Execute "C:\Users\Admin\catsoop-quiz\venv\Scripts\python.exe" `
  -Argument "-m catsoop start" `
  -WorkingDirectory "C:\Users\Admin\catsoop-quiz"
Register-ScheduledTask -TaskName "CUQuizCatsoop" -Action $action2 -Trigger $trigger -RunLevel Highest
```

## Step 7 — Firewall

Allow incoming connections to ports 8000 and 7667:

```powershell
New-NetFirewallRule -DisplayName "CU Quiz API" -Direction Inbound `
  -Protocol TCP -LocalPort 8000 -Action Allow

New-NetFirewallRule -DisplayName "CU Quiz Catsoop" -Direction Inbound `
  -Protocol TCP -LocalPort 7667 -Action Allow
```

## Access

| Page | URL |
|------|-----|
| Admin panel | `http://<server-ip>:8000/admin` |
| API docs | `http://<server-ip>:8000/docs` |
| Course homepage | `http://<server-ip>:7667` |
| Course example | `http://<server-ip>:7667/Biology` |

## Stopping the services

```powershell
Stop-Service CUQuizAPI
Stop-Service CUQuizCatsoop
```

To remove:
```powershell
C:\nssm\win64\nssm.exe remove CUQuizAPI confirm
C:\nssm\win64\nssm.exe remove CUQuizCatsoop confirm
```

## Hint generation — future RAG implementation

The current `POST /admin/hints/generate` endpoint calls Anthropic Claude (`api/routes/hints.py:133`) but is **non-functional** — missing `x-api-key` header. The planned replacement is a **local RAG pipeline** (no API key needed):

- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Vector store**: ChromaDB (on-disk, persists to `_vectors/`)
- **Generator**: ollama + Qwen2.5-3B-Q4 (or template-based from retrieved hints)
- **Course content**: Chunked `.catsoop` lecture files ingested per course/week

For now, the hint generate endpoint will return an error. The admin panel's hint editing (manual create/edit/delete) and hint stats work fine without it.
