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
- **./oauth_keys/** - OAuth cryptographic keys (.pem files)
  - Required for OAuth 1.0a authentication
- **.env** - OAuth credentials and configuration
  - Consumer key, access tokens, DH prime

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
- startup.sh will be updated
- Checked into git so will auto-update

## Infrastructure Requirements

### Resource Optimization with OAuth

Since migrating from IB Gateway to OAuth 1.0a, the bot now has **significantly reduced resource requirements**:

**Before (with IB Gateway/Java):**
- IB Gateway container: 1-2 GB RAM
- IBeam container: 512 MB - 1 GB RAM
- Bot container: 256-512 MB RAM
- **Total: 2-4 GB RAM required** (~$12-24/month droplet)

**After (OAuth only):**
- Bot container: 256-512 MB RAM
- **Total: 1 GB RAM sufficient** (~$6/month droplet)
- **Savings: 50-75% cost reduction** ($6-18/month)

### Recommended Droplet Sizes

- **Minimum**: 1 GB RAM / 1 vCPU / 25 GB SSD (~$6/month)
  - Sufficient for paper trading with monitoring
  - ~500 MB free RAM under normal operation
  - Suitable for cron-based bot execution

- **Recommended**: 2 GB RAM / 1 vCPU / 50 GB SSD (~$12/month)
  - Comfortable buffer for peak usage
  - Better for live trading or multiple bots
  - Room for log growth and database expansion

**Why so lightweight?**
- Python 3.12-slim base image (~150 MB)
- No Java/JVM overhead (Gateway removed)
- Cron-based execution (bot idle most of the time)
- OAuth connects directly to api.ibkr.com (no Gateway proxy)
- Minimal dependencies (7 lightweight Python packages)

## First Deploy After These Changes

With custom OAuth 1.0a client implementation:

1. Pull new code with custom IBKR client
2. Rebuild bot container with Python 3.12-slim and pycryptodome
3. Bot authenticates directly with IBKR API using OAuth
4. No Gateway, no IBeam, no Java - just lightweight Python bot

## Potential Issues

### Issue 1: OAuth Authentication Failed

With OAuth 1.0a setup:
- Check OAuth credentials in .env are correct
- Verify .pem key files exist in /opt/skim/oauth_keys/
- Ensure DH prime was extracted correctly
- Check bot logs for specific OAuth error messages

### Issue 2: Missing oauth_keys Directory

- OAuth requires .pem files to be uploaded to server
- Use scp to copy from local: `scp -r oauth_keys root@server:/opt/skim/`
- Verify permissions: `ls -la /opt/skim/oauth_keys/`

### Issue 3: Environment Variables

If you have custom env vars on server not in repo:
- Create .env file on server at /opt/skim/.env
- It will persist across deployments
- Example:
  ```
  OAUTH_CONSUMER_KEY=your_consumer_key
  OAUTH_ACCESS_TOKEN=your_access_token
  OAUTH_ACCESS_TOKEN_SECRET=your_secret
  OAUTH_SIGNATURE_PATH=/opt/skim/oauth_keys/private_signature.pem
  OAUTH_ENCRYPTION_PATH=/opt/skim/oauth_keys/private_encryption.pem
  OAUTH_DH_PRIME=your_dh_prime_hex
  PAPER_TRADING=true
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

# Check bot OAuth authentication
docker-compose logs bot | grep -i "oauth\|connected"
```

### After Deployment

Wait 3-5 minutes for everything to stabilize, then check:
```bash
cd /opt/skim
docker-compose ps
docker-compose logs bot | tail -50
```

## Manual Intervention Scenarios

### Scenario 1: Fresh Server Setup

1. Clone repo to /opt/skim
2. Create .env file with OAuth credentials
3. Upload oauth_keys/ directory with .pem files
4. Run webhook.sh manually first time
5. Bot authenticates via OAuth directly with IBKR API
6. Future deploys are automatic

### Scenario 2: Database Corruption

```bash
cd /opt/skim
docker-compose down
# Backup/delete data/skim.db if needed
docker-compose up -d
```

### Scenario 3: OAuth Authentication Issues

```bash
cd /opt/skim
docker-compose logs bot | grep -i "oauth\|error" | tail -100
# Check for invalid consumer, missing keys, etc.
# Verify .env OAuth credentials and .pem files
# Update .env or re-upload oauth_keys/ if needed
docker-compose restart bot
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
- ✅ Preserves OAuth keys (./oauth_keys/)
- ✅ Preserves OAuth credentials (.env)
- ✅ Rebuilds application code
- ✅ Direct IBKR API connection via OAuth - no Gateway needed!

Main consideration: Ensure OAuth credentials and .pem files are on server before first deploy.
