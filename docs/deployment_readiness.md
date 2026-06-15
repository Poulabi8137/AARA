# Deployment Readiness Guide

## Overview

AARA can be deployed on several platforms. This guide covers the most common options.

---

## Option 1: Docker (Recommended)

### Backend

```bash
cd backend

# Production build
docker build -t aara-api:latest .

# Run with PostgreSQL + ChromaDB
docker compose up -d
```

### Environment Variables

```bash
# Required
SECRET_KEY=<64-char-random-string>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/aara

# Optional
OPENAI_API_KEY=<your-key>
GEMINI_API_KEY=<your-key>
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=<your-sentry-dsn>
ENV=production
LOG_LEVEL=WARNING
```

### Frontend

```bash
# Build
npm run build

# Environment
NEXT_PUBLIC_API_URL=https://api.aara.dev
JWT_SECRET=<same-as-backend-SECRET_KEY>

# Start
npm start
```

---

## Option 2: Render

### Backend (Web Service)

1. **Runtime**: Python 3.12
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Environment**:
   - `SECRET_KEY`: Required
   - `DATABASE_URL`: Render PostgreSQL
   - `ENV`: production

### Frontend (Static Site)

1. **Runtime**: Node 20
2. **Build Command**: `npm install && npm run build`
3. **Publish Directory**: `.next`
4. **Environment**:
   - `NEXT_PUBLIC_API_URL`: Backend URL
   - `JWT_SECRET`: Must match backend

---

## Option 3: Railway

### Backend

1. Connect GitHub repo
2. Root directory: `backend/`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add PostgreSQL plugin
5. Add Redis plugin (optional)

### Frontend

1. Root directory: `/`
2. Build command: `npm run build`
3. Start command: `npm start`

---

## Option 4: VPS (Ubuntu 22.04+)

### Backend Setup

```bash
# System dependencies
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql redis-server nginx

# Clone and setup
git clone https://github.com/your-org/aara.git
cd aara/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Database
sudo -u postgres createdb aara
sudo -u postgres psql -c "CREATE USER aara WITH PASSWORD 'secure-pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aara TO aara;"

# Run with systemd
# Create /etc/systemd/system/aara-api.service
cat > /etc/systemd/system/aara-api.service << EOF
[Unit]
Description=AARA API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/aara/backend
Environment=SECRET_KEY=<your-key>
Environment=DATABASE_URL=postgresql+asyncpg://aara:secure-pass@localhost:5432/aara
Environment=ENV=production
ExecStart=/home/ubuntu/aara/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable aara-api
sudo systemctl start aara-api
```

### Frontend Setup

```bash
# Build
cd /home/ubuntu/aara
npm install
npm run build

# Serve with nginx
cat > /etc/nginx/sites-available/aara << EOF
server {
    listen 80;
    server_name aara.dev;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/aara /etc/nginx/sites-enabled/
sudo nginx -s reload
```

---

## Production Checklist

### Security
- [ ] `SECRET_KEY` set to cryptographically random 64-char string
- [ ] `DATABASE_URL` uses strong, unique credentials
- [ ] HTTPS enabled via Let's Encrypt / Cloudflare
- [ ] CORS origins restricted to frontend domain
- [ ] Rate limiting configured with Redis
- [ ] JWT_SECRET matches backend SECRET_KEY

### Monitoring
- [ ] Sentry DSN configured for error tracking
- [ ] Prometheus metrics endpoint accessible
- [ ] Grafana dashboards imported
- [ ] Log aggregation configured (Loki / CloudWatch)

### Database
- [ ] Migrations run (alembic upgrade head)
- [ ] Automated backups configured
- [ ] Connection pooling limits set

### Performance
- [ ] Redis configured for caching + rate limiting
- [ ] Response compression enabled
- [ ] Static assets served via CDN
