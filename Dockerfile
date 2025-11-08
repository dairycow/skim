FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies and cron
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management (official installer from Astral)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files for optimal layer caching
COPY pyproject.toml uv.lock ./

# Copy source code
COPY src/ ./src/

# Install dependencies using uv sync (deterministic, fast)
RUN uv sync --frozen

# Update PATH to include uv and uv-installed packages
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

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
