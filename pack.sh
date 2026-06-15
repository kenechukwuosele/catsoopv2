#!/bin/bash
# Creates catsoop-bundle.tar.gz in the current directory.
# Contains: the app folder + the HuggingFace embedding model cache.
# Transfer the .tar.gz to the supervisor's machine, then follow DEPLOY.md.

set -e

BUNDLE="catsoop-bundle.tar.gz"
APP_DIR="/home/alex/.local/share/catsoop"
HF_MODEL="/home/alex/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"

echo "Packing app (~220MB) + HF model (~88MB)..."

tar czf "$BUNDLE" \
  --exclude="$APP_DIR/_cached" \
  --exclude="$APP_DIR/_locks" \
  --exclude="$APP_DIR/venv" \
  --exclude="$APP_DIR/__pycache__" \
  --exclude="$APP_DIR/api/__pycache__" \
  -C /home/alex/.local/share catsoop \
  -C /home/alex/.cache/huggingface/hub models--sentence-transformers--all-MiniLM-L6-v2

echo "Done: $BUNDLE ($(du -sh "$BUNDLE" | cut -f1))"
echo "Transfer this file to the supervisor's machine, then follow DEPLOY.md."
