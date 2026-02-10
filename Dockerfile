# Dockerfile for FKT Application

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p tracker_app/data

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=tracker_app.web.app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "-m", "tracker_app.web.app"]
