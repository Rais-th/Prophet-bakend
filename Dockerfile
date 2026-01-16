FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Railway provides PORT env var
ENV PORT=8000

# Run FastAPI with uvicorn - shell form to expand $PORT
CMD ["/bin/sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
