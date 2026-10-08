# ConversX — Production Deployment Guide

## 1. Prerequisites

1. **Domain Names**:
   - Frontend: `conversx.com` (configured in DNS pointing to Vercel CNAME).
   - API Gateway: `api.conversx.com` (configured in DNS A-record pointing to Oracle Cloud VM public IP).
2. **Oracle Cloud VM**:
   - Ubuntu 22.04 LTS (A1 Compute / ARM64 or x86_64).
   - Docker Engine 26+ and Docker Compose v2.
   - Ports 80 and 443 open in OCI Security List.

---

## 2. Step-by-Step Backend Deployment (Oracle Cloud VM)

### Step 1: Clone Repository & Prepare Directory
```bash
sudo mkdir -p /opt/conversx
sudo chown -R $USER:$USER /opt/conversx
git clone https://github.com/anand/Conversx.git /opt/conversx
cd /opt/conversx
```

### Step 2: Configure Environment Variables
Copy and fill the production environment file:
```bash
cp .env.example .env
chmod 600 .env
```
Ensure required secrets are configured:
- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `APP_SECRET_KEY`
- `ADMIN_API_KEY`

### Step 3: Issue SSL Certificates via Certbot
```bash
# Start Nginx in HTTP-only challenge mode or use certbot standalone
docker compose -f infra/docker-compose.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
  -d api.conversx.com -d conversx.com \
  --email admin@conversx.com --agree-tos --no-eff-email" certbot
```

### Step 4: Run Database Migrations
```bash
docker compose -f infra/docker-compose.yml run --rm api alembic -c backend/alembic.ini upgrade head
```

### Step 5: Start Production Containers
```bash
docker compose -f infra/docker-compose.yml up -d
```

### Step 6: Verify Deployment
```bash
# Check container status
docker compose -f infra/docker-compose.yml ps

# Run readiness health probe
curl -fsS https://api.conversx.com/health

# Run automated smoke tests
docker compose -f infra/docker-compose.yml run --rm api pytest tests/production/smoke/ -v
```

---

## 3. Automated Certificate Renewal

Certbot automatically runs in the `conversx-certbot` background container every 12 hours:
- ACME challenge files are placed in `/var/www/certbot`.
- Certificates are updated in the shared volume `/etc/letsencrypt`.
- To trigger manual renewal:
  ```bash
  bash infra/scripts/renew_certificates.sh
  ```

---

## 4. Frontend Deployment (Vercel)

1. Connect the GitHub repository to Vercel.
2. Set Root Directory to `frontend`.
3. Configure Environment Variables in Vercel Dashboard:
   - `VITE_API_BASE_URL`: `https://api.conversx.com`
4. Deploy to Production.
