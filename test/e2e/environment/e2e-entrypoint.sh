#!/usr/bin/env bash

# Frontend
if [ ! -d /app/node_modules ]; then
    echo "Downloading frontend dependencies"
    npm install
fi
echo "Starting frontend"
npm run dev &

# Backend
if [ ! -d /app/backend/.venv ]; then
    echo "Downloading backend dependencies"
    python -m venv /app/backend/.venv
    . /app/backend/.venv/bin/activate
    pip install --no-cache-dir -r ./backend/requirements.txt
fi
echo "Starting backend"

. /app/backend/.venv/bin/activate
cd /app/backend
sh dev.sh &
sleep 60

# Wait until either server stops
wait -n
exit $?
