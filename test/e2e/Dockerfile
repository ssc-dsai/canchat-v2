FROM node:slim AS builder

RUN mkdir /app

WORKDIR /app

COPY ./package-lock.json ./package-lock.json

COPY ./package.json ./package.json

COPY ./playwright.config.ts ./playwright.config.ts

RUN apt update && apt install -y curl git rsync && rm -rf /var/lib/apt/lists/*

RUN npm install -D @playwright/test@latest

RUN npx playwright install --with-deps --only-shell

FROM node:slim AS final

WORKDIR /app

ENV PW_TEST_HTML_REPORT_OPEN='never'

COPY --from=builder / /