# Aegis — Deployment Guide

## Prerequisites

- A VPS running Ubuntu 22.04 (Hetzner, DigitalOcean, or Vultr recommended)
- A domain name pointed to Cloudflare nameservers
- A Cloudflare account (free tier is fine to start)
- Docker and Docker Compose installed on the VPS
- WSL2 or Linux on your development machine

---

## Step 1 — Server Initial Hardening

```bash
# SSH in as root first time
ssh root@YOUR_VPS_IP

# Create app user
adduser aegisuser
usermod -aG sudo aegisuser

# Harden SSH
nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no
systemctl restart sshd

# Basic firewall — allow SSH temporarily until tunnel is running
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw enable
```

---

## Step 2 — Install Docker

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker aegisuser
```

---

## Step 3 — Generate Journalist Keypair

**Do this on your local machine, ideally air-gapped.**

```bash
pip install cryptography
python scripts/keygen.py --output-dir ./keys
```

Copy **only** `journalist_public.pem` to the server:

```bash
scp keys/journalist_public.pem aegisuser@YOUR_VPS_IP:~/aegis/backend/keys/
```

Store `journalist_private.pem` on an **encrypted USB drive** and delete it from your local machine.

---

## Step 4 — Deploy the Backend

```bash
# On VPS
git clone https://github.com/yourusername/aegis.git
cd aegis
cp .env.example .env
nano .env  # Set your domain and any other values

docker-compose up -d
docker-compose logs -f  # Verify it started cleanly
```

Test locally on the VPS:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## Step 5 — Set Up Cloudflare Tunnel

```bash
bash scripts/setup.sh yourdomain.com
```

This will:
1. Install `cloudflared`
2. Authenticate with your Cloudflare account
3. Create the tunnel and DNS routes
4. Install it as a systemd service
5. Lock the firewall (removes all inbound rules)

After this step, your server has **no open inbound ports**. All traffic flows through the tunnel.

---

## Step 6 — Deploy the Cloudflare Worker

```bash
# On your local machine
cd worker
npm install -g wrangler

# Edit wrangler.toml — set your zone and domain
wrangler login
wrangler deploy
```

---

## Step 7 — Cloudflare Access (Admin Panel)

In the Cloudflare Zero Trust dashboard:

1. Go to **Access → Applications → Add Application**
2. Choose **Self-hosted**
3. Set subdomain: `admin.yourdomain.com`
4. Create a policy:
   - Rule: **Allow**
   - Require: **Emails ending in** `@yourorg.com`
   - Require: **Authentication method** → Hardware key (FIDO2)

For SSH access via Access:

```bash
# On your local machine, add to ~/.ssh/config
Host admin.yourdomain.com
  ProxyCommand cloudflared access ssh --hostname admin.yourdomain.com
```

---

## Step 8 — Apply for Project Galileo

Go to [cloudflare.com/galileo](https://www.cloudflare.com/galileo/) and apply.

This gives you:
- Unmetered DDoS mitigation
- Enterprise WAF
- Free for eligible journalism and civil society orgs

---

## Step 9 — Verification Checklist

```
[ ] curl https://submit.yourdomain.com/health returns {"status":"ok"}
[ ] Submitting a test message works end-to-end
[ ] Decrypting with journalist_private.pem works locally (scripts/decrypt.py)
[ ] Admin panel requires Cloudflare Access authentication
[ ] No open inbound ports on VPS (sudo ufw status)
[ ] cloudflared service is running (systemctl status cloudflared)
[ ] Logpush disabled for the zone in Cloudflare dashboard
[ ] Project Galileo application submitted
```
