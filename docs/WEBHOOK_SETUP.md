# GitOps Webhook Setup Guide

This guide explains how to set up automated deployments using GitHub webhooks on your DigitalOcean droplet.

## Overview

When you push code to GitHub, a webhook will trigger automatic deployment on your server, running the deployment script without manual intervention.

## Prerequisites

- Server with Docker and docker-compose installed
- Repository cloned to `/opt/skim`
- Port 9000 available on your server
- Root or sudo access

## Option 1: Using webhook (Recommended)

We'll use the lightweight `webhook` tool written in Go.

### Step 1: Install webhook

SSH into your server and install webhook:

```bash
# Install webhook
sudo apt-get update
sudo apt-get install -y webhook

# Verify installation
webhook --version
```

### Step 2: Create webhook configuration

Create the hooks configuration file:

```bash
sudo mkdir -p /etc/webhook
sudo nano /etc/webhook/hooks.json
```

Add this configuration:

```json
[
  {
    "id": "skim-deploy",
    "execute-command": "/opt/skim/deploy/webhook.sh",
    "command-working-directory": "/opt/skim",
    "response-message": "Deployment triggered",
    "trigger-rule": {
      "and": [
        {
          "match": {
            "type": "payload-hmac-sha256",
            "secret": "YOUR_SECRET_HERE",
            "parameter": {
              "source": "header",
              "name": "X-Hub-Signature-256"
            }
          }
        },
        {
          "match": {
            "type": "value",
            "value": "refs/heads/main",
            "parameter": {
              "source": "payload",
              "name": "ref"
            }
          }
        }
      ]
    }
  }
]
```

**Important:** Replace `YOUR_SECRET_HERE` with a strong random secret:

```bash
# Generate a secure secret
openssl rand -hex 32
```

Save this secret - you'll need it for GitHub configuration.

### Step 3: Create systemd service

Create a service to run webhook automatically:

```bash
sudo nano /etc/systemd/system/webhook.service
```

Add this content:

```ini
[Unit]
Description=Webhook server for GitOps deployments
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/webhook -hooks /etc/webhook/hooks.json -port 9000 -verbose
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable webhook
sudo systemctl start webhook
sudo systemctl status webhook
```

### Step 4: Configure firewall

Allow webhook traffic:

```bash
# If using ufw
sudo ufw allow 9000/tcp

# If using iptables
sudo iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
```

### Step 5: Configure GitHub webhook

1. Go to your GitHub repository
2. Navigate to: Settings > Webhooks > Add webhook
3. Configure:
   - **Payload URL**: `http://YOUR_SERVER_IP:9000/hooks/skim-deploy`
   - **Content type**: `application/json`
   - **Secret**: The secret you generated in Step 2
   - **SSL verification**: Disable (since we're using HTTP)
   - **Events**: Select "Just the push event"
   - **Active**: Check this box
4. Click "Add webhook"

### Step 6: Test the webhook

Push a change to your main branch:

```bash
git commit --allow-empty -m "Test webhook"
git push origin main
```

Monitor the webhook service:

```bash
# Watch webhook logs
sudo journalctl -u webhook -f

# Check deployment logs
sudo tail -f /var/log/syslog | grep webhook
```

On GitHub, go to Settings > Webhooks and check the "Recent Deliveries" to see if the webhook was delivered successfully.

## Option 2: Using Python webhook receiver

If you prefer a Python-based solution:

### Step 1: Create webhook receiver script

```bash
sudo nano /opt/skim/deploy/webhook_receiver.py
```

```python
#!/usr/bin/env python3
import hmac
import hashlib
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

WEBHOOK_SECRET = "YOUR_SECRET_HERE"  # Same secret as in GitHub
PORT = 9000

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        # Verify signature
        signature = self.headers.get('X-Hub-Signature-256', '')
        expected_signature = 'sha256=' + hmac.new(
            WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return

        # Parse payload
        payload = json.loads(body)

        # Only deploy on push to main branch
        if payload.get('ref') != 'refs/heads/main':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Skipped - not main branch')
            return

        # Run deployment script
        try:
            subprocess.Popen(['/opt/skim/deploy/webhook.sh'])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Deployment triggered')
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Error: {str(e)}'.encode())

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    print(f'Webhook receiver listening on port {PORT}')
    server.serve_forever()
```

Make it executable:

```bash
sudo chmod +x /opt/skim/deploy/webhook_receiver.py
```

### Step 2: Create systemd service

```bash
sudo nano /etc/systemd/system/skim-webhook.service
```

```ini
[Unit]
Description=Skim Trading Bot Webhook Receiver
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/skim
ExecStart=/usr/bin/python3 /opt/skim/deploy/webhook_receiver.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable skim-webhook
sudo systemctl start skim-webhook
sudo systemctl status skim-webhook
```

Configure GitHub webhook as described in Option 1, Step 5, but use:
- **Payload URL**: `http://YOUR_SERVER_IP:9000/webhook`

## Security Improvements (Optional but Recommended)

### Use nginx as reverse proxy with HTTPS

Instead of exposing the webhook directly, use nginx with Let's Encrypt:

1. Install nginx and certbot:
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

2. Configure nginx:
```bash
sudo nano /etc/nginx/sites-available/webhook
```

```nginx
server {
    listen 80;
    server_name webhook.yourdomain.com;

    location /hooks/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Enable site and get SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/webhook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d webhook.yourdomain.com
```

4. Update GitHub webhook URL to: `https://webhook.yourdomain.com/hooks/skim-deploy`

### Restrict webhook to GitHub IPs

Add firewall rules to only allow GitHub's webhook IPs:

```bash
# Get GitHub's hook IPs from their meta API
curl https://api.github.com/meta | jq .hooks

# Add rules (example)
sudo ufw allow from 192.30.252.0/22 to any port 9000
sudo ufw allow from 185.199.108.0/22 to any port 9000
```

## Troubleshooting

### Check webhook service status

```bash
sudo systemctl status webhook
# or
sudo systemctl status skim-webhook
```

### View logs

```bash
# For webhook (Option 1)
sudo journalctl -u webhook -f

# For Python receiver (Option 2)
sudo journalctl -u skim-webhook -f

# Deployment script logs
sudo tail -f /var/log/syslog | grep skim
```

### Test webhook locally

```bash
curl -X POST http://localhost:9000/hooks/skim-deploy \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main"}'
```

### GitHub webhook delivery issues

1. Go to GitHub > Settings > Webhooks
2. Click on your webhook
3. Check "Recent Deliveries" tab
4. Click on a delivery to see request/response details

### Port not accessible

Check if the port is listening:

```bash
sudo netstat -tlnp | grep 9000
# or
sudo ss -tlnp | grep 9000
```

Check firewall:

```bash
sudo ufw status
# or
sudo iptables -L -n | grep 9000
```

## Update deployment branch

The webhook script currently deploys from a specific branch. To deploy from main branch instead:

```bash
sudo nano /opt/skim/deploy/webhook.sh
```

Change line 19 from:
```bash
git reset --hard origin/claude/asx-trading-bot-setup-011CUaapBZE3mo2kEGwriSKK
```

To:
```bash
git reset --hard origin/main
```

## Manual deployment

You can still deploy manually at any time:

```bash
cd /opt/skim
sudo ./deploy/webhook.sh
```

## Summary

You now have automated GitOps deployments. When you push to your main branch:

1. GitHub sends a webhook to your server
2. Webhook receiver verifies the signature
3. Deployment script runs automatically
4. Bot is rebuilt and restarted with new code

Monitor deployments via logs and check bot status after deployments.
