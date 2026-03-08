# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
# Copy package files
COPY tracker_app/web/frontend/package*.json ./
# Install dependencies
RUN npm install
# Copy frontend source
COPY tracker_app/web/frontend/ ./
# Build the Vite app
RUN npm run build

# Stage 2: Build the Python backend
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

# Copy built frontend from Stage 1 into the Python container's expected path
COPY --from=frontend-builder /app/frontend/dist /app/tracker_app/web/frontend/dist

# Create data directory
RUN mkdir -p tracker_app/data

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=tracker_app.web.app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "-m", "tracker_app.web.app"]
