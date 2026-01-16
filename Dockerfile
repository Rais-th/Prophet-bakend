FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Shell form - properly expands $PORT
CMD uvicorn api:app --host 0.0.0.0 --port $PORT
