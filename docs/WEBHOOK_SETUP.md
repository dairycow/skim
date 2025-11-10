# GitOps Webhook Setup Guide

This guide explains how to set up automated deployments using GitHub webhooks on your DigitalOcean droplet.

## Overview

When you push code to GitHub, a webhook will trigger automatic deployment on your server, running the deployment script without manual intervention.

## Prerequisites

- Server with Docker and docker-compose installed
- Repository cloned to `/opt/skim`
- Domain name configured with A record pointing to your server
- Port 9000 available on your server (internal only)
- Root or sudo access

## Webhook Setup (Recommended)

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
sudo vim /etc/webhook/hooks.json
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
sudo vim /etc/systemd/system/webhook.service
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

### Step 4: Configure DNS and SSL

**DNS Configuration:**
1. Create A record: `webhook.yourdomain.com → YOUR_SERVER_IP`
2. Wait for DNS propagation (use `nslookup webhook.yourdomain.com` to verify)

**Install nginx and certbot:**
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

**Configure nginx reverse proxy:**
```bash
sudo vim /etc/nginx/sites-available/webhook
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name webhook.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name webhook.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/webhook.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webhook.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location /hooks/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
    }
}
```

**Enable site and obtain SSL certificate:**
```bash
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/webhook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d webhook.yourdomain.com
```

### Step 5: Configure firewall with GitHub IP restrictions

**Get current GitHub webhook IPs:**
```bash
curl https://api.github.com/meta | jq .hooks
```

**Configure UFW firewall:**
```bash
# Allow SSH
sudo ufw allow 22

# Allow GitHub webhook IPs (IPv4)
sudo ufw allow from 192.30.252.0/22 to any port 443
sudo ufw allow from 185.199.108.0/22 to any port 443
sudo ufw allow from 140.82.112.0/20 to any port 443
sudo ufw allow from 143.55.64.0/20 to any port 443

# Allow GitHub webhook IPs (IPv6)
sudo ufw allow from 2a0a:a440::/29 to any port 443
sudo ufw allow from 2606:50c0::/32 to any port 443

# Deny all other traffic to HTTPS
sudo ufw deny 443

# Enable firewall
sudo ufw enable
```

**Note:** Port 9000 should NOT be exposed externally - nginx handles all external traffic.

### Step 6: Configure GitHub webhook

1. Go to your GitHub repository
2. Navigate to: Settings > Webhooks > Add webhook
3. Configure:
   - **Payload URL**: `https://webhook.yourdomain.com/hooks/skim-deploy`
   - **Content type**: `application/json`
   - **Secret**: The secret you generated in Step 2
   - **SSL verification**: Enable (HTTPS with valid certificate)
   - **Events**: Select "Just the push event"
   - **Active**: Check this box
4. Click "Add webhook"

### Step 7: Test the webhook

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



## SSL Certificate Management

### Monitor certificate expiry
```bash
# Check certbot auto-renewal is configured
sudo systemctl status certbot.timer

# Test renewal process
sudo certbot renew --dry-run

# Check certificate expiry date
sudo certbot certificates
```

### Manual certificate renewal
```bash
# Renew all certificates
sudo certbot renew

# Renew specific certificate
sudo certbot renew --cert-name webhook.yourdomain.com
```

## Security Hardening (Recommended)

### Current GitHub webhook IP ranges
As of the latest update, GitHub's webhook IPs are:
- **IPv4:** 192.30.252.0/22, 185.199.108.0/22, 140.82.112.0/20, 143.55.64.0/20
- **IPv6:** 2a0a:a440::/29, 2606:50c0::/32

**Always verify current IPs:** `curl https://api.github.com/meta | jq .hooks`

### Additional security measures
```bash
# Install fail2ban for nginx protection
sudo apt-get install fail2ban
sudo systemctl enable fail2ban

# Monitor nginx access logs for suspicious activity
sudo tail -f /var/log/nginx/access.log

# Check SSL certificate configuration
sudo nginx -t | grep -i ssl
```

## Troubleshooting

### Check webhook service status

```bash
sudo systemctl status webhook
```

### View logs

```bash
# For webhook service
sudo journalctl -u webhook -f

# Deployment script logs
sudo tail -f /var/log/syslog | grep skim
```

### Test webhook locally

```bash
# Test local webhook service
curl -X POST http://localhost:9000/hooks/skim-deploy \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main"}'

# Test HTTPS endpoint (from server)
curl -I https://webhook.yourdomain.com/hooks/skim-deploy

# Test that direct port 9000 access is blocked (should timeout/fail)
curl -I http://YOUR_SERVER_IP:9000/hooks/skim-deploy
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
sudo ufw status verbose
# or
sudo iptables -L -n | grep 443
```

## Update deployment branch

The webhook script currently deploys from a specific branch. To deploy from main branch instead:

```bash
sudo vim /opt/skim/deploy/webhook.sh
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

You now have secure automated GitOps deployments with HTTPS and IP restrictions. When you push to your main branch:

1. GitHub sends a webhook to your secure HTTPS endpoint
2. Nginx reverse proxy forwards to local webhook service
3. Webhook receiver verifies the signature
4. Deployment script runs automatically
5. Bot is rebuilt and restarted with new code

**Security features implemented:**
- HTTPS with Let's Encrypt SSL certificates
- Domain-based access (webhook.yourdomain.com)
- GitHub IP restrictions via firewall
- Nginx reverse proxy with security headers
- Internal-only webhook service (port 9000 not exposed)

Monitor deployments via logs and check bot status after deployments.
