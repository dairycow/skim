# Remove Docker Dependency - Design Document

**Date:** 2025-11-23
**Status:** Approved
**Author:** Design Session

## Overview

Remove Docker dependency from the Skim trading bot to improve deployment speed, reduce resource overhead, and simplify debugging. The application will run directly on the VPS using system Python 3.12+ and uv for package management.

## Context

**Current Setup:**
- Docker container running Python 3.12 slim
- Cron daemon inside container
- GitOps deployment via webhook (rebuild + restart)
- Volume mounts for persistence

**Pain Points:**
- Slow build/deployment times (30-60s)
- Resource overhead (Docker daemon: ~500MB disk, ~100-200MB RAM)
- Debugging complexity (container layer between app and logs)

**Target Environment:**
- Dedicated VPS/cloud instance (Ubuntu/Debian)
- Full root/sudo access
- System Python 3.12+ available

## Design

### Approach: System Cron + Direct Execution

Run the application directly on the VPS using:
- System Python 3.12+ with uv for package management
- System cron for scheduling (reuse existing crontab file)
- Standard Linux tools for logging and monitoring
- GitOps webhook for deployment (simplified, no Docker)

### Deployment Workflow

**New deployment process:**

```bash
# 1. Pull latest code
cd /opt/skim && git fetch && git reset --hard origin/main

# 2. Update dependencies (fast with uv)
/home/skim/.local/bin/uv sync --frozen

# 3. Update crontab (copy from repo to system)
sudo cp /opt/skim/crontab /etc/cron.d/skim-trading-bot
sudo chmod 644 /etc/cron.d/skim-trading-bot

# 4. Reload cron (to pick up any schedule changes)
sudo systemctl reload cron

# 5. Health check
/opt/skim/.venv/bin/python -m skim.core.bot status
```

**Improvements:**
- No Docker build step (saves 30-60 seconds)
- `uv sync` only updates changed dependencies
- Direct execution - no container restart needed
- Running cron jobs continue uninterrupted

### Logging Strategy

**Application logs:**
- Location: `/opt/skim/logs/skim_*.log` (unchanged from current setup)
- Cron output: `/opt/skim/logs/cron.log` (redirected in crontab)
- Access: Direct file access with standard tools (`tail`, `grep`, `less`)

**Log rotation:**
```bash
# /etc/logrotate.d/skim-trading-bot
/opt/skim/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 skim skim
}
```

**Benefits:**
- Direct file access (no docker exec needed)
- Standard Linux tools work
- Easier debugging (no container layer)
- Built-in log rotation

### System Dependencies

**Required packages:**
```bash
sudo apt install -y python3.12 python3.12-venv cron curl git
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Application user:**
```bash
sudo useradd -r -m -d /opt/skim -s /bin/bash skim
sudo mkdir -p /opt/skim/{logs,data,oauth_keys}
sudo chown -R skim:skim /opt/skim
```

**Removed dependencies:**
- Docker Engine (~500MB)
- Docker Compose
- Container runtime overhead (~100-200MB RAM)

### Webhook Script Updates

**New `deploy/webhook.sh`:**

```bash
#!/bin/bash
set -e

cd /opt/skim

# 1. Pull latest code
git fetch origin main
git reset --hard origin/main

# 2. Update dependencies
/home/skim/.local/bin/uv sync --frozen

# 3. Install/update crontab
sudo cp crontab /etc/cron.d/skim-trading-bot
sudo chmod 644 /etc/cron.d/skim-trading-bot
sudo chown root:root /etc/cron.d/skim-trading-bot

# 4. Reload cron daemon
sudo systemctl reload cron

# 5. Health check
/opt/skim/.venv/bin/python -m skim.core.bot status

echo "Deployment completed successfully at $(date)"
```

**Sudo permissions** (`/etc/sudoers.d/skim-deploy`):
```bash
skim ALL=(ALL) NOPASSWD: /bin/cp /opt/skim/crontab /etc/cron.d/skim-trading-bot
skim ALL=(ALL) NOPASSWD: /bin/chmod 644 /etc/cron.d/skim-trading-bot
skim ALL=(ALL) NOPASSWD: /bin/chown root\:root /etc/cron.d/skim-trading-bot
skim ALL=(ALL) NOPASSWD: /bin/systemctl reload cron
```

### Crontab File Updates

**Path changes needed:**
- `/app` → `/opt/skim` (all occurrences)
- `/var/log/cron.log` → `/opt/skim/logs/cron.log`
- Add `skim` user field (required for `/etc/cron.d/` format)

**Example:**
```bash
# Before (Docker)
30 22 * * 0 cd /app && /app/.venv/bin/python -m skim.core.bot scan >> /var/log/cron.log 2>&1

# After (Direct)
30 22 * * 0 skim cd /opt/skim && /opt/skim/.venv/bin/python -m skim.core.bot scan >> /opt/skim/logs/cron.log 2>&1
```

## Migration Plan

### Phase 1: Preparation (Local Machine)

1. Update `crontab` file with new paths and user field
2. Update `deploy/webhook.sh` with new deployment script
3. Create `deploy/sudoers-skim` file
4. Update documentation (README.md, docs/DEVELOPMENT.md)
5. Commit and push changes

### Phase 2: Fresh VPS Setup

1. Restart VM via cloud provider (fresh start)
2. Install system dependencies:
   ```bash
   sudo apt update && sudo apt install -y python3.12 python3.12-venv cron curl git
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Create skim user and directories:
   ```bash
   sudo useradd -r -m -d /opt/skim -s /bin/bash skim
   sudo -u skim git clone <repo-url> /opt/skim
   sudo mkdir -p /opt/skim/{logs,data,oauth_keys}
   sudo chown -R skim:skim /opt/skim
   ```

### Phase 3: Configuration

1. Copy secrets to VPS:
   ```bash
   scp .env root@vps:/opt/skim/.env
   scp -r oauth_keys/* root@vps:/opt/skim/oauth_keys/
   sudo chown skim:skim /opt/skim/.env /opt/skim/oauth_keys/*
   sudo chmod 600 /opt/skim/.env /opt/skim/oauth_keys/*.pem
   ```

2. Install Python dependencies:
   ```bash
   cd /opt/skim
   sudo -u skim /home/skim/.local/bin/uv sync --frozen
   ```

3. Install crontab:
   ```bash
   sudo cp /opt/skim/crontab /etc/cron.d/skim-trading-bot
   sudo chmod 644 /etc/cron.d/skim-trading-bot
   sudo chown root:root /etc/cron.d/skim-trading-bot
   ```

4. Configure sudoers:
   ```bash
   sudo cp /opt/skim/deploy/sudoers-skim /etc/sudoers.d/skim-deploy
   sudo chmod 440 /etc/sudoers.d/skim-deploy
   ```

5. Reload cron:
   ```bash
   sudo systemctl reload cron
   ```

### Phase 4: Validation

1. Health check: `sudo -u skim /opt/skim/.venv/bin/python -m skim.core.bot status`
2. Verify cron loaded: `cat /etc/cron.d/skim-trading-bot`
3. Check logs directory: `ls -la /opt/skim/logs/`
4. Test webhook (trigger or run manually)
5. Monitor first scheduled run: `tail -f /opt/skim/logs/*.log`

## Cleanup

### Files to Remove

```bash
rm Dockerfile
rm docker-compose.yml
rm startup.sh
rm .dockerignore  # Optional
```

### Documentation Updates

- `README.md` - Remove Docker references, update deployment instructions
- `docs/DEVELOPMENT.md` - Update local setup, remove docker-compose
- `docs/ARCHITECTURE.md` - Update deployment section

### Rollback Plan

Keep old VM around for 1-2 days as backup. If issues arise:
1. Point DNS/webhook back to old VM
2. Old Docker setup still works
3. Debug new setup without time pressure

## Benefits Summary

| Benefit | Impact |
|---------|--------|
| **Faster deploys** | 5-10s vs 30-60s (no Docker build) |
| **Less disk usage** | ~500MB saved (no Docker Engine) |
| **Less memory** | ~100-200MB saved (no Docker daemon) |
| **Easier debugging** | Direct log access, no container layer |
| **Simpler stack** | Standard Linux tools (cron, systemd, logrotate) |
| **Better CI/CD** | Can add GitHub Actions for pre-deployment tests |

## Future Enhancements

- GitHub Actions for running tests before webhook deployment
- Systemd journal integration for centralized logging (optional)
- Monitoring/alerting for cron job failures
- Blue/green deployment setup for zero-downtime updates
