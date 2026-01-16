FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Railway provides PORT env var
ENV PORT=8000
EXPOSE $PORT

# Run FastAPI with uvicorn (uses $PORT from Railway)
CMD uvicorn api:app --host 0.0.0.0 --port $PORT
