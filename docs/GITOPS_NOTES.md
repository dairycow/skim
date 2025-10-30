# GitOps Deployment Notes

## Current Setup Analysis

Your gitops webhook is configured at deploy/webhook.sh and will trigger on push to main branch.

## What Happens on Push/Commit

When you push to GitHub:

1. GitHub webhook triggers deploy/webhook.sh on your server
2. Script runs: `git reset --hard origin/main` (pulls latest code)
3. Script runs: `docker-compose down` (stops all containers)
4. Script runs: `docker-compose up -d --build` (rebuilds and starts containers)

## Persistent Data

### What WILL Persist (Safe)

These are mounted as volumes and will survive restarts:

- **./data/** - Trading database (skim.db)
  - Candidates, positions, trades all preserved
- **./logs/** - Log files
- **./ibgateway/** - IB Gateway config including jts.ini
  - Trusted IPs configuration will persist
  - Login credentials stored here

### What Will Be Rebuilt (Expected)

- Docker images (bot container rebuilt from Dockerfile)
- Python dependencies reinstalled
- Application code updated to latest commit

### What Might Need Attention

**Environment Variables (.env file)**
- If you have a .env file on the server at /opt/skim/.env, it will persist
- Make sure .env is in .gitignore so secrets don't get committed
- Environment variables in docker-compose.yml use .env if present

**New Scripts**
- startup.sh, apply_trusted_ips.sh, diagnose.sh will be updated
- They're checked into git so will auto-update

**IB Gateway Container**
- Uses pre-built image, not rebuilt
- Configuration in ./ibgateway/ persists
- Should reconnect automatically after restart

## First Deploy After These Changes

Since we've made significant changes (lazy connection, startup delays, etc.), the first deploy will:

1. Pull new code with all our fixes
2. Rebuild bot container with new bot.py and startup.sh
3. Restart both containers
4. Bot will wait 60s for IB Gateway to be ready
5. Connection should succeed automatically (if jts.ini is configured)

## Potential Issues

### Issue 1: jts.ini Not Configured Yet

If this is first deployment and jts.ini doesn't exist:
- Bot will retry connection 10 times with 20s timeout each
- Will fail but container keeps running
- After IB Gateway creates jts.ini, run: `./apply_trusted_ips.sh`
- Then restart: `docker-compose restart bot`

### Issue 2: IB Gateway Restart Delay

- IB Gateway takes ~2 minutes to fully initialize after restart
- startup.sh waits 60s after TCP port opens
- First connection attempts may still timeout
- Bot will retry automatically via lazy connection

### Issue 3: Environment Variables

If you have custom env vars on server not in repo:
- Create .env file on server at /opt/skim/.env
- It will persist across deployments
- Example:
  ```
  IB_USERNAME=your_username
  IB_PASSWORD=your_password
  IB_CLIENT_ID=1
  ```

## Recommended Deployment Workflow

### Normal Deployment (Code Changes)

Just push to main:
```bash
git add .
git commit -m "your changes"
git push origin main
```

Webhook handles the rest.

### Monitor Deployment

SSH to server and watch:
```bash
# Watch webhook trigger
sudo journalctl -u webhook -f

# Watch containers restart
docker-compose logs -f

# Check bot connection
docker-compose logs bot | grep "IB connection"
```

### After Deployment

Wait 3-5 minutes for everything to stabilize, then check:
```bash
cd /opt/skim
docker-compose ps
docker-compose logs bot | tail -50
./diagnose.sh
```

## Manual Intervention Scenarios

### Scenario 1: Fresh Server Setup

1. Clone repo to /opt/skim
2. Create .env file with credentials
3. Run webhook.sh manually first time
4. Wait for IB Gateway to create jts.ini
5. Run ./apply_trusted_ips.sh
6. Restart: docker-compose restart
7. Future deploys are automatic

### Scenario 2: Database Corruption

```bash
cd /opt/skim
docker-compose down
# Backup/delete data/skim.db if needed
docker-compose up -d
```

### Scenario 3: IB Gateway Not Connecting

```bash
cd /opt/skim
docker-compose logs ibgateway | tail -100
# Check for 2FA timeout, wrong credentials, etc.
# May need to update .env and restart
docker-compose restart ibgateway
```

## Testing the Deployment

Create a test commit:
```bash
# Add a comment to bot.py or create empty commit
git commit --allow-empty -m "Test gitops deployment"
git push origin main
```

Check GitHub webhook delivery:
- Go to Settings > Webhooks
- Click on your webhook
- Check "Recent Deliveries" tab
- Should show 200 response

Check server:
```bash
sudo journalctl -u webhook -f
cd /opt/skim
docker-compose ps
```

## Rollback Procedure

If deployment breaks something:

```bash
cd /opt/skim
# Check git log for last working commit
git log --oneline

# Reset to previous commit
git reset --hard <commit-hash>

# Rebuild
docker-compose down
docker-compose up -d --build
```

Or fix forward by pushing a new commit with the fix.

## Summary

Your gitops setup is solid:
- ✅ Auto-deploys on push to main
- ✅ Preserves trading data (./data/)
- ✅ Preserves IB Gateway config (./ibgateway/)
- ✅ Rebuilds application code
- ✅ Handles secrets via .env

Main consideration: First deploy after connection fixes may need manual jts.ini configuration if not already done.
