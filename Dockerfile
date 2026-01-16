FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Railway provides PORT env var
ENV PORT=8000

# Run uvicorn via Python to avoid shell issues
CMD ["python", "-c", "import os; import uvicorn; uvicorn.run('api:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
