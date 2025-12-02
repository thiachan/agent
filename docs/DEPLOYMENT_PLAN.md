# AWS EC2 Deployment & Scalability Plan

## 1. Operating System Recommendation

**Recommended: Ubuntu 22.04 LTS (Jammy Jellyfish)**

**Rationale:**
- Long-term support until 2027
- Excellent Python 3.10+ and Node.js 18+ support
- Well-documented for Docker and production deployments
- Strong AWS EC2 integration and AMI availability
- Active security updates and patches
- Minimal resource overhead

**Alternative:** Amazon Linux 2023 (if you prefer AWS-native OS)

---

## 2. Architecture Overview

### Current State (Single Server)
- FastAPI backend (single process)
- Next.js frontend (single process)
- SQLite database (file-based, not scalable)
- ChromaDB (local file-based, not scalable)
- Local file storage

### Target State (Scalable)
- **Load Balancer:** Nginx reverse proxy
- **Backend:** Multiple FastAPI containers (horizontal scaling)
- **Frontend:** Next.js static export or containerized
- **Database:** PostgreSQL (RDS or self-hosted)
- **Vector DB:** ChromaDB server mode or managed service
- **Cache:** Redis for session/query caching
- **Storage:** S3 for file uploads
- **Monitoring:** CloudWatch or Prometheus

---

## 3. Infrastructure Components

### 3.1 EC2 Instance Sizing (Budget-Optimized)

**Option A: Single Large Instance (Initial)**
- **Instance Type:** `t3.xlarge` or `t3.2xlarge`
- **Specs:** 4-8 vCPU, 16-32 GB RAM
- **Cost:** ~$120-240/month
- **Use Case:** Start here, scale horizontally when needed

**Option B: Multiple Smaller Instances (Recommended for 200+ users)**
- **App Servers:** 2x `t3.large` (2 vCPU, 8GB RAM each) = ~$120/month
- **Database:** 1x `db.t3.medium` RDS PostgreSQL = ~$60/month
- **Cache:** 1x `cache.t3.micro` ElastiCache Redis = ~$15/month
- **Load Balancer:** Application Load Balancer = ~$20/month
- **S3 Storage:** ~$10/month (for uploads)
- **Total:** ~$225/month (well under $500 budget)

### 3.2 Database Migration: SQLite → PostgreSQL

**Why PostgreSQL:**
- Concurrent connection support (SQLite limited to 1 writer)
- Better performance under load
- ACID compliance for production
- Connection pooling support
- Backup and replication capabilities

**Migration Steps:**
1. Install PostgreSQL on EC2 or use RDS
2. Update `DATABASE_URL` in `backend/.env`
3. Run Alembic migrations (create new migration system)
4. Data migration script to transfer existing data
5. Update connection pooling in `backend/app/core/database.py`

**Files to Modify:**
- `backend/app/core/database.py` - Add connection pooling
- `backend/app/core/config.py` - Update DATABASE_URL format
- Create `backend/alembic.ini` and migration files
- Create `backend/migrate_db.py` - Data migration script

---

## 4. Docker Containerization

### 4.1 Dockerfile Structure

**Backend Dockerfile** (`backend/Dockerfile`):
- Python 3.10 slim base
- Multi-stage build for optimization
- Install dependencies from `requirements.txt`
- Expose port 8000
- Health check endpoint

**Frontend Dockerfile** (`Dockerfile`):
- Node.js 18 Alpine base
- Build Next.js app
- Serve with standalone mode or static export
- Nginx for serving (optional)

**Docker Compose** (`docker-compose.yml`):
- Backend service (scalable)
- Frontend service
- PostgreSQL service (or external RDS)
- Redis service (or external ElastiCache)
- Nginx load balancer

### 4.2 Container Orchestration

**For Production:**
- Use Docker Compose for single-server deployment
- Or migrate to ECS/EKS for advanced orchestration (future)

---

## 5. Scalability Improvements

### 5.1 Backend Scaling

**Current Issues:**
- Single uvicorn process
- No connection pooling
- Synchronous file operations

**Solutions:**
1. **Multiple Workers:**
   - Use `gunicorn` with `uvicorn` workers
   - Configure: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
   - Scale containers horizontally

2. **Connection Pooling:**
   - SQLAlchemy connection pool (already supported, needs config)
   - Redis connection pooling

3. **Async Operations:**
   - Ensure all I/O operations are async
   - Use `aiofiles` for file operations (already in use)

**Files to Modify:**
- `backend/main.py` - Add gunicorn configuration
- `backend/app/core/database.py` - Configure connection pool
- `backend/Dockerfile` - Use gunicorn as entrypoint

### 5.2 ChromaDB Scaling

**Current Issue:** Local file-based ChromaDB doesn't scale across instances

**Solutions:**

**Option A: ChromaDB Server Mode (Recommended)**
- Run ChromaDB as a separate service
- All backend instances connect to shared ChromaDB server
- Deploy on dedicated EC2 instance or container

**Option B: Shared Volume (EBS)**
- Mount EBS volume to all instances
- ChromaDB reads/writes to shared storage
- Risk: File locking issues with concurrent writes

**Option C: Managed Vector DB (Future)**
- Pinecone, Weaviate Cloud, or AWS OpenSearch
- Higher cost but better scalability

**Implementation:**
- Create `backend/docker-compose.chromadb.yml` for ChromaDB server
- Update `backend/app/services/rag_service.py` to use ChromaDB client mode
- Configure `CHROMA_SERVER_HOST` and `CHROMA_SERVER_PORT`

**Files to Modify:**
- `backend/app/services/rag_service.py` - Switch to ChromaDB client mode
- `backend/app/core/config.py` - Add ChromaDB server settings
- Create `backend/docker-compose.chromadb.yml`

### 5.3 Caching Layer (Redis)

**Purpose:**
- Cache RAG query results
- Session storage
- Rate limiting
- Frequently accessed data

**Implementation:**
- Use ElastiCache Redis or self-hosted Redis container
- Add Redis client to backend
- Implement caching decorators for expensive operations

**Files to Create/Modify:**
- `backend/app/services/cache_service.py` - Redis caching service
- `backend/app/api/chat.py` - Add caching for RAG queries
- `backend/app/core/config.py` - Add Redis connection settings

### 5.4 File Storage Migration to S3

**Current Issue:** Local file storage doesn't scale across instances

**Solution:** Migrate uploads to S3

**Implementation:**
- Use `boto3` (already in requirements.txt)
- Update `backend/app/api/upload.py` to upload to S3
- Update `backend/app/services/document_processor.py` to read from S3
- Update `backend/app/core/config.py` for S3 bucket configuration

**Files to Modify:**
- `backend/app/api/upload.py` - S3 upload logic
- `backend/app/services/document_processor.py` - S3 download logic
- `backend/app/core/config.py` - Add S3 settings

---

## 6. Load Balancing & Reverse Proxy

### 6.1 Nginx Configuration

**Purpose:**
- Distribute traffic across backend instances
- SSL/TLS termination
- Static file serving
- Rate limiting

**Configuration:**
- Upstream backend servers (multiple FastAPI instances)
- Health checks
- Load balancing algorithm (round-robin or least connections)
- SSL certificate (Let's Encrypt or ACM)

**Files to Create:**
- `nginx/nginx.conf` - Main configuration
- `nginx/conf.d/app.conf` - Application-specific config

---

## 7. Monitoring & Logging

### 7.1 Application Monitoring

**Tools:**
- CloudWatch Logs (AWS native)
- Prometheus + Grafana (self-hosted)
- Application-level metrics

**Metrics to Track:**
- Request latency
- Error rates
- Database connection pool usage
- ChromaDB query performance
- Memory/CPU usage

### 7.2 Logging Strategy

**Centralized Logging:**
- CloudWatch Logs for AWS services
- File-based logs with log rotation
- Structured JSON logging

**Files to Modify:**
- `backend/main.py` - Add structured logging
- Create `backend/app/core/logging_config.py`

---

## 8. Security Enhancements

### 8.1 Production Security

1. **Environment Variables:**
   - Use AWS Secrets Manager or Parameter Store
   - Never commit secrets to code

2. **Network Security:**
   - Security groups (only necessary ports)
   - VPC with private subnets for backend
   - Public subnet only for load balancer

3. **SSL/TLS:**
   - ACM certificate or Let's Encrypt
   - Force HTTPS redirect

4. **Database Security:**
   - Encrypted connections
   - Strong passwords
   - Restricted access (security groups)

---

## 9. Deployment Strategy

### 9.1 Initial Deployment

1. **Setup EC2 Instance:**
   - Launch Ubuntu 22.04 LTS
   - Install Docker and Docker Compose
   - Configure security groups

2. **Database Setup:**
   - Launch RDS PostgreSQL or install on EC2
   - Create database and user
   - Run migrations

3. **Deploy Application:**
   - Clone repository
   - Build Docker images
   - Configure environment variables
   - Start services with Docker Compose

4. **Configure Nginx:**
   - Install and configure Nginx
   - Set up SSL certificate
   - Configure upstream backends

### 9.2 CI/CD Pipeline (Optional)

**Tools:**
- GitHub Actions or AWS CodePipeline
- Automated testing
- Docker image building
- Deployment to EC2

---

## 10. Cost Optimization Strategies

### 10.1 Instance Optimization

- Use Reserved Instances for 1-year commitment (30-40% savings)
- Use Spot Instances for non-critical workloads
- Right-size instances based on actual usage
- Use Auto Scaling to scale down during low traffic

### 10.2 Storage Optimization

- S3 lifecycle policies (move old files to Glacier)
- Compress files before upload
- Clean up temporary files regularly

### 10.3 Database Optimization

- Use RDS Reserved Instances
- Enable automated backups (7-day retention)
- Monitor and optimize query performance

---

## 11. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Choose and launch EC2 instance
- [ ] Install Docker and Docker Compose
- [ ] Create Dockerfiles for backend and frontend
- [ ] Set up PostgreSQL database
- [ ] Migrate from SQLite to PostgreSQL
- [ ] Test basic deployment

### Phase 2: Containerization (Week 1-2)
- [ ] Create docker-compose.yml
- [ ] Configure environment variables
- [ ] Test containerized deployment
- [ ] Set up basic Nginx reverse proxy

### Phase 3: Scalability (Week 2-3)
- [ ] Implement ChromaDB server mode
- [ ] Add Redis caching layer
- [ ] Migrate file storage to S3
- [ ] Configure connection pooling
- [ ] Set up multiple backend instances

### Phase 4: Production Hardening (Week 3-4)
- [ ] Configure SSL/TLS
- [ ] Set up monitoring and logging
- [ ] Implement health checks
- [ ] Configure auto-scaling (if needed)
- [ ] Security audit and hardening
- [ ] Load testing with 200+ concurrent users

### Phase 5: Optimization (Ongoing)
- [ ] Performance tuning
- [ ] Cost optimization
- [ ] Monitoring and alerting
- [ ] Documentation

---

## 12. Files to Create/Modify

### New Files to Create:
- `backend/Dockerfile`
- `Dockerfile` (frontend)
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `nginx/nginx.conf`
- `nginx/conf.d/app.conf`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/` (migration files)
- `backend/migrate_db.py` (SQLite to PostgreSQL migration)
- `backend/app/services/cache_service.py`
- `backend/app/core/logging_config.py`
- `backend/gunicorn_config.py`
- `backend/docker-compose.chromadb.yml`
- `.github/workflows/deploy.yml` (optional CI/CD)
- `deployment/README.md` (deployment guide)

### Files to Modify:
- `backend/app/core/database.py` - Connection pooling, PostgreSQL support
- `backend/app/core/config.py` - Add new environment variables
- `backend/app/services/rag_service.py` - ChromaDB client mode
- `backend/app/api/upload.py` - S3 integration
- `backend/app/services/document_processor.py` - S3 file access
- `backend/main.py` - Gunicorn configuration, logging
- `backend/requirements.txt` - Add gunicorn, alembic, psycopg2
- `package.json` - Update build scripts for production

---

## 13. Environment Variables (New)

### Backend (.env):
```env
# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/dbname
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# ChromaDB Server
CHROMA_SERVER_HOST=chromadb-server
CHROMA_SERVER_PORT=8000

# Redis Cache
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# AWS S3
AWS_S3_BUCKET=your-bucket-name
AWS_S3_REGION=us-east-1

# Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 14. Testing Strategy

### Load Testing:
- Use Apache Bench (ab) or Locust
- Test with 200+ concurrent users
- Monitor response times, error rates
- Identify bottlenecks

### Performance Benchmarks:
- API response time < 2 seconds (p95)
- Database query time < 500ms
- ChromaDB search < 1 second
- File upload < 10 seconds (100MB)

---

## 15. Rollback Plan

- Keep SQLite database backup
- Maintain previous Docker images
- Document rollback procedures
- Test rollback process

---

## 16. Estimated Costs (Monthly)

**Option A: Single Large Instance**
- EC2 t3.2xlarge: ~$240
- RDS db.t3.medium: ~$60
- ElastiCache cache.t3.micro: ~$15
- ALB: ~$20
- S3 Storage (100GB): ~$3
- Data Transfer: ~$10
- **Total: ~$348/month**

**Option B: Multiple Smaller Instances**
- 2x EC2 t3.large: ~$120
- RDS db.t3.medium: ~$60
- ElastiCache cache.t3.micro: ~$15
- ALB: ~$20
- S3 Storage: ~$10
- Data Transfer: ~$20
- **Total: ~$245/month**

Both options are well under the $500/month budget with room for scaling.

---

## 17. Next Steps

1. Review and approve this plan
2. Set up AWS account and IAM roles
3. Begin Phase 1 implementation
4. Test each phase before proceeding
5. Monitor costs and performance
6. Iterate based on real-world usage

---

## Summary

This plan provides a comprehensive roadmap for deploying the AGENT platform to AWS EC2 with:
- **OS:** Ubuntu 22.04 LTS (recommended)
- **Containerization:** Docker with Docker Compose
- **Database:** PostgreSQL (migrated from SQLite)
- **Scalability:** Horizontal scaling with multiple backend instances
- **Caching:** Redis for performance
- **Storage:** S3 for file uploads
- **Load Balancing:** Nginx reverse proxy
- **Budget:** Under $500/month (Option B: ~$245/month)
- **Capacity:** Supports 200+ concurrent users

The plan is structured in 5 phases, allowing for incremental implementation and testing at each stage.




