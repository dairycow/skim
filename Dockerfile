FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and cron
RUN apt-get update && apt-get install -y \
    cron \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy bot code
COPY bot.py .

# Copy startup script
COPY startup.sh .
RUN chmod +x /app/startup.sh

# Copy crontab file
COPY crontab /etc/cron.d/skim-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/skim-cron

# Apply cron job
RUN crontab /etc/cron.d/skim-cron

# Create log file to be able to run tail
RUN touch /var/log/cron.log

# Make bot.py executable
RUN chmod +x /app/bot.py

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Use startup script to ensure IB Gateway is ready
CMD ["/app/startup.sh"]
