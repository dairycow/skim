# Discord Webhook Setup for Deployed Skim Bot

This guide walks you through adding Discord webhook notifications to your deployed skim trading bot.

## Prerequisites

1. **Discord Server**: You must have a Discord server where you can create webhooks
2. **Server Access**: SSH access to your deployed skim bot server
3. **Bot Deployed**: Skim bot should already be running via Docker Compose

## Step 1: Create Discord Webhook

### In Discord Desktop/Web App:
1. Go to your Discord server
2. Click the **⚙️** next to your server name
3. Select **"Server Settings"** → **"Integrations"**
4. Click **"Create Webhook"** or **"New Webhook"**
5. Configure webhook:
   - **Name**: `Skim Trading Bot` (or your preferred name)
   - **Channel**: Choose the channel for notifications
   - **Avatar**: Optional - upload bot avatar if desired
6. Click **"Copy Webhook URL"** - this is what you need
7. Click **"Save"**

### Webhook URL Format:
```
https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN
```

## Step 2: Add Webhook URL to Server Environment

### Option A: SSH to Server (Recommended)

1. **SSH to your server**:
```bash
ssh root@your-server-ip
cd /opt/skim
```

2. **Edit the .env file**:
```bash
nano .env
```

3. **Add Discord webhook URL** at the end of the file:
```bash
# Discord webhook URL for notifications (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

4. **Save and exit**:
- Press `Ctrl+X`
- Press `Y` to confirm
- Press `Enter` to save

### Option B: Edit via SCP (if you prefer local editing)

1. **Copy .env file locally**:
```bash
scp root@your-server-ip:/opt/skim/.env ./
```

2. **Edit locally** and add the Discord webhook URL

3. **Upload back to server**:
```bash
scp ./env root@your-server-ip:/opt/skim/.env
```

## Step 3: Restart Bot Container

### Method 1: Full Restart (Recommended)
```bash
cd /opt/skim
docker-compose down
docker-compose up -d
```

### Method 2: Just Restart Bot Container
```bash
cd /opt/skim
docker-compose restart bot
```

## Step 4: Verify Discord Integration

### Check 1: Verify Environment Variable
```bash
# Check if webhook URL is set
docker-compose exec bot printenv | grep DISCORD_WEBHOOK_URL
```

### Check 2: Test Notification
```bash
# Trigger a manual scan to test Discord notification
docker-compose exec bot python -m skim.core.bot scan
```

### Check 3: Monitor Logs
```bash
# Watch for Discord-related log messages
docker-compose logs -f bot | grep -i discord
```

You should see:
- `"Discord notification sent successfully"` in the logs
- A notification message in your Discord channel

## Step 5: Verify Full Integration

### Automated Test (if cron is configured)
Wait for the next scheduled scan (check your crontab), or trigger manually:

```bash
# Check cron schedule
cat /etc/cron.d/skim-cron

# Manually trigger if needed
docker-compose exec bot python -m skim.core.bot run
```

## Expected Discord Notifications

### When Candidates Are Found:
- **Colour**: Green (success)
- **Title**: "ASX Market Scan Complete"
- **Description**: "X new candidates found"
- **Fields**: List of candidates with ticker, gap %, and price

### When No Candidates Found:
- **Colour**: Yellow (warning)
- **Title**: "ASX Market Scan Complete" 
- **Description**: "No new candidates found with price-sensitive announcements"

### On Scan Errors:
- **Colour**: Red (error)
- **Title**: "ASX Market Scan Error"
- **Description**: "An error occurred during market scanning"

## Troubleshooting

### Issue: No Discord Notification
**Symptoms**: Bot runs but no Discord message appears

**Solutions**:
1. **Check webhook URL**:
```bash
docker-compose exec bot printenv DISCORD_WEBHOOK_URL
```

2. **Test webhook manually**:
```bash
# On server
curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"Test message from skim bot"}' \
  "YOUR_WEBHOOK_URL"
```

3. **Check bot logs**:
```bash
docker-compose logs bot | grep -i discord
```

### Issue: Webhook Error in Logs
**Symptoms**: `"Failed to send Discord notification (HTTP error)"`

**Solutions**:
1. **Verify webhook is still active** in Discord server settings
2. **Check webhook URL** - re-copy from Discord if needed
3. **Ensure bot has write permissions** in the Discord channel

### Issue: Container Won't Start
**Symptoms**: Docker container fails after adding webhook URL

**Solutions**:
1. **Check .env syntax** - no extra spaces, quotes, etc.
2. **Validate webhook URL format**:
```bash
# Should look like this:
https://discord.com/api/webhooks/123456789/abcdefg-hijklmnop
```

3. **Check docker-compose logs**:
```bash
docker-compose logs bot
```

## Security Considerations

### Webhook URL Security
- **Treat webhook URL like a password** - anyone with it can post to your channel
- **Don't commit .env to git** - it should remain in .gitignore
- **Regenerate webhook** if you suspect it's compromised

### Server Security
- **Keep .env file permissions restricted**:
```bash
chmod 600 /opt/skim/.env
```

- **Regular webhook rotation** (optional but recommended for production)

## Advanced Configuration

### Multiple Channels (Advanced)
If you want notifications in multiple channels:

1. **Create multiple webhooks** in Discord
2. **Use environment variables** like:
```bash
DISCORD_SCAN_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_TRADE_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

3. **Modify bot code** to use different webhooks for different events

### Custom Embed Styling
The Discord integration uses rich embeds with:
- **Green**: Successful scans with candidates
- **Yellow**: No candidates found  
- **Red**: Scan errors

You can customise colours and formatting in `src/skim/notifications/discord.py`.

## Maintenance

### Regular Checks
1. **Monthly**: Verify webhook is still active in Discord
2. **Quarterly**: Rotate webhook URLs for security
3. **After Discord updates**: Test notifications still work

### Monitoring
Set up alerts for:
- Failed Discord notifications in logs
- Webhook rate limiting (Discord limits: 30 requests/minute)
- Container restarts after webhook configuration

## Success Criteria

You'll know it's working when:
- ✅ Bot starts without errors
- ✅ Discord messages appear after scans
- ✅ Messages include candidate details
- ✅ Different colours for different scenarios
- ✅ No error messages in bot logs

## Support

If you encounter issues:

1. **Check logs first**: `docker-compose logs bot`
2. **Verify webhook**: Test manually with curl
3. **Check environment**: Ensure DISCORD_WEBHOOK_URL is set
4. **Review this guide**: Follow troubleshooting steps

The Discord webhook integration is designed to be **non-blocking** - even if Discord notifications fail, the bot will continue trading operations normally.