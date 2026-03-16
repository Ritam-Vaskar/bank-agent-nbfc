# AWS EC2 + Docker Deployment Guide

This guide deploys the full stack (Frontend + Backend + MongoDB + Redis) on one EC2 instance using Docker Compose.

## 1) Launch EC2 Instance

- AMI: Ubuntu 22.04 LTS
- Instance type: `t3.medium` (recommended minimum)
- Storage: 20 GB+
- Security Group inbound rules:
  - `22` (SSH) from your IP
  - `3000` (Frontend) from your IP or `0.0.0.0/0`
  - `8000` (Backend API) from your IP or `0.0.0.0/0`
  - Optional (only if needed externally): `27017`, `6379`

## 2) SSH Into EC2

```bash
ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>
```

## 3) Install Docker + Compose Plugin

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

## 4) Clone Project

```bash
git clone <YOUR_REPO_URL> bank-agent
cd bank-agent
```

## 5) Configure Environment

Create backend env file:

```bash
cp backend/.env.example backend/.env 2>/dev/null || touch backend/.env
nano backend/.env
```

Set at least these variables in `backend/.env`:

```env
ENVIRONMENT=production
MONGODB_URI=mongodb://mongodb:27017/nbfc_loan_platform
REDIS_URL=redis://redis:6379
JWT_SECRET_KEY=<STRONG_SECRET>
GROQ_API_KEY=<YOUR_GROQ_API_KEY>
ENCRYPTION_KEY=<FERNET_KEY>
BACKEND_URL=http://<EC2_PUBLIC_IP>:8000
FRONTEND_URL=http://<EC2_PUBLIC_IP>:3000
CORS_ORIGINS=http://<EC2_PUBLIC_IP>:3000
```

Generate `ENCRYPTION_KEY` locally or on EC2:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 6) Build and Start (Production Compose)

For browser-to-backend URL in frontend build, export `NEXT_PUBLIC_API_URL` first:

```bash
export NEXT_PUBLIC_API_URL=http://<EC2_PUBLIC_IP>:8000
docker compose -f docker-compose.prod.yml up -d --build
```

## 7) Verify Deployment

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
curl http://localhost:8000/health
```

Open in browser:
- Frontend: `http://<EC2_PUBLIC_IP>:3000`
- API docs: `http://<EC2_PUBLIC_IP>:8000/docs`

## 8) Basic Operations

Restart:

```bash
docker compose -f docker-compose.prod.yml restart
```

Stop:

```bash
docker compose -f docker-compose.prod.yml down
```

Update after git pull:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## 9) Recommended Hardening (Next step)

- Put Nginx + TLS (Let’s Encrypt) in front of ports 3000/8000.
- Restrict Security Group inbound to only `80`/`443` publicly.
- Keep `27017` and `6379` closed to public internet.
- Enable automated backups for MongoDB volume.
