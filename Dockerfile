FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Railway provides PORT env var
ENV PORT=8000

# Run via start script
ENTRYPOINT ["./start.sh"]
