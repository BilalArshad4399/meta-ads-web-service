FROM python:3.11-slim

WORKDIR /app

# Skip gcc installation - use pre-compiled wheels only

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create database directory
RUN mkdir -p /app/instance

# Environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run Flask directly for debugging
CMD ["python", "app.py"]