FROM python:3.11-slim

# Install system dependencies for ffmpeg and audio processing libraries
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    gfortran \
    libsndfile1 \
    libsndfile1-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
ENV PORT=3088
EXPOSE 3088

# Command to run the application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
