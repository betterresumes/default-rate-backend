# Environment Configuration

Core application variables
- DATABASE_URL: PostgreSQL connection string (required)
- REDIS_URL: Redis connection for cache/rate-limit/celery (recommended)
- ENVIRONMENT: development | staging | production
- DEBUG: true|false
- SECRET_KEY: app secret (secure in prod)
- JWT_SECRET_KEY: JWT signing secret (required)
- AWS_REGION: AWS region (e.g., us-east-1)

Optional
- CORS_ORIGIN: frontend origin for CORS
- PORT: container/app port (default 8000)
- WORKERS: gunicorn workers (prod; default 4)

Storage of secrets
- Production: use AWS SSM Parameter Store (recommended)
- Alternative: AWS Secrets Manager

Notes
- App reads DATABASE_URL directly; DB_HOST/DB_USER/DB_PASS are not used unless you build DATABASE_URL from them.
- Rate limiting falls back to in-memory if REDIS_URL is missing.
