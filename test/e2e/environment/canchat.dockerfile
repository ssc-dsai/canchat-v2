# Backend
FROM python:3.11-slim AS builder

RUN apt update && apt install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*

RUN mkdir /app

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -U pip wheel

# Frontend
FROM node:22.14-slim AS final

WORKDIR /app

COPY --from=builder / /

RUN chmod +x ./test/e2e/environment/e2e-entrypoint.sh

ENTRYPOINT ["./test/e2e/environment/e2e-entrypoint.sh"]