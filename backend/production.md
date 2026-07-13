# Production Deployment Guide

This document explains how to deploy the AARA API to production using environment variables injected by your deployment platform.

## Environment Variables

All production configuration should be handled through environment variables injected by your deployment platform. Never commit secrets to the repository.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Strong secret key for JWT signing (minimum 32 characters) | `nXJ9kL2pR5vW8mQ7tY1bN4xZ6cD3fH8gJ2qR5vW9xZ1cD4fH7jM0nQ3rT6vW9xZ2c` |
| `DATABASE_URL` | Production PostgreSQL connection string | `postgresql+asyncpg://[user]:[pass]@[host]:[port]/[db]` |
| `ALLOWED_ORIGINS` | CORS allowed domains for production | `["https://app.yourdomain.com", "https://api.yourdomain.com"]` |

### Optional Variables

| Variable | Description | Default | Environment Variable |
|----------|-------------|---------|----------------------|
| `LLM_PROVIDER` | LLM provider choice | `mock` | `LLM_PROVIDER=openai` |
| `LLM_MODEL` | Model name for chosen provider | `gpt-4o` | `LLM_MODEL=gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key | empty | `OPENAI_API_KEY=sk-...` |
| `GEMINI_API_KEY` | Gemini API key | empty | `GEMINI_API_KEY=AI...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | empty | `ANTHROPIC_API_KEY=sk-...` |
| `REDIS_URL` | Redis connection URL | `memory` | `REDIS_URL=[redis-url]` |
| `SENTRY_DSN` | Sentry DSN for error tracking | empty | `SENTRY_DSN=https://...` |
| `ENV` | Environment name | `development` | `ENV=production` |

## Deployment Platforms

### Docker Compose

```yaml
docker-compose.production.yml:
dervices:
  app:
    build: .
    env_file: ./.env.production
    environment:
      # Example: Inject secrets from deployment platform
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_URL: ${DATABASE_URL}
      ALLOWED_ORIGINS: '["https://app.yourdomain.com"]'
    ports:
      - "8000:8000"
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aara-api
spec:
  template:
    spec:
      containers:
      - name: app
        image: aara/api:latest
        envFrom:
        - secretRef:
            name: aara-secrets
        env:
        - name: ALLOWED_ORIGINS
          value: '["https://app.yourdomain.com", "https://api.yourdomain.com"]'
        - name: ENV
          value: "production"
```

Create the secret:
```bash
kubectl create secret generic aara-secrets \
  --from-literal=SECRET_KEY="[strong_random_secret]" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://[user]:[pass]@[host]:[port]/[db]" \
  --from-literal=OPENAI_API_KEY="sk-..." \
  --from-literal=GEMINI_API_KEY="AI..."
```

### Terraform

```hcl
resource "aws_ecs_task_definition" "aara" {
  family = "aara-api"
  
  container_definitions = jsonencode([
    {
      name  = "app"
      image = "aara/api:latest"
      
      essential = true
      
      environment = [
        { name = "SECRET_KEY", value = var.secret_key },
        { name = "DATABASE_URL", value = var.database_url },
        { name = "ALLOWED_ORIGINS", value = "[\"https://app.yourdomain.com\", \"https://api.yourdomain.com\"]" },
        { name = "ENV", value = "production" }
      ]
      
      # Mount secrets from AWS Secrets Manager
      secrets = [
        { name = "OPENAI_API_KEY", valueFrom = aws_secretsmanager_secret_version.openai.arn },
        { name = "GEMINI_API_KEY", valueFrom = aws_secretsmanager_secret_version.gemini.arn }
      ]
    }
  ])
}
```

## Secret Management

### AWS Secrets Manager

```bash
# Store secrets securely
aws secretsmanager create-secret --name aara/production --secret-string '{"SECRET_KEY":"...","DATABASE_URL":"...","OPENAI_API_KEY":"...","GEMINI_API_KEY":"..."}'

# Reference in ECS/Task Definition
aws ecs update-service --cluster aara --service aara-api --task-definition aara-api --force-new-deployment
```

### Docker Secrets

```bash
# Create secrets (requires Docker swarm or Compose v2)
docker secret create aara_secret_key echo "[strong_random_secret]" > aara_secret_key
docker secret create aara_database_url echo "postgresql+asyncpg://[user]:[pass]@[host]:[port]/[db]" > aara_database_url

# Reference in docker-compose.yml
version: '3.8'
services:
  app:
    secrets:
      - aara_secret_key
      - aara_database_url
    
secrets:
  aara_secret_key:
    external: true
  aara_database_url:
    external: true
```

## Configuration Security

### Security Checklist

- ✅ All secrets use environment variables or secret managers
- ✅ No secrets in source code or configuration files
- ✅ Strong secret keys (32+ characters)
- ✅ Production secrets injected at deployment time
- ✅ Environment-specific configurations (dev/staging/prod)
- ✅ Access controls for secret management

### Example Production Workflow

1. **Development:** Use `.env.example` with local development values
2. **Testing:** Use CI/CD pipeline with test secrets
3. **Staging:** Copy production secrets to staging environment
4. **Production:** Use deployment platform's secret injection mechanism

```bash
# Development
cp .env.example .env
# Edit .env for local development

# CI/CD Pipeline (example)
export SECRET_KEY=$CI_SECRET_KEY
export DATABASE_URL=$CI_DATABASE_URL
export ALLOWED_ORIGINS='["https://staging.app.example.com"]'
export ENV=staging

# Production (Kubernetes)
export SECRET_KEY=$(kubectl get secret aara-secrets -o jsonpath='{.data.SECRET_KEY}' | base64 --decode)
export DATABASE_URL=$(kubectl get secret aara-secrets -o jsonpath='{.data.DATABASE_URL}' | base64 --decode)
export ALLOWED_ORIGINS='["https://app.example.com", "https://api.example.com"]'
export ENV=production
```

## Monitoring Configuration

### Production Monitoring Variables

- `PROMETHEUS_METRICS_ENABLED=true` - Enable Prometheus metrics
- `SENTRY_DSN=[sentry_dsn]` - Error tracking
- `LOG_LEVEL=INFO` - Logging level
- `METRICS_PORT=9090` - Metrics server port

### Example Production Environment File

```bash
# File: .env.production (never commit to git!)
SECRET_KEY=[injected_by_deployment_platform]
DATABASE_URL=[injected_by_deployment_platform]
ALLOWED_ORIGINS=["https://app.yourdomain.com", "https://api.yourdomain.com"]
LLM_PROVIDER=openai
OPENAI_API_KEY=[injected_by_deployment_platform]
GEMINI_API_KEY=[injected_by_deployment_platform]
REDIS_URL=[injected_by_deployment_platform]
SENTRY_DSN=[injected_by_deployment_platform]
ENV=production
PROMETHEUS_METRICS_ENABLED=true
LOG_LEVEL=INFO
```

## Best Practices

1. **Never hardcode secrets** in any configuration files
2. **Use deployment platform's secret management** (Kubernetes secrets, AWS Secrets Manager, etc.)
3. **Enable secret rotation** mechanisms
4. **Use different environments** for development, testing, and production
5. **Audit secret access** and rotation regularly
6. **Enable logging** for secret access (without logging secret values)
7. **Use least privilege** access for secret management

## Troubleshooting

### Common Issues

**Environment Variable Not Found**
```bash
# Check if environment variable exists
env | grep SECRET_KEY
# Set environment variable
export SECRET_KEY="[your-secret]"
```

**Database Connection Issues**
```bash
# Check database connection
psql "[database_url]" -c "SELECT 1;"

# Verify connection string
DATABASE_URL=[your-database-url]
echo $DATABASE_URL
```

**JWT Token Issues**
```bash
# Check JWT signing
SECRET_KEY=[your-secret-key]
echo $SECRET_KEY | wc -c  # Should be 32+ characters
```

## Rollback Procedure

If you need to rollback to a previous configuration:

```bash
# Restore previous .env file
cp .env.backup .env

# Reapply production secrets from backup
# (secrets should be re-injected by deployment platform)
```

## Contact

For deployment questions or issues, contact the development team.
