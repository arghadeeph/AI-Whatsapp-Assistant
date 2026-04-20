# Use official Python 3.11 image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (if required by some Python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Expose port for Django/Gunicorn
EXPOSE 8000

# Default command (can be overridden)
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ai-whatsapp-assistant.wsgi:application"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
