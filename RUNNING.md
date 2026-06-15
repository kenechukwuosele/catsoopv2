# CU Quiz App — How the Server Works

## What's Actually Running

The app is hosted on **your laptop** (WSL2 on Windows), not a cloud server. Four services run as background daemons managed by SystemD:

| Service | What it does | Port |
|---------|-------------|------|
| `ollama` | AI model server for hint generation | 11434 (localhost only) |
| `catsoop-api` | FastAPI — quiz engine, admin panel, hints, gamification | 8000 (localhost only) |
| `catsoop` | CatSooP — course pages, login, quiz rendering | 7667 (localhost only) |
| `cloudflared` | Cloudflare Tunnel — connects your laptop to the internet | (no port — outbound only) |

None of these ports are open to the internet directly. The Cloudflare Tunnel makes an outbound connection to Cloudflare's servers, and all traffic from students flows back through that tunnel. This means:

- No port forwarding on your router needed
- No firewall rules to configure
- Your laptop's IP address doesn't matter — Cloudflare handles it

**Public URLs:**
- Students: `https://quiz.kenechukwuosele.me`
- Admin panel: `https://api.kenechukwuosele.me/admin`
- API docs: `https://api.kenechukwuosele.me/docs`

---

## How Traffic Flows

```
Student browser
    ↓ HTTPS
Cloudflare Edge (London)
    ↓ Encrypted tunnel (outbound from your laptop)
cloudflared (running on your laptop)
    ↓ HTTP localhost
CatSooP :7667  ←→  FastAPI :8000
    ↓
SQLite database (questions.db)
Ollama (hint generation)
```

Cloudflare handles HTTPS/TLS — your laptop only ever sees plain HTTP on localhost.

---

## Effect of Laptop Sleep, Shutdown, and Restart

### Sleep / Lid close
**Site stays up briefly, then pauses.**
WSL2 suspends when Windows sleeps. The Cloudflare tunnel drops, so students get a "Bad Gateway" error while the laptop is asleep. When you wake the laptop, WSL2 resumes within a few seconds and the tunnel reconnects automatically. **No action needed on your part.**

### Restart or shutdown
**Site goes down until you manually open a WSL2 terminal.**
When Windows shuts down, WSL2 stops completely. All four services stop. The SystemD services are configured to start automatically — but only once WSL2 itself is running. WSL2 does not start on Windows boot by default.

**To bring the site back up after a restart:**
1. Open any WSL2 terminal (Windows Terminal → Ubuntu, or the Ubuntu app)
2. That's it — SystemD starts automatically and all four services come back within ~10 seconds

You do not need to run any commands. Just opening the terminal is enough.

**To verify everything came back:**
```bash
systemctl is-active cloudflared catsoop-api catsoop ollama
# Should print: active active active active
```

### Long absence (laptop off for hours/days)
Same as restart — open a WSL2 terminal when you're back and the services start. The Cloudflare tunnel will reconnect to Cloudflare's servers on its own. Students will see "Bad Gateway" the entire time the laptop is off.

### Internet disconnected (no WiFi)
The Cloudflare tunnel drops and students get "Bad Gateway". When internet reconnects, `cloudflared` automatically re-establishes the tunnel within seconds. No action needed.

---

## Checking Server Health

```bash
# Quick status of all four services
systemctl is-active cloudflared catsoop-api catsoop ollama

# If something shows "failed", restart it:
sudo systemctl restart catsoop-api   # or catsoop, cloudflared, ollama

# View recent logs for a service:
journalctl -u catsoop-api -n 50 --no-pager
journalctl -u catsoop -n 50 --no-pager
```

---

## Making Changes to the Project

The production services run from `~/.local/share/catsoop/` — the same directory you developed in. There are two ways to work:

### Option A — Edit in place (production stays up)

For small changes you're confident about:

| What you changed | Command to apply it |
|-----------------|-------------------|
| `.catsoop` content files | Nothing — CatSooP reads files on each request |
| `api/` Python code | `sudo systemctl restart catsoop-api` |
| `api/templates/` files | `sudo systemctl restart catsoop-api` then `POST /admin/repair` |

### Option B — Test on localhost first (site goes offline briefly)

For bigger changes you want to verify before going live:

```bash
# 1. Stop production services
sudo systemctl stop catsoop-api catsoop

# 2. Run the dev server (same as before deployment)
cd ~/.local/share/catsoop
source ~/catsoop-env/bin/activate
bash run.sh
# → App now runs on http://localhost:7667 / http://localhost:8000
# → Test your changes, then Ctrl+C to stop

# 3. Bring production back up
sudo systemctl start catsoop-api catsoop
```

The site is only offline during the time you're in test mode. CloudFlared stays running throughout.

**Important:** While in test mode, avoid running `POST /admin/repair` — `run.sh` sets `CU_QUIZ_BASE_URL` to the old tunnel URL. If you need repair during testing:
```bash
CU_QUIZ_BASE_URL=http://localhost:8000 \
  curl -s -X POST http://localhost:8000/admin/repair \
  -H "Authorization: Bearer <token>"
```

---

## Data and Database

Everything lives in `~/.local/share/catsoop/`:

| Data | Location |
|------|---------|
| Quiz questions | `courses/<Course>/<week>/quiz.catsoop` (text files) |
| Student grades | `_logs/_courses/<course>/<username>/` (CatSooP binary logs) |
| XP / streaks / badges | `questions.db` → `student_profiles`, `badges` tables |
| Hints | `_hint_store/<course>/<week>/<question>.json` |
| Face enrollments | `questions.db` → `face_enrollments` table |
| RAG vectors | `_vectors/` (ChromaDB) |

Test data from localhost sessions and production sessions share the same database. There is no separation.

---

## Campus Network Note (Fortinet Filter)

Covenant University's campus firewall blocks newly registered domains. Both `quiz.kenechukwuosele.me` and `api.kenechukwuosele.me` were flagged as "Newly Observed Domain" when first deployed. This block typically lifts within a few days.

Re-evaluation links (submit once from any browser):
- `https://globalurl.fortinet.net/rate/submit.php?id=40497509225B165A3F3826373E613327&cat=5A&loc=https://quiz.kenechukwuosele.me/`
- `https://globalurl.fortinet.net/rate/submit.php?id=49033A142E5A0C4A38276B342E642131&cat=5A&loc=https://api.kenechukwuosele.me/`

Students on mobile data or off-campus WiFi can access the site immediately.

---

## Quick Reference

| Task | Command |
|------|---------|
| Check all services | `systemctl is-active cloudflared catsoop-api catsoop ollama` |
| Restart API after code change | `sudo systemctl restart catsoop-api` |
| Restart CatSooP | `sudo systemctl restart catsoop` |
| View API logs | `journalctl -u catsoop-api -n 50 --no-pager` |
| Switch to test mode | `sudo systemctl stop catsoop-api catsoop && bash run.sh` |
| Switch back to production | `sudo systemctl start catsoop-api catsoop` |
| Full repair (after template change) | `POST /admin/repair` via admin panel or curl |
