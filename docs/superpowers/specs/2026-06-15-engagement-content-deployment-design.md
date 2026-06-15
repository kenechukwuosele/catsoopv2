# Design: Engagement Monitoring Fix + Content Verification + Deployment

**Date:** 2026-06-15  
**Scope:** Three independent workstreams for the CU Quiz App

---

## 1. Engagement Monitoring Improvements

### Problem

- `tinyFaceDetector` with `inputSize: 224` fails on offset/tilted heads — returns null rather than a low-confidence result
- Head pose uses bounding box center, not facial landmarks (landmark model IS loaded but ignored for pose)
- EAR (eye aspect ratio) is computed every frame but never used in state classification
- State flicker: a single bad frame triggers a state change
- Inactivity thresholds too aggressive: 90s → distracted catches careful readers
- Head-roll threshold for "confused" (20°) catches normal reading posture

### Changes (all in `api/templates/affect.py`)

| # | Change | Detail |
|---|--------|--------|
| 1 | `inputSize: 224 → 320` | Biggest fix for offset detection; gives model more context |
| 2 | Landmark-based head pose | Use left/right eye center midpoints + nose tip from `landmarks.positions` to compute yaw/pitch instead of bounding box center; replace `estimateHeadPoseFromBox()` |
| 3 | EAR in state classification | `meanEAR < 0.18` sustained across 2 consecutive samples → `disengaged` |
| 4 | Raise inactivity thresholds | `disengaged` at >90s (was 60s); `distracted` at >150s (was 90s) |
| 5 | State smoothing | 2-sample ring buffer; state only changes if two consecutive detections agree |
| 6 | Head-roll threshold | Raise confused trigger from 20° to 30° |

**Post-change requirement:** `POST /admin/repair` must be called after editing `affect.py` to regenerate all `quiz.catsoop` files.

### No model changes needed

`faceLandmark68TinyNet` is already loaded in every quiz page. No new CDN fetches or static model files required.

---

## 2. Content Verification

### Context

The CLAUDE.md note says only Econs/week1 has quiz questions. An explore agent found 150 questions (15 weeks × 10). This discrepancy must be verified by reading actual `quiz.catsoop` files.

### Verification steps

1. Grep all `quiz.catsoop` files for `<question` blocks — count per week
2. For any empty quiz weeks: use `POST /admin/bulk-import/{course}/{week}` to add 10 questions
3. Spot-check `problem1.catsoop` in each course for real vs. placeholder content
4. Spot-check `lecture1.catsoop` in each course for accuracy

### Courses to check

Physics (4 weeks), Programming (3 weeks), Sports (3 weeks), Automation_and_Robotics (2 weeks), Econs (1 week), Finance (1 week), History (1 week), Languages (1 week) — 15 weeks total.

---

## 3. Functionality Checklist

| Feature | How to verify |
|---------|--------------|
| Student login + JWT | Log in, open browser console, check `window.__CU_TOKEN` present |
| Face enrollment | Enroll via quiz overlay; `GET /admin/face-enrollments` shows entry |
| Face verification | Verify with enrolled face → passes; different face → rejected |
| Quiz submit + XP | Submit quiz, check `GET /{course}/my-stats?username=` for XP increase |
| Leaderboard | `GET /{course}/leaderboard` returns correct ranking |
| Manual hints | Add hint via admin, confirm it appears on quiz question |
| AI hint generation | Admin → generate hints; Ollama must respond (phi3:mini) |
| Affect monitoring | Run with webcam: centered face → focused; offset head → not "no face detected" |
| Admin monitoring tab | Engagement samples appear after student session |
| WebSocket | Instructor WS receives `SUBMISSION` / `AFFECT_CHANGE` events |
| Gradebook | `/{course}/gradebook` accessible as Instructor role |
| Admin repair | `POST /admin/repair` regenerates all quiz/example/gradebook files |

---

## 4. Deployment

### Recommended: Oracle Cloud Free Tier + SystemD + Cloudflare Tunnel

**Server:** Oracle Cloud Always-Free ARM instance (Ampere A1)  
- 4 vCPU, 24 GB RAM, 200 GB block volume  
- Cost: **free permanently**  
- OS: Ubuntu 24.04 ARM64

**Fallback if ARM64 compatibility issues:** Hetzner CX32 — 4 Intel vCPU, 8 GB RAM — €6.29/mo

**Process management:** SystemD (not Docker) — lighter, OS-native, auto-restart, journald logging

**Ingress:** Cloudflare Tunnel (`cloudflared`) — no open inbound ports (80/443 not needed), TLS handled by Cloudflare, domain: `kenechukwuosele.me`

### Architecture

```
Internet (HTTPS)
  └── Cloudflare Edge (kenechukwuosele.me)
        └── cloudflared tunnel (outbound only, no open ports)
              ├── kenechukwuosele.me       → localhost:7667  (CatSooP)
              └── api.kenechukwuosele.me   → localhost:8000  (FastAPI)

Localhost only:
  Ollama      :11434
  SQLite      /opt/catsoop/questions.db
  ChromaDB    /opt/catsoop/_vectors/
```

### Cloudflare Tunnel setup

1. In the Cloudflare dashboard (Zero Trust → Networks → Tunnels), create a tunnel named `cu-quiz`
2. Install `cloudflared` on the server:
   ```bash
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
   sudo dpkg -i cloudflared.deb
   ```
3. Authenticate and create tunnel:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create cu-quiz
   ```
4. Write `/etc/cloudflared/config.yml`:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /etc/cloudflared/<tunnel-id>.json

   ingress:
     - hostname: kenechukwuosele.me
       service: http://localhost:7667
     - hostname: api.kenechukwuosele.me
       service: http://localhost:8000
     - service: http_status:404
   ```
5. Add DNS routes in Cloudflare:
   ```bash
   cloudflared tunnel route dns cu-quiz kenechukwuosele.me
   cloudflared tunnel route dns cu-quiz api.kenechukwuosele.me
   ```
6. Install as SystemD service:
   ```bash
   sudo cloudflared service install
   sudo systemctl enable --now cloudflared
   ```

### Secrets file

`/etc/catsoop.env` (chmod 600, owned by catsoop service user):
```
CU_QUIZ_SECRET=<openssl rand -hex 32>
CU_QUIZ_ADMIN_PASSWORD=<strong password>
CU_QUIZ_BASE_URL=https://api.kenechukwuosele.me
CU_QUIZ_ALLOWED_ORIGINS=https://kenechukwuosele.me,https://api.kenechukwuosele.me
OLLAMA_BASE_URL=http://localhost:11434
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### SystemD units

Three app units: `ollama.service`, `catsoop-api.service`, `catsoop.service` (plus `cloudflared` installed above)

`catsoop-api.service` (FastAPI):
```ini
[Unit]
Description=CU Quiz FastAPI
After=ollama.service
[Service]
EnvironmentFile=/etc/catsoop.env
WorkingDirectory=/opt/catsoop
ExecStart=/opt/catsoop/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=always
[Install]
WantedBy=multi-user.target
```

`catsoop.service` (CatSooP engine):
```ini
[Unit]
Description=CatSooP Course Engine
After=catsoop-api.service
[Service]
EnvironmentFile=/etc/catsoop.env
WorkingDirectory=/opt/catsoop
ExecStart=/opt/catsoop/venv/bin/python3 -m catsoop_engine start
Restart=always
[Install]
WantedBy=multi-user.target
```

### Deployment checklist

1. Provision Oracle ARM Ubuntu 24.04 instance — **only port 22 (SSH) needs to be open**
2. Install: Python 3.12, pip, venv, Ollama, cloudflared
3. Copy project to `/opt/catsoop/`, create `venv/`, install dependencies
4. Pre-pull models: `ollama pull phi3:mini`
5. Copy HuggingFace cache (`all-MiniLM-L6-v2`) from local machine or re-download
6. Write `/etc/catsoop.env` with production secrets
7. Create `ollama.service`, `catsoop-api.service`, `catsoop.service` — `systemctl enable --now` each
8. Set up Cloudflare Tunnel (see above) — `systemctl enable --now cloudflared`
9. Visit `https://kenechukwuosele.me` — confirm HTTPS works via Cloudflare
10. Visit `https://api.kenechukwuosele.me/docs` — confirm FastAPI is reachable
11. Call `POST /admin/repair` to rewrite all quiz URLs to production `CU_QUIZ_BASE_URL`
12. Run RAG ingest for all course weeks
13. Test face enrollment + hint generation

### CORS note

`CU_QUIZ_ALLOWED_ORIGINS` must include both `https://kenechukwuosele.me` and `https://api.kenechukwuosele.me`. `CU_QUIZ_BASE_URL` (`https://api.kenechukwuosele.me`) is automatically added. After updating env, restart `catsoop-api.service`.

### Face auth / webcam note

`getUserMedia` requires HTTPS or localhost. Cloudflare Tunnel provides HTTPS automatically — face auth and affect monitoring will work on the production domain without any extra config.

---

## Out of Scope

- Adding new courses or weeks beyond the 15 existing
- Changing the SQLite database to PostgreSQL
- Multi-server / load balancing (not needed for <30 students)
- CI/CD pipeline
