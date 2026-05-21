# CatSooP + FastAPI notes

## Run / verify
- Start everything via `./run.sh` (activates `/home/alex/catsoop-env/`, runs FastAPI on `172.31.184.39:8000`, then starts CatSooP via `catsoop_engine`).
- FastAPI docs: `http://172.31.184.39:8000/docs`.
- FastAPI admin panel: `http://172.31.184.39:8000/admin`.
- FastAPI admin panel: `http://172.31.184.39:8000/admin`.

## Entry points
- FastAPI app: `api/main.py` (creates tables on import; admin panel routes live here).
- DB config: `api/database.py` uses `sqlite:///./questions.db`.
- CatSooP engine: `catsoop_engine` (run via `python -m catsoop_engine start`).
- CatSooP content lives under `courses/*` with `__INFO__.py` metadata and `.catsoop` content files.

## Config
- CatSooP config lives at `\wsl.localhost\Ubuntu\home\alex\.config\catsoop`.
- CatSooP config lives at `/home/alex/.config/catsoop`.

## Data / state
- SQLite file is `questions.db` in repo root; deleting it resets data.

## External calls
- Hint generation calls Anthropic API from `api/main.py` (`/admin/hints/generate`); requires valid API access to work.
