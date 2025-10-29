FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and cron
RUN apt-get update && apt-get install -y \
    cron \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

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

# Start cron in foreground
CMD cron && tail -f /var/log/cron.log /app/logs/skim_*.log 2>/dev/null || tail -f /var/log/cron.log
