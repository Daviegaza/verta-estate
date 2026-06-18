# ═══════════════════════════════════════════════════════════════════════════════
# VESTRA — Production Deployment Guide
# ═══════════════════════════════════════════════════════════════════════════════
#
# VESTRA is an AI-Powered Property Trust & Operating System for Africa.
# This guide covers deployment to any environment: bare metal, VPS, cloud VM,
# Kubernetes, Docker Compose, or managed cloud platforms.
# ═══════════════════════════════════════════════════════════════════════════════

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM REQUIREMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MINIMUM (up to 1,000 daily active users):
  - CPU: 2 vCPUs (x86_64 or ARM64)
  - RAM: 4 GB
  - Storage: 40 GB SSD
  - OS: Ubuntu 22.04+ / Debian 12+ / RHEL 9+
  - Docker Engine 24+ & Docker Compose v2
  - Public IP with ports 80/443 open

RECOMMENDED (up to 10,000 daily active users):
  - CPU: 4 vCPUs
  - RAM: 8 GB
  - Storage: 100 GB NVMe SSD
  - OS: Ubuntu 24.04 LTS
  - Docker Engine 26+ & Docker Compose v2
  - SSL certificate (LetsEncrypt or paid)

ENTERPRISE (unlimited scale):
  - Kubernetes cluster (GKE / EKS / AKS)
  - Horizontal Pod Autoscaling
  - Multi-AZ database with read replicas
  - Redis Cluster with sentinel
  - Object storage (S3 / GCS) for uploads
  - WAF + DDoS protection

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUICK DEPLOY OPTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Platform | What It Deploys | Best For | Method |
|----------|----------------|----------|--------|
| **Docker (VPS)** | Full stack + monitoring | Full control, Kenya-hosted | `docker compose up -d` |
| **Fly.io** | Backend API | Global edge, Africa regions | `fly deploy` |
| **Render** | Full stack | Easiest setup | Connect repo |
| **Railway** | Backend API | Startups, scale-to-zero | Connect repo |
| **Vercel** | Frontend only | Fast CDN | `vercel --prod` |
| **Kubernetes** | Everything | Enterprise scale | `kubectl apply -f k8s/` |

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOCKER COMPOSE — RECOMMENDED SELF-HOSTED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

12 services deployed automatically:
  postgres, redis, backend, frontend, nginx, prometheus,
  grafana, alertmanager, node-exporter, redis-exporter,
  postgres-exporter, flower

1. CLONE & CONFIGURE
   ```bash
   git clone https://github.com/your-org/vestra.git /opt/vestra
   cd /opt/vestra
   cp .env.production .env
   # EDIT .env — fill in ALL secrets:
   #   POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY (64 chars)
   #   MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET
   #   SMTP_HOST, SMTP_USER, SMTP_PASSWORD
   #   GRAFANA_ADMIN_PASSWORD
   nano .env
   ```

2. SSL (LetsEncrypt)
   ```bash
   sudo certbot certonly --standalone -d vestra.co.ke -d monitoring.vestra.co.ke
   sudo cp /etc/letsencrypt/live/vestra.co.ke/fullchain.pem nginx/ssl/
   sudo cp /etc/letsencrypt/live/vestra.co.ke/privkey.pem nginx/ssl/
   # Uncomment HTTPS section in nginx/conf.d/default.conf
   ```

3. START
   ```bash
   docker compose up -d
   docker compose ps  # verify all 12 services are "healthy" or "running"
   ```

4. MIGRATE & VERIFY
   ```bash
   docker compose exec backend alembic upgrade head
   curl -s https://vestra.co.ke/health | jq
   # → {"status":"healthy","database":"connected","redis":"connected"}
   ```

5. SEED (optional demo data)
   ```bash
   docker compose exec backend python seed.py
   # Demo creds: admin@vestra.co.ke / demo1234
   ```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONITORING STACK (built-in)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Backend     │────▶│  Prometheus   │────▶│   Grafana     │
  │  /metrics    │     │  (30d data)   │     │  (dashboards) │
  └─────────────┘     └──────┬───────┘     └──────────────┘
                             │
                    ┌────────▼───────┐
                    │  Alertmanager   │
                    │  → email/Slack  │
                    └────────────────┘

URLs (after deployment):
  - App:         https://vestra.co.ke
  - Grafana:     https://monitoring.vestra.co.ke  (admin / $GRAFANA_ADMIN_PASSWORD)
  - In-App:      https://vestra.co.ke/admin/monitoring
  - Prometheus:  https://vestra.co.ke/prometheus/  (internal IPs only)
  - Alerts:      https://vestra.co.ke/alertmanager/ (internal IPs only)
  - Flower:      https://vestra.co.ke/flower/       (internal IPs only)

ALERTS CONFIGURED:
  CRITICAL → API down, DB down, Redis down (oncall@vestra.co.ke)
  WARNING  → High latency, error rate >5%, memory >90% (engineering@vestra.co.ke)
  BUSINESS → Fraud spikes, payment failures (product@vestra.co.ke)

PRE-BUILT GRAFANA DASHBOARD:
  "Vestra System Overview" — services health, API throughput/latency,
  business metrics, host resources, database connections, Redis cache stats

BUILT-IN MONITORING DASHBOARD (in-app):
  /admin/monitoring — real-time health, DB metrics, Redis metrics,
  business KPIs, auto-refresh every 10 seconds

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLOUD PLATFORM DEPLOYMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AWS (ECS Fargate + RDS + ElastiCache)
  - GitHub Actions pushes to ECR
  - RDS PostgreSQL, ElastiCache Redis
  - ALB for load balancing, CloudWatch for logs
  - S3 for uploads

Google Cloud (Cloud Run + Cloud SQL)
  - Cloud Run for serverless containers
  - Cloud SQL PostgreSQL, Memorystore Redis
  - Cloud CDN, Cloud Storage for uploads
  - Cloud Monitoring for observability

Azure (Container Apps + Flexible Server)
  - Container Apps for backend/frontend
  - PostgreSQL Flexible Server, Azure Cache for Redis
  - Azure CDN, Blob Storage for uploads
  - Application Insights for monitoring

DigitalOcean (Droplet / App Platform)
  - Single Droplet: Follow Docker Compose guide above
  - App Platform: Deploy backend and frontend as separate apps
  - Managed Database, Managed Redis, Spaces for uploads

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KUBERNETES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```bash
kubectl create namespace vestra
kubectl create secret generic vestra-secrets \
  --from-literal=secret-key=$(openssl rand -base64 64) \
  --from-literal=postgres-password=<password> \
  --from-literal=redis-password=<password>
kubectl apply -f k8s/
kubectl autoscale deployment vestra-backend --cpu-percent=70 --min=2 --max=10
```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MOBILE (iOS + Android — PWA)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vestra is a PWA — no separate codebase needed:
  - iOS: Users visit in Safari → Share → "Add to Home Screen"
  - Android: Chrome auto-prompts "Install app"
  - App Store / Play Store: Use PWABuilder to wrap in native shell

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WHATSAPP BUSINESS API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Create Meta Business Account at business.facebook.com
2. Create WhatsApp Business App at developers.facebook.com
3. Set webhook: https://your-domain.com/api/whatsapp/webhook
4. Configure env: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, etc.
5. Create message templates in WhatsApp Business Manager

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PERFORMANCE TUNING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POSTGRESQL: shared_buffers = 25% RAM, effective_cache_size = 75% RAM
REDIS: maxmemory = 75% RAM, allkeys-lru policy, AOF with everysec
BACKEND: GUNICORN_WORKERS = (2 × vCPUs) + 1, DATABASE_POOL_SIZE = 20
NGINX: worker_processes = auto, gzip on, keepalive 32 to backend

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCALING FOR MILLIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Layer | Current | 100K Users | 1M Users | 10M Users |
|-------|---------|------------|----------|-----------|
| API Servers | 4 workers | 8 workers | 16 workers | 32+ workers |
| Database | 1 node | 4GB + replica | 16GB + replicas | Sharded cluster |
| Redis | 256MB | 512MB | 1GB | 2GB + sentinel |
| CDN | Local | Cloudflare | Cloudflare + S3 | Multi-CDN |

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY CHECKLIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ Change ALL default passwords
☐ Enable HTTPS with valid SSL certificate
☐ Firewall: only ports 80/443 open
☐ CORS_ORIGINS set to specific domains
☐ IP-whitelist /metrics, /docs, /grafana/
☐ Run containers as non-root (configured)
☐ Rate limit auth: 10/min per IP
☐ SECRET_KEY: 64+ random characters
☐ Enable database SSL/TLS
☐ Regular security scanning
☐ Set up WAF (Cloudflare)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKUP STRATEGY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATABASE (daily crontab):
  docker compose exec -T postgres pg_dump -U postgres vestra | gzip > /backups/vestra_$(date +%Y%m%d).sql.gz
  Retention: 7 daily, 4 weekly, 12 monthly

REDIS: AOF + RDB persistence built-in
UPLOADS: Sync to S3/GCS daily

DISASTER RECOVERY:
  1. Restore: gunzip -c vestra_YYYYMMDD.sql.gz | docker compose exec -T postgres psql -U postgres vestra
  2. Start: docker compose up -d
  3. Migrate: docker compose exec backend alembic upgrade head
  4. Verify: curl https://vestra.co.ke/health

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TROUBLESHOOTING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SERVICE WON'T START:
  docker compose logs <service> --tail=100

DATABASE ISSUES:
  docker compose exec postgres pg_isready -U postgres -d vestra
  curl http://localhost:8000/api/monitoring/health/database | jq

HIGH LATENCY:
  1. Check DB slow queries
  2. Check Redis hit rate: curl /api/monitoring/health/redis | jq
  3. Scale GUNICORN_WORKERS

MONITORING DOWN:
  curl http://localhost:9090/api/v1/targets | jq
  curl http://localhost:3001/api/health

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAINTENANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WEEKLY: Review dashboards, check disk, review error logs
MONTHLY: OS patches, Docker pull, VACUUM ANALYZE, rotate keys, test backup
QUARTERLY: Security audit, update rate limits, capacity planning, DR drill

# ═══════════════════════════════════════════════════════════════════════════════
# SUPPORT
# ═══════════════════════════════════════════════════════════════════════════════

Docs: https://docs.vestra.co.ke | API: https://vestra.co.ke/docs
Monitoring: https://monitoring.vestra.co.ke | Support: support@vestra.co.ke
