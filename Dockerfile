FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies and cron
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for dependency installation
COPY pyproject.toml .

# Copy source code
COPY src/ ./src/

# Install package in editable mode
RUN pip install --no-cache-dir -e .

# Copy startup script
COPY scripts/startup.sh .
RUN chmod +x /app/startup.sh

# Copy crontab file
COPY crontab /etc/cron.d/skim-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/skim-cron

# Apply cron job
RUN crontab /etc/cron.d/skim-cron

# Create log file to be able to run tail
RUN touch /var/log/cron.log

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Use startup script to run cron and OAuth-authenticated bot
CMD ["/app/startup.sh"]
