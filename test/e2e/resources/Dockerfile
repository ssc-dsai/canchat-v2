# backend.dockerfile
FROM python:3.11-slim AS builder


RUN apt update && apt install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*

RUN mkdir /app

WORKDIR /app

COPY . .


# Install dependencies
RUN pip install --no-cache-dir -U pip wheel setuptools
RUN bash -c '\
    python -m venv ./backend/.venv && \
    . ./backend/.venv/bin/activate && \
    pip install --no-cache-dir -r ./backend/requirements.txt'

FROM node:22.14-slim AS final

VOLUME /app

WORKDIR /app

COPY --from=builder / /

RUN bash -c 'npm install'

WORKDIR /app
