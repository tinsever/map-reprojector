# CartA Map Reprojection API Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    proj-bin \
    libproj-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY . .

# Expose port
EXPOSE 5100

# Set environment variables
ENV FLASK_APP=api_main.py
ENV PYTHONUNBUFFERED=1

# Run the API with gunicorn production server
CMD ["gunicorn", "--bind", "0.0.0.0:5100", "--workers", "2", "--timeout", "120", "--preload", "api_main:app"]

