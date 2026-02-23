FROM python:3.12-slim

WORKDIR /app

COPY heart/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY heart/main.py .
COPY tools/ ./tools/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
