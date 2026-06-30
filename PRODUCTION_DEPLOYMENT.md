# ComplianceOS Production Deployment — www.polkorp.com

## 🌐 Production URLs

### Primary Domain
```
Website:         https://www.polkorp.com
Compliance Page: https://www.polkorp.com/compliance-assessment
HTML Embed:      https://www.polkorp.com/assets/compliance-os-embed.html
```

### API Endpoints
```
Base URL:        https://api.polkorp.com
Assess:          POST   https://api.polkorp.com/api/v1/agents/assess
Registry:        GET    https://api.polkorp.com/api/v1/agents/registry
Capabilities:    GET    https://api.polkorp.com/api/v1/agents/capabilities
Domains:         GET    https://api.polkorp.com/api/v1/agents/domains
Modules:         GET    https://api.polkorp.com/api/v1/agents/modules
```

## 🚀 Step-by-Step Deployment

### Phase 1: Backend Deployment

**1. Prepare Production Environment**
```bash
# On production server
git clone https://github.com/TheApostol/compliance-os.git
cd compliance-os

# Configure production secrets
cp .env.example .env.production
# Edit .env.production with:
# - NVIDIA_API_KEY (from build.nvidia.com)
# - DATABASE_URL (production PostgreSQL)
# - REDIS_URL (production Redis)
# - JWT_SECRET (generate: openssl rand -hex 32)
```

**2. Set Up Infrastructure**
```bash
# Option A: Docker Compose (Recommended)
docker-compose -f docker-compose.yml up -d

# Option B: Kubernetes
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Option C: Manual with systemd
systemctl start compliance-os-backend
```

**3. Database Migrations**
```bash
docker exec compliance-os-backend alembic upgrade head
# or
python -m alembic upgrade head
```

**4. Health Check**
```bash
curl -s https://api.polkorp.com/api/v1/agents/registry \
  -H "X-Tenant-Id: polkorp" | jq .total_agents
# Expected: 13
```

### Phase 2: Frontend Deployment

**1. Build Next.js App**
```bash
cd frontend
npm install
npm run build
npm start
```

Or deploy via Vercel:
```bash
vercel --prod
```

**2. Static HTML Embed**
```bash
# Copy HTML embed to web server
cp frontend/compliance-os-embed.html /var/www/polkorp/public/assets/

# Or serve via CDN
aws s3 cp frontend/compliance-os-embed.html s3://polkorp-cdn/compliance-os-embed.html
```

### Phase 3: Configuration

**1. Update HTML Embed API URL**

In `compliance-os-embed.html`, line 280:
```javascript
// Change from:
const API_URL = 'http://localhost:8000';

// To:
const API_URL = 'https://api.polkorp.com';
```

**2. Configure CORS**

In backend `app/core/config.py`:
```python
CORS_ORIGINS = [
    "https://www.polkorp.com",
    "https://polkorp.com",
    "https://api.polkorp.com",
    "https://compliance.polkorp.com",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-Tenant-Id"]
```

**3. Configure TLS/HTTPS**

```nginx
# Nginx config for api.polkorp.com
server {
    listen 443 ssl http2;
    server_name api.polkorp.com;
    
    ssl_certificate /etc/letsencrypt/live/polkorp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/polkorp.com/privkey.pem;
    
    location /api/v1/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

**4. Environment Variables**

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false

# API Config
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE="ComplianceOS"

# Database
DATABASE_URL=postgresql://user:pass@prod-db.polkorp.com:5432/compliance_os
DB_POOL_SIZE=20
DB_POOL_OVERFLOW=10

# Cache
REDIS_URL=redis://prod-redis.polkorp.com:6379/0

# AI Providers (40 RPM limit)
NVIDIA_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# Audit & Security
JWT_SECRET=your_secret_here (generate: openssl rand -hex 32)
LOG_LEVEL=info
SENTRY_DSN=https://...@sentry.io/...  # Optional

# Tenant Config
DEFAULT_TENANT_ID=polkorp
TENANT_CACHE_TTL=3600
```

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  www.polkorp.com                            │
│  (Polkorp Marketing Site)                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
    ┌──────────────────┐   ┌──────────────────┐
    │ Compliance Page  │   │  HTML Embed      │
    │ (Next.js Router) │   │  (Static HTML)   │
    └──────────────────┘   └──────────────────┘
                │           │
                └───────────┼───────────┐
                            │
            ┌───────────────────────────┐
            │   api.polkorp.com         │
            │  (ComplianceOS Backend)   │
            │  - 13 Agents              │
            │  - Rate Limiter (40 RPM)  │
            │  - Multi-tenant isolation │
            └───────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌────────┐  ┌────────┐  ┌────────┐
    │ Qdrant │  │ PostgreSQL │ Redis  │
    │(Vectors)  │(Data)      │(Cache) │
    └────────┘  └────────┘  └────────┘
```

## 🔒 Security Checklist

- [ ] **HTTPS/TLS**: All traffic over HTTPS (SSL certificate from Let's Encrypt)
- [ ] **CORS**: Restricted to polkorp.com domains only
- [ ] **Authentication**: JWT tokens stored securely in httpOnly cookies
- [ ] **Authorization**: X-Tenant-Id header validated for multi-tenant isolation
- [ ] **Rate Limiting**: 40 RPM per tenant enforced
- [ ] **Database**: Encrypted connections, credentials in .env only
- [ ] **Secrets**: No hardcoded keys, use environment variables
- [ ] **Logging**: Audit trail for all compliance assessments
- [ ] **Monitoring**: Sentry alerts for errors, DataDog for metrics
- [ ] **Backups**: Daily database backups to S3

## 📈 Performance Optimization

### Database
```sql
-- Index for common queries
CREATE INDEX idx_tenant_id ON failure_modes(tenant_id);
CREATE INDEX idx_entity_assessments ON assessments(tenant_id, entity_id);
CREATE INDEX idx_audit_log_tenant ON audit_log(tenant_id, created_at);
```

### Caching
```python
# Cache common queries in Redis
CACHE_TTL_REGULATIONS = 86400  # 24 hours
CACHE_TTL_JURISDICTIONS = 604800  # 7 days
CACHE_TTL_AGENT_REGISTRY = 3600  # 1 hour
```

### CDN
```bash
# Serve static assets via CDN
# compliance-os-embed.html → CloudFront/Cloudflare
# Frontend assets → CDN for global delivery
```

## 📊 Monitoring & Alerts

### Metrics to Track
```
- API response time (target: < 5s for assessments)
- Agent execution latency (target: < 30s)
- Rate limiter: requests/minute (max 40)
- Database connection pool usage
- Vector DB query latency
- Error rate (target: < 0.1%)
- JWT token expiration/refresh rate
```

### Alerts
```yaml
# Sentry
- Alert on: HTTP 5xx errors
- Alert on: Rate limiter exhaustion (429 responses)
- Alert on: Database connection pool exhausted

# CloudWatch / DataDog
- Alert on: API latency > 10s
- Alert on: Agent execution timeout (180s)
- Alert on: Redis connection failures
```

## 🚀 Deployment Checklist

**Pre-Deployment (1 week before)**
- [ ] Review security & compliance requirements
- [ ] Set up production infrastructure (servers, databases, CDN)
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring (Sentry, DataDog, CloudWatch)
- [ ] Load test backend API (100 concurrent requests)
- [ ] Test failover/redundancy
- [ ] Create runbooks for common issues

**Day Before**
- [ ] Final code review of all commits
- [ ] Backup production databases
- [ ] Notify stakeholders of deployment window
- [ ] Brief on-call team on new system

**Deployment Day**
- [ ] [ ] 1. Deploy backend API (blue-green deployment)
- [ ] [ ] 2. Run database migrations
- [ ] [ ] 3. Health check API endpoints
- [ ] [ ] 4. Deploy frontend (Next.js build)
- [ ] [ ] 5. Serve HTML embed from CDN
- [ ] [ ] 6. Update DNS if needed
- [ ] [ ] 7. Test end-to-end flow
- [ ] [ ] 8. Update Polkorp navigation links
- [ ] [ ] 9. Announce to customers
- [ ] [ ] 10. Monitor logs for 24h

**Post-Deployment**
- [ ] Monitor error rates hourly (first 24h)
- [ ] Check API response times
- [ ] Verify rate limiter is working
- [ ] Test multi-tenant isolation
- [ ] Review audit logs
- [ ] Collect customer feedback
- [ ] Document any issues & resolutions

## 📞 Support & Runbooks

### Issue: Assessment timeout (>30s)
```
Cause: Slow AI model or network latency
Fix:
1. Check NVIDIA API status at build.nvidia.com
2. Verify backend logs: docker logs compliance-os-backend
3. Check database query performance
4. Scale up resources if needed
```

### Issue: Rate limiter returning 429
```
Cause: Tenant exceeded 40 RPM budget
Fix:
1. Check rate limiter metrics in CloudWatch
2. Spread requests over time (batch assessments)
3. Consider increasing budget if legitimate usage
4. Monitor for abuse patterns
```

### Issue: CORS errors on frontend
```
Cause: Frontend domain not in CORS_ORIGINS
Fix:
1. Update app/core/config.py CORS_ORIGINS
2. Restart backend: docker-compose restart backend
3. Clear browser cache
4. Verify curl works: curl -H "Origin: ..." https://api.polkorp.com/...
```

## 🎯 Production Features

✅ **Multi-tenant isolation** — Each tenant's data is isolated
✅ **Rate limiting** — 40 RPM per tenant, priority queue for interactive requests
✅ **Circuit breaker** — Automatic fallback: NVIDIA → Anthropic → OpenRouter
✅ **Data residency** — Respect tenant's provider constraints
✅ **Audit logging** — Hash-chain tamper detection
✅ **JWT authentication** — Secure token-based auth
✅ **HTTPS/TLS** — End-to-end encryption
✅ **Database backups** — Daily snapshots to S3
✅ **Monitoring** — Real-time alerts for errors & performance

## 📚 Documentation Files

- `API_GUIDE.md` — 600+ lines of API documentation
- `ARCHITECTURE.md` — Agent framework architecture
- `POLKORP_INTEGRATION.md` — Integration guide
- `CLAUDE.md` — Project context & coding standards
- This file — Production deployment guide

## 🔗 Links

- **GitHub**: https://github.com/TheApostol/compliance-os
- **Main Site**: https://www.polkorp.com
- **API Docs**: https://api.polkorp.com/docs (Swagger)
- **Status**: https://status.polkorp.com (uptime monitoring)

---

**ComplianceOS Production Deployment v1.0**  
Ready for www.polkorp.com
