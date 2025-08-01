# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including curl for health check
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with increased timeout and retries
RUN pip install --no-cache-dir \
    --timeout 1000 \
    --retries 5 \
    --default-timeout=1000 \
    -r requirements.txt

# Copy the entire project (including ai_pipeline)
COPY backend/  ./backend
COPY ai_pipeline/ ./ai_pipeline

# Create uploads directory if it doesn't exist
RUN mkdir -p backend/uploads

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000


# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]