# Cloud-Agnostic Deployment Guide

## Overview

VibePruner is designed to be deployed on any cloud platform (AWS, Azure, GCP, DigitalOcean) or on-premises without platform-specific dependencies. This guide outlines the deployment architecture and best practices.

## Core Principles

1. **No Cloud SDK Dependencies**: The core application doesn't import cloud-specific SDKs
2. **Environment-Based Configuration**: All cloud services configured via environment variables
3. **Standard Interfaces**: Use standard protocols (HTTP, SQL, S3-compatible APIs)
4. **Container-First**: Docker as the primary deployment mechanism
5. **Platform-Agnostic Storage**: Abstract file storage behind interfaces

## Architecture Components

### 1. Application Layer
```python
# No cloud-specific imports!
# ❌ import boto3
# ❌ from azure.storage import BlobServiceClient
# ❌ from google.cloud import storage

# ✅ Use abstractions
from storage_providers import StorageProvider
from config import get_storage_provider
```

### 2. Storage Abstraction
```python
class StorageProvider(ABC):
    """Abstract storage that works with any cloud"""
    
    @abstractmethod
    async def upload_file(self, key: str, content: bytes) -> str:
        pass
    
    @abstractmethod
    async def download_file(self, key: str) -> bytes:
        pass

# Implementations for each platform
class S3CompatibleStorage(StorageProvider):
    """Works with AWS S3, MinIO, DigitalOcean Spaces"""
    
class AzureBlobStorage(StorageProvider):
    """Azure Blob Storage implementation"""
    
class GCSStorage(StorageProvider):
    """Google Cloud Storage implementation"""
    
class LocalFileStorage(StorageProvider):
    """Local filesystem for development/on-premises"""
```

### 3. Configuration via Environment Variables
```bash
# Storage Configuration (platform-agnostic)
STORAGE_TYPE=s3              # s3, azure, gcs, local
STORAGE_ENDPOINT=            # Optional custom endpoint
STORAGE_BUCKET=vibepruner    # Bucket/container name
STORAGE_ACCESS_KEY=          # Access credentials
STORAGE_SECRET_KEY=          # Secret credentials
STORAGE_REGION=us-east-1     # Region if applicable

# Database Configuration (works anywhere)
DATABASE_URL=postgresql://user:pass@host:5432/vibepruner
# or
DATABASE_TYPE=sqlite
DATABASE_PATH=/data/vibepruner.db

# AI Provider Configuration (cloud-agnostic)
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Application Configuration
APP_ENV=production
APP_PORT=8080
APP_LOG_LEVEL=info
```

## Deployment Options

### 1. Docker Container (Universal)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run as non-root user
RUN useradd -m -u 1000 vibepruner && chown -R vibepruner:vibepruner /app
USER vibepruner

# Standard port
EXPOSE 8080

# Start application
CMD ["python", "vibepruner.py", "--web"]
```

### 2. Docker Compose (Development/Small Deployments)
```yaml
version: '3.8'

services:
  vibepruner:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/vibepruner
      - STORAGE_TYPE=local
      - STORAGE_PATH=/data/storage
    volumes:
      - ./data:/data
    depends_on:
      - db
  
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=vibepruner
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 3. Kubernetes (Any Cloud)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vibepruner
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vibepruner
  template:
    metadata:
      labels:
        app: vibepruner
    spec:
      containers:
      - name: vibepruner
        image: vibepruner:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: vibepruner-secrets
              key: database-url
        - name: STORAGE_TYPE
          value: "s3"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: vibepruner-service
spec:
  selector:
    app: vibepruner
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## Platform-Specific Deployment Examples

### AWS Deployment
```bash
# Using ECS Fargate (serverless containers)
aws ecs create-cluster --cluster-name vibepruner-cluster

# Deploy with environment variables
aws ecs run-task \
  --cluster vibepruner-cluster \
  --task-definition vibepruner:latest \
  --environment STORAGE_TYPE=s3,DATABASE_URL=$RDS_URL

# Or use Elastic Beanstalk for simplicity
eb init -p python-3.11 vibepruner
eb create production
eb setenv STORAGE_TYPE=s3 DATABASE_URL=$RDS_URL
```

### Azure Deployment
```bash
# Container Instances
az container create \
  --resource-group vibepruner-rg \
  --name vibepruner \
  --image vibepruner:latest \
  --cpu 1 --memory 1 \
  --environment-variables \
    STORAGE_TYPE=azure \
    DATABASE_URL=$AZURE_PG_URL

# Or App Service
az webapp create \
  --resource-group vibepruner-rg \
  --plan vibepruner-plan \
  --name vibepruner-app \
  --deployment-container-image-name vibepruner:latest
```

### Google Cloud Deployment
```bash
# Cloud Run (serverless)
gcloud run deploy vibepruner \
  --image gcr.io/project/vibepruner:latest \
  --platform managed \
  --set-env-vars STORAGE_TYPE=gcs,DATABASE_URL=$CLOUD_SQL_URL

# Or GKE
gcloud container clusters create vibepruner-cluster
kubectl apply -f k8s/
```

### DigitalOcean Deployment
```bash
# App Platform
doctl apps create --spec vibepruner-app.yaml

# vibepruner-app.yaml
name: vibepruner
services:
- name: web
  image:
    registry_type: DOCKER_HUB
    registry: vibepruner
    repository: vibepruner
    tag: latest
  instance_count: 2
  instance_size_slug: basic-xxs
  envs:
  - key: STORAGE_TYPE
    value: "s3"  # DO Spaces is S3-compatible
  - key: STORAGE_ENDPOINT
    value: "nyc3.digitaloceanspaces.com"
```

## Health Checks and Monitoring

### Standard Health Endpoint
```python
@app.route('/health')
def health_check():
    """Platform-agnostic health check"""
    return {
        'status': 'healthy',
        'version': APP_VERSION,
        'storage': check_storage_connection(),
        'database': check_database_connection(),
        'timestamp': datetime.utcnow().isoformat()
    }
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

# Logs work with any platform's log aggregation
logger.info("file_analyzed", 
    file_path=file_path,
    size_bytes=size,
    duration_ms=duration,
    ai_providers_used=providers
)
```

## Database Considerations

### Use Database URLs
```python
# Works with any SQL database
DATABASE_URL = os.getenv('DATABASE_URL')
# postgresql://user:pass@host/db
# mysql://user:pass@host/db
# sqlite:///path/to/db.sqlite
```

### Migration Strategy
```python
# Use platform-agnostic migration tools
from alembic import command
from alembic.config import Config

def run_migrations():
    """Run database migrations on any platform"""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

## Security Best Practices

1. **Never hardcode credentials** - Use environment variables
2. **Use least-privilege IAM** - Platform-specific but similar concepts
3. **Enable encryption** - At rest and in transit
4. **Regular updates** - Keep base images and dependencies updated
5. **Secret rotation** - Implement key rotation for all platforms

## Cost Optimization

### Universal Strategies
1. **Use spot/preemptible instances** where appropriate
2. **Auto-scaling based on load**
3. **Efficient container sizing**
4. **Cache AI responses** to reduce API costs
5. **Use object lifecycle policies** for storage

### Platform-Agnostic Monitoring
```python
# Use OpenTelemetry for vendor-neutral observability
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("analyze_file")
def analyze_file(file_path):
    # Traced across any platform
    pass
```

## Development to Production Path

1. **Local Development**
   ```bash
   docker-compose up
   # or
   python vibepruner.py --config config.dev.json
   ```

2. **CI/CD Pipeline** (GitHub Actions example)
   ```yaml
   - name: Build and push Docker image
     run: |
       docker build -t vibepruner:${{ github.sha }} .
       docker push $REGISTRY/vibepruner:${{ github.sha }}
   
   - name: Deploy to cloud
     run: |
       # Platform-specific deploy command
       # But app doesn't change!
   ```

3. **Production Deployment**
   - Same container everywhere
   - Only environment variables change
   - Platform-specific ingress/load balancer

## Troubleshooting

### Common Issues Across Platforms
1. **Container fails to start**: Check logs, ensure health endpoint responds
2. **Storage connection fails**: Verify credentials and endpoint configuration
3. **Out of memory**: Increase container memory limits
4. **Slow performance**: Check CPU limits and database connection pooling

### Debug Mode
```bash
# Enable debug logging on any platform
export APP_LOG_LEVEL=debug
export VERBOSE_AI_LOGGING=true
```

## Summary

VibePruner's cloud-agnostic design ensures:
- **Portability**: Deploy anywhere without code changes
- **Flexibility**: Switch clouds without vendor lock-in
- **Simplicity**: One codebase, multiple deployment targets
- **Cost-effective**: Choose the most economical platform
- **Future-proof**: New cloud providers just need environment configuration