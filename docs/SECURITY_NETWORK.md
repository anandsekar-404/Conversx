# ConversX — Network Security & Firewall Hardening (Oracle Cloud VM)

## 1. Overview & Architecture

ConversX adopts a defense-in-depth network architecture. Public traffic from the Internet reaches **only** the Nginx reverse proxy on standard HTTP (80) and HTTPS (443) ports. All databases, caches, ML models, and internal application ports are isolated on private container networks and VM-level firewall rules.

```text
Internet
   │
   ├── (TCP 80, 443)  ──► Oracle VM [Nginx Reverse Proxy]
   │                             │ (conversx-internal bridge network)
   │                             ├──► FastAPI Gateway (api:8000)
   │                             │       ├──► PostgreSQL (postgres:5432 - INTERNAL ONLY)
   │                             │       ├──► Redis (redis:6379 - INTERNAL ONLY)
   │                             │       ├──► Whisper STT (In-process singleton)
   │                             │       └──► RQ Worker (worker - INTERNAL ONLY)
   │                             └──► Ollama LLM (ollama:11434 - INTERNAL ONLY)
   │
   └── (TCP 22) ──────► Oracle VM [OpenSSH - Trusted IP / Bastion Only]
```

---

## 2. Port Allocation & Exposure Rules

| Service | Port | Protocol | Public Access | Internal Access | Security Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HTTP (ACME Challenge / 301 Redirect)** | 80 | TCP | **ALLOWED** | Global | Redirects immediately to HTTPS; serves Let's Encrypt `.well-known/acme-challenge/`. |
| **HTTPS (Nginx Reverse Proxy)** | 443 | TCP | **ALLOWED** | Global | TLS 1.2/1.3 only, HSTS enabled, rate limited, CSP enforced. |
| **SSH Management** | 22 | TCP | **RESTRICTED** | Bastion / Admin IP | Key-based auth only, password auth disabled, fail2ban active. |
| **FastAPI Backend** | 8000 | TCP | **BLOCKED** | Internal (`127.0.0.1:8000` / Docker) | Only Nginx reverse proxy communicates with FastAPI. |
| **PostgreSQL Database** | 5432 | TCP | **BLOCKED** | Docker `conversx-internal` | Never bound to host 0.0.0.0; isolated on Docker network. |
| **Redis Broker** | 6379 | TCP | **BLOCKED** | Docker `conversx-internal` | Internal to Docker; password/AOF enabled. |
| **Prometheus Metrics** | 9090 | TCP | **BLOCKED** | Docker / `127.0.0.1:9090` | Public access to `/metrics` blocked via Nginx (403 Forbidden). |
| **Uptime Kuma Status** | 3001 | TCP | **BLOCKED** | `127.0.0.1:3001` | Accessible only via SSH tunnel or internal VPN. |
| **Ollama Local LLM** | 11434 | TCP | **BLOCKED** | Docker `conversx-internal` | Internal only. |

---

## 3. Oracle Cloud Infrastructure (OCI) Security Rules

In the OCI Console under **Virtual Cloud Network (VCN) ➔ Security Lists / Network Security Groups (NSGs)**:

### Ingress Rules (Stateful)
1. **HTTP Ingress**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port Range: `80`
   - Description: Allow ACME challenges and HTTP to HTTPS redirects.
2. **HTTPS Ingress**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port Range: `443`
   - Description: Production HTTPS traffic for api.conversx.com.
3. **SSH Ingress**:
   - Source CIDR: `<ADMIN_IP>/32` (or Bastion Subnet CIDR)
   - IP Protocol: TCP
   - Destination Port Range: `22`
   - Description: Administrative remote shell access.

### Egress Rules (Stateful)
- **All Outbound Traffic**:
  - Destination CIDR: `0.0.0.0/0`
  - IP Protocol: All Protocols
  - Description: Outbound access for package updates, ACME certificate renewal, and Firebase rule sync.

---

## 4. Host-Level Firewall Configuration (UFW on Ubuntu)

Run the following commands on the Oracle Cloud VM to configure and lock down UFW:

```bash
# 1. Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. Allow SSH (restrict to admin IP if static)
# Option A: Restrict to specific admin IP
sudo ufw allow from <YOUR_ADMIN_IP> to any port 22 proto tcp comment "Admin SSH access"

# Option B: General SSH with rate limiting
sudo ufw limit 22/tcp comment "Rate-limited SSH"

# 3. Allow Public HTTP & HTTPS for Nginx
sudo ufw allow 80/tcp comment "Nginx HTTP / ACME Challenge"
sudo ufw allow 443/tcp comment "Nginx HTTPS Production"

# 4. Verify Docker bypass protection
# Docker by default manipulates iptables directly. To ensure Docker containers
# respect UFW, add the DOCKER-USER chain rule:
sudo iptables -I DOCKER-USER -i eth0 ! -s 127.0.0.1 -p tcp --dport 5432 -j DROP
sudo iptables -I DOCKER-USER -i eth0 ! -s 127.0.0.1 -p tcp --dport 6379 -j DROP

# 5. Enable UFW
sudo ufw enable
sudo ufw status verbose
```

---

## 5. Docker Network Isolation

The Docker Compose configuration enforces network isolation:
1. All inter-service communication occurs across the `conversx-internal` bridge network.
2. `postgres` has **no published ports** (`ports:` is omitted); it listens strictly within the Docker network.
3. `redis` has **no published ports**; accessible only to `api` and `worker`.
4. `api` publishes only to `127.0.0.1:8000:8000`, preventing direct Internet traffic from bypassing Nginx.
5. `nginx` is the sole ingress container publishing ports `80` and `443` to `0.0.0.0`.
