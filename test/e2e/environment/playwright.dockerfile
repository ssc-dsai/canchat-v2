# playwright.dockerfile

FROM node:slim

WORKDIR /app

VOLUME /app

COPY . .

ENV PW_TEST_HTML_REPORT_OPEN='never'

RUN npm install -D @playwright/test@latest

RUN npx playwright install --with-deps
