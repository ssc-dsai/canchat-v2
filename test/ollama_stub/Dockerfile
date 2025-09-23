FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY fauxllama.py ./

EXPOSE 11404

CMD ["uvicorn", "fauxllama:app", "--host", "0.0.0.0", "--port", "11404"]
