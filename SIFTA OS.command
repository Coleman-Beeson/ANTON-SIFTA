#!/bin/bash
set -u

cd "$(dirname "$0")"

OLLAMA_BIN="/Applications/Ollama.app/Contents/Resources/ollama"
if [ -x "$OLLAMA_BIN" ]; then
    export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"
    if ! "$OLLAMA_BIN" list >/dev/null 2>&1; then
        open -a Ollama --args hidden >/dev/null 2>&1
        sleep 3
    fi
fi

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

export PYTHONPATH=.
exec "$PYTHON" sifta_os_desktop.py
