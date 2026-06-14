# AgentWatch Disaster Recovery Report

**Date:** June 13, 2026
**Version:** 0.1.0
**Environment:** Production
**Classification:** Internal — Confidential

---

## Recovery Scenario Matrix

| Scenario | RTO Estimate | RPO Estimate | Severity | Dependencies |
|----------|:-----------:|:-----------:|:--------:|:------------:|
| PostgreSQL Failure | 30-60 min | 5 min (WAL) / 24 hr (backup) | CRITICAL | S3/EBS for backups |
| Redis Failure | 5-15 min | 0-60 sec (AOF) | HIGH | AOF persistence |
| Worker (Dramatiq) Failure | 10-30 min | 0 min (in Redis) | HIGH | Redis availability |
| ChromaDB Failure | 30-120 min | 24 hr (backup) | MEDIUM | Persistent volume |
| API Restart | 1-5 min | 0 min | LOW | Load balancer |
| Full Region Outage | 4-24 hr | 24 hr | CRITICAL | Multi-region infra |

---

## 1. PostgreSQL Failure

### Detection
- **Health check failure**: Docker healthcheck (`pg_isready`) in `docker-compose.yml:15-19` — interval 5s, timeout 5s, retries 5
- **API error surge**: `Database session error` or `connection refused` in `RequestLoggingMiddleware` logs (appears as 5xx responses)
- **Prometheus alert**: `db_query_duration_seconds` spikes → `errors_total{service="database"}` increases
- **Application logs**: SQLAlchemy raises `OperationalError` / `InterfaceError`; logged via `app/core/logging.py` structured logger
- **Sentry**: SQLAlchemy integration captures DB errors as Sentry events
- **Grafana dashboard**: DB connection pool metrics, query duration panels

### Impact
- **Complete service outage**: All API endpoints that read/write data fail (projects, sessions, documents, reports, auth, evaluation)
- **Statistics endpoint**: `/health` may still respond (depends on implementation — if health check queries DB, it fails)
- **Metrics endpoint**: `/metrics` still works (Prometheus client is in-process)
- **Workers**: Dramatiq workers also connect to DB for status updates — they will fail with retries
- **Auth**: Login/register/refresh all fail — no new sessions or token refreshes

### RTO Estimate: 30-60 minutes
- **WAL replay (fastest)**: 5-15 min if using streaming replica + pg_rewind
- **EBS snapshot restore**: 20-40 min to detach, restore, reattach volume
- **pg_dump restore**: 30-60 min for full restore (depends on data size)
- **Aurora failover**: 1-2 min (if using RDS Aurora with Multi-AZ)

### RPO Estimate: 5 minutes (WAL) / 24 hours (backup)
- **Synchronous replication**: 0 RPO with synchronous_standby_names
- **Asynchronous replication**: ~5 sec RPO with streaming replication
- **Daily pg_dump**: 24 hr RPO window (maximum data loss)
- **WAL archival**: Continuous WAL shipping to S3 enables point-in-time recovery (5 min RPO)

### Recovery Procedure

**Scenario A: PostgreSQL process crashed but volume intact**

1. Verify the failure:
   ```bash
   docker-compose ps db
   docker-compose logs db --tail 50
   ```

2. Restart the container:
   ```bash
   docker-compose restart db
   ```

3. Verify recovery:
   ```bash
   docker-compose exec db pg_isready -U agentwatch
   ```

4. Verify API connectivity:
   ```bash
   curl -f http://localhost:8000/health
   ```

5. Monitor application logs for connection re-establishment.

**Scenario B: Data corruption or volume failure requiring restore**

1. Stop all dependent services:
   ```bash
   docker-compose stop api worker
   ```

2. Identify latest valid backup:
   ```bash
   ls -la /backups/postgres/
   # Most recent: agentwatch_2026-06-13_020000.sql.gz
   ```

3. Restore from pg_dump:
   ```bash
   docker-compose exec -T db psql -U agentwatch < agentwatch_2026-06-13_020000.sql
   ```

4. Or restore from EBS snapshot:
   ```bash
   # AWS CLI
   aws ec2 stop-instances --instance-ids $DB_INSTANCE
   aws ec2 detach-volume --volume-id $VOLUME_ID
   aws ec2 create-volume --snapshot-id $SNAPSHOT_ID --availability-zone $AZ
   aws ec2 attach-volume --volume-id $NEW_VOLUME_ID --instance-id $DB_INSTANCE --device /dev/sdf
   aws ec2 start-instances --instance-ids $DB_INSTANCE
   ```

5. Run pending Alembic migrations:
   ```bash
   docker-compose run api alembic upgrade head
   ```

6. Verify data integrity:
   ```bash
   docker-compose exec db psql -U agentwatch -c "SELECT count(*) FROM users;"
   ```

7. Restart services:
   ```bash
   docker-compose start api worker
   ```

**Scenario C: RDS Aurora Multi-AZ failover**

1. Automatic — RDS handles failover to standby replica
2. Verify new writer endpoint:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier agentwatch | jq '.DBClusters[0].Endpoint'
   ```
3. Update connection string if DNS hasn't propagated:
   - Update `DATABASE_URL` environment variable with new writer endpoint
   - Restart API and workers: `docker-compose restart api worker`

### Mitigations Available
- **Connection pooling**: `app/core/config.py:17-18` — `database_pool_size: 10`, `database_max_overflow: 20`. Pool absorbs brief outages.
- **Retry logic**: SQLAlchemy engine has built-in retry. Alembic retries on migration.
- **Backup schedule**: Postgres 16 with `pg_dump` via cron (recommended: daily at 02:00 UTC)
- **WAL archiving**: Recommended: archive to S3 with `archive_command` for PITR
- **Read replicas**: Not currently configured — recommended for failover and read scaling

### Required Tooling
- `pg_dump` / `pg_restore` (PostgreSQL 16 client)
- AWS CLI (for EBS/RDS operations)
- `wal-g` or `pgBackRest` (recommended for WAL-based backup)
- Monitoring: Prometheus `pg_exporter` (recommended)

### Prevention Measures
- Enable PostgreSQL `archive_mode = on` and `archive_command` to S3
- Configure RDS Multi-AZ or streaming replication standby
- Set `max_connections` with headroom (current staging: pool_size=20, max_overflow=40)
- Regular backup testing — restore from backup monthly
- Disk space monitoring: `df -h` alert at 80% capacity

### Testing Recommendations
- Monthly: Restore from latest backup to staging environment, verify data integrity
- Quarterly: Failover test (promote replica, verify application)
- Post-deployment: Verify migrations are idempotent: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`

---

## 2. Redis Failure

### Detection
- **Health check failure**: Docker healthcheck (`redis-cli ping`) in `docker-compose.staging.yml:53-56` — interval 15s
- **Application logs**: `app/main.py:47-50` logs `"Redis unavailable, rate limiting disabled"` warning on connection failure
- **Prometheus**: `redis_up` metric (if using `redis_exporter`) drops to 0
- **Dramatiq errors**: `RedisBroker` connection errors in worker logs → tasks fail to enqueue/dequeue
- **API errors**: Rate limiting becomes non-operational (fail-open). Cache misses increase.
- **Sentry**: Redis connection errors captured via `app/redis/client.py` error logging

### Impact
- **Rate limiting disabled**: `app/middleware/rate_limit.py:71-83` — fail-open means all requests pass without rate checks
- **Dramatiq queue unavailable**: `app/workers/dramatiq_worker.py:25-32` — `RedisBroker` cannot connect → all async tasks (workflow execution, report generation) fail to enqueue. **StubBroker fallback only works in dev** (`redis_url != "memory"` check)
- **Cache misses**: `CacheService` degrades — every request hits the database directly
- **Distributed locks unavailable**: `app/redis/client.py:173-188` — `acquire_lock`/`release_lock` fail. Concurrent workflow execution protection lost.
- **Workflow state storage**: `app/redis/client.py:153-171` — `set_workflow_state`/`get_workflow_state` fail. In-progress workflows lose state persistence.
- **No cascading failure**: API continues serving requests; all Redis failures are caught with graceful error handling

### RTO Estimate: 5-15 minutes
- **Container restart**: 1-2 min (`docker-compose restart redis`)
- **AOF recovery**: Depends on AOF file size — typically 1-5 min for append replay
- **RDB reload**: 5-10 min for large datasets
- **ElastiCache failover**: 30-60 sec automatic (if Multi-AZ cluster)

### RPO Estimate: 0-60 seconds
- **AOF everysec**: `appendfsync everysec` → at most 1 second of data loss
- **RDB snapshots**: Last snapshot (configurable: 60s if 1 key changed per staging config)
- **No persistence**: If AOF disabled, all data since last RDB is lost

### Recovery Procedure

**Scenario A: Redis process crash (AOF enabled)**

1. Redis auto-restarts with `restart: always` policy:
   ```bash
   docker-compose ps redis
   ```

2. If auto-restart fails, force restart:
   ```bash
   docker-compose restart redis
   ```

3. Verify AOF recovery:
   ```bash
   docker-compose exec redis redis-cli info persistence
   # aof_enabled:1, aof_last_bgrewrite_status:ok
   ```

4. Verify connectivity from API:
   ```bash
   docker-compose exec api python -c "from app.redis.client import get_redis; import asyncio; print(asyncio.run(get_redis().ping()))"
   ```

5. Check rate limiting resumes:
   ```bash
   # Rapid requests to /auth/login should return 429 after 5 attempts
   for i in $(seq 1 6); do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"wrong"}'; done
   ```

**Scenario B: Data corruption — flush and rebuild**

1. Flush Redis:
   ```bash
   docker-compose exec redis redis-cli FLUSHALL
   ```

2. Verify flush:
   ```bash
   docker-compose exec redis redis-cli DBSIZE
   # Output: (integer) 0
   ```

3. Restart Redis fresh:
   ```bash
   docker-compose restart redis
   ```

4. Note: All rate limit counters, cache entries, and workflow states are lost. No permanent data loss (PostgreSQL is source of truth).

**Scenario C: ElastiCache failover**

1. Automatic failover to replica node (30-60 sec)
2. Verify new primary:
   ```bash
   aws elasticache describe-replication-groups --replication-group-id agentwatch | jq '.ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint'
   ```
3. Update `REDIS_URL` if endpoint changed
4. Restart API + workers: `docker-compose restart api worker`

### Mitigations Available
- **Connection retry**: `app/redis/client.py:30-57` — `connect()` retries with exponential backoff (2s, 4s, 8s), 3 attempts max
- **Graceful degradation**: `app/middleware/rate_limit.py:71-73` — All rate limit checks return `(True, max_req, 0)` on Redis failure
- **AOF persistence**: `docker-compose.staging.yml:48` — `--appendonly yes --save 60 1` — enables AOF + periodic RDB
- **Connection pooling**: `app/redis/client.py:21` — `pool_size=10` (configurable, staging: 20)
- **Health check interval**: `app/core/config.py:57` — `redis_health_check_interval: int = 30`

### Required Tooling
- `redis-cli` (included in Redis image)
- `redis_exporter` for Prometheus (recommended)
- AWS CLI (for ElastiCache operations)

### Prevention Measures
- Enable AOF persistence (`appendonly yes`) at all times (staging does this, dev `memory` mode does not)
- Configure Redis maxmemory + eviction policy (`maxmemory-policy allkeys-lru`)
- Set up Redis Sentinel or ElastiCache Multi-AZ for automatic failover
- Monitor: `INFO keyspace`, `INFO memory`, `INFO stats` via Prometheus

### Testing Recommendations
- Monthly: Simulate Redis failure by stopping Redis container, verify:
  - API continues serving with rate limiting disabled
  - Dramatiq tasks fail gracefully
  - Cache misses return correct data from DB
- Quarterly: Test AOF recovery by corrupting appendonly.aof and verifying auto-recovery
- Post-deployment: Verify `sliding_window_counter` correctness with `zrange` inspection

---

## 3. Worker (Dramatiq) Failure

### Detection
- **Queue backlog**: Prometheus `queue_depth` gauge (`app/core/observability.py:77-81`) increases
- **Execution staleness**: `AgentExecution` records remain in `PENDING` status beyond expected completion time
- **Dramatiq logs**: Worker process crash or `RedisBroker` connection errors in `app/workers/dramatiq_worker.py` logs
- **API caller experience**: `POST /agents/run` returns 202 Accepted but execution never completes (status stays PENDING)
- **Sentry**: Worker exception events with `service="worker"` tag
- **Docker health**: `docker-compose ps worker` shows unhealthy/restarting state
- **Prometheus alert**: `active_workflows` gauge at 0 for >5 min during business hours (alert rule)

### Impact
- **No workflow execution**: Research workflows, report generation, evaluation benchmarks — all async tasks stall
- **No cancellation**: `cancel_workflow_actor` cannot process cancellation requests
- **API unaffected**: All synchronous endpoints (auth, CRUD, retrieval) continue working
- **Database unaffected**: PostgreSQL and ChromaDB remain operational
- **Revenue impact**: Customers cannot run research or generate reports

### RTO Estimate: 10-30 minutes
- **Container restart**: 1-2 min (`docker-compose restart worker`)
- **Scaling up replicas**: 5-10 min to add worker instances
- **Code fix + redeploy**: 30-60 min if a bug caused the crash

### RPO Estimate: 0 minutes
- **No data loss**: Tasks are stored in Redis broker until acknowledged. If worker crashes mid-task, the message is re-queued (Dramatiq redelivery)
- **In-flight work loss**: If a task was being processed but not acknowledged, it will be retried (up to `max_retries=3`)

### Recovery Procedure

**Scenario A: Worker process crash (OOM, unhandled exception)**

1. Check worker status:
   ```bash
   docker-compose ps worker
   docker-compose logs worker --tail 50
   ```

2. Restart worker:
   ```bash
   docker-compose restart worker
   ```

3. Verify queue processing resumes:
   ```bash
   # Check Prometheus queue_depth metric
   curl -s http://localhost:9090/api/v1/query?query=queue_depth | jq '.data.result'
   
   # Or check execution records transitioning from PENDING
   docker-compose exec db psql -U agentwatch -c "SELECT COUNT(*) FROM agent_executions WHERE execution_status = 'PENDING';"
   ```

4. Monitor worker logs for task completion.

**Scenario B: All workers crashed / stuck**

1. Scale down and restart:
   ```bash
   docker-compose stop worker
   docker-compose rm worker
   docker-compose up -d worker
   ```

2. If using orchestrator (K8s/ECS):
   ```bash
   kubectl delete pod -l app=agentwatch-worker
   # Or
   aws ecs update-service --cluster agentwatch --service worker --desired-count 0
   aws ecs update-service --cluster agentwatch --service worker --desired-count 2
   ```

3. Verify Dramatiq broker status:
   ```python
   # Connect to Redis and inspect queue
   docker-compose exec redis redis-cli LLEN dramatiq:workflows.default
   ```

4. Check for poisoned messages (messages that crash on processing):
   ```bash
   docker-compose exec redis redis-cli LLEN dramatiq:workflows.default
   # If >0 and workers keep crashing, inspect message content
   docker-compose exec redis redis-cli LRANGE dramatiq:workflows.default 0 0
   ```
   
   If poisoned message found, remove it:
   ```bash
   docker-compose exec redis redis-cli LTRIM dramatiq:workflows.default 1 -1
   ```

**Scenario C: Stuck task holding worker hostage**

1. Identify stuck execution ID from worker logs
2. Connect to Redis and cancel the task:
   ```bash
   docker-compose exec redis redis-cli GET dramatiq:workflows.default:${execution_id}:state
   ```
3. Restart worker:
   ```bash
   docker-compose restart worker
   ```
4. Mark execution as FAILED in DB:
   ```bash
   docker-compose exec db psql -U agentwatch -c "UPDATE agent_executions SET execution_status='FAILED', end_time=NOW() WHERE id='${execution_id}' AND execution_status='RUNNING';"
   ```

### Mitigations Available
- **Max retries**: `app/workers/dramatiq_worker.py:50` — `max_retries=3`. Failed tasks retry up to 3 times.
- **Time limit**: `app/workers/dramatiq_worker.py:51` — `time_limit=600_000` (10 min). Tasks exceeding limit are killed.
- **Age limit**: `app/workers/dramatiq_worker.py:31` — `age_limit=86_400_000` (24 hr). Old tasks are dropped.
- **Graceful shutdown**: `app/workers/dramatiq_worker.py:32` — `ShutdownNotifications()` middleware ensures in-flight tasks are requeued on shutdown.
- **Multiple workers**: `docker-compose.staging.yml:203` — `replicas: 2`. At least one worker remains operational if one fails.
- **Error tracking**: `app/workers/dramatiq_worker.py:113` — Exception caught and logged; execution status set to FAILED.

### Required Tooling
- `redis-cli` for queue inspection and management
- Prometheus + Grafana for queue depth monitoring
- Docker Compose / kubectl / AWS CLI for container management

### Prevention Measures
- **Horizontal scaling**: Run ≥2 worker replicas (staging runs 2)
- **Resource limits**: `docker-compose.staging.yml:204-209` — CPU/Memory limits defined per worker
- **Queue monitoring**: Prometheus `queue_depth` alert at threshold
- **Health checks**: Add application-level health check endpoint for workers
- **Graceful degradation**: Implement circuit breaker for LLM provider calls (prevent worker from hanging on slow API response)

### Testing Recommendations
- Monthly: Kill a worker pod, verify the other picks up tasks
- Monthly: Enqueue a poisoned message that crashes worker, verify remaining workers continue
- Quarterly: Load test with max queue depth (1000+ messages), verify throughput and backpressure handling
- Post-deployment: Verify `kill -15` gracefully shuts down worker (tasks requeued, not lost)

---

## 4. ChromaDB Failure

### Detection
- **Health check failure**: Docker healthcheck (`curl -f http://localhost:8000/api/v1/heartbeat`) in `docker-compose.yml:32-36`
- **API error**: Document retrieval/search endpoints return 500 with error trace containing `chromadb` or `grpc` errors
- **Application logs**: `app/vectorstore/retrieval.py` logs connection errors
- **Sentry**: ChromaDB driver exceptions captured
- **User impact**: Search and retrieval features fail; document upload succeeds but ingestion silently fails or errors

### Impact
- **Search/retrieval broken**: All semantic search endpoints (`POST /retrieval/search`, `POST /retrieval/context`) fail
- **Document ingestion fails**: New documents cannot be indexed into vector store
- **RAG workflow broken**: Research workflows that depend on retrieval-augmented generation will fail or produce empty context
- **API endpoints partially available**: Auth, CRUD, reports still work
- **No data loss**: Documents stored in PostgreSQL metadata remain; only vector embeddings are unavailable

### RTO Estimate: 30-120 minutes
- **Container restart**: 5-10 min (ChromaDB loads persisted data from disk on startup)
- **Volume restore from snapshot**: 20-40 min
- **Full rebuild from scratch**: 60-120 min (re-ingest all documents to regenerate embeddings)

### RPO Estimate: 24 hours (with daily backup) / RTO-dependent for full rebuild
- **Persistent volume**: Data on `chroma_data` volume — last good state
- **Full rebuild**: Zero data loss from source documents (stored in PostgreSQL / S3), but embeddings must be regenerated

### Recovery Procedure

**Scenario A: ChromaDB process crash**

1. Check ChromaDB status:
   ```bash
   docker-compose ps chromadb
   docker-compose logs chromadb --tail 50
   ```

2. Restart:
   ```bash
   docker-compose restart chromadb
   ```

3. Verify heartbeat:
   ```bash
   curl -f http://localhost:8001/api/v1/heartbeat
   ```

4. Verify search functionality:
   ```bash
   curl -X POST http://localhost:8000/retrieval/search \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query":"test","top_k":1}'
   ```

**Scenario B: Data corruption — restore from backup**

1. Stop dependent services:
   ```bash
   docker-compose stop api
   ```

2. Backup current corrupted data:
   ```bash
   mv /var/lib/docker/volumes/agentwatch_chroma_data/_data /var/lib/docker/volumes/agentwatch_chroma_data/_data.corrupted
   ```

3. Restore from snapshot:
   ```bash
   # Copy backup volume data
   cp -a /backups/chromadb/2026-06-13/chroma_data/* /var/lib/docker/volumes/agentwatch_chroma_data/_data/
   ```

4. Restart ChromaDB:
   ```bash
   docker-compose restart chromadb
   ```

5. Verify data:
   ```bash
   curl -f http://localhost:8001/api/v1/heartbeat
   ```

6. Restart API:
   ```bash
   docker-compose start api
   ```

**Scenario C: Full rebuild (no backup) — regenerate embeddings**

1. Ensure source documents are accessible in PostgreSQL:
   ```bash
   docker-compose exec db psql -U agentwatch -c "SELECT COUNT(*) FROM documents;"
   ```

2. Clear and restart ChromaDB:
   ```bash
   docker-compose stop chromadb
   rm -rf /var/lib/docker/volumes/agentwatch_chroma_data/_data/*
   docker-compose start chromadb
   ```

3. Run re-indexing script:
   ```bash
   # Trigger re-ingestion for all documents
   docker-compose run api python -m scripts.reindex_chromadb
   ```

4. Verify count:
   ```bash
   curl -X POST http://localhost:8000/retrieval/search \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query":"*","top_k":1000}'
   ```

5. Verify search quality with test queries.

### Mitigations Available
- **Persistent volume**: `docker-compose.yml:27` — `chroma_data:/chroma/chroma` maps to Docker volume; survives container restarts
- **Health checks**: Docker-level health check with curl heartbeat
- **Self-contained**: ChromaDB runs as a separate service; failure does not cascade to API or DB
- **Source document storage**: Documents are stored in PostgreSQL or S3; embeddings are derivable

### Required Tooling
- Re-indexing script (to be created): `scripts/reindex_chromadb.py`
- Docker volume management commands
- Prometheus `blackbox_exporter` for ChromaDB health monitoring

### Prevention Measures
- Regular volume backups (EBS snapshots of the ChromaDB volume)
- Monitor disk space on ChromaDB persistent volume
- Pin ChromaDB version (staging uses `chromadb/chroma:0.5.5`)
- Document re-indexing runbook available
- Consider ChromaDB clustering for high availability (future)

### Testing Recommendations
- Monthly: Restore ChromaDB from backup to staging, verify search results match
- Quarterly: Full re-index from source documents, measure time and verify completeness
- Post-deployment: Verify `/api/v1/heartbeat` returns 200 after each deployment

---

## 5. API Restart

### Detection
- **Load balancer health check**: LB marks API instances as unhealthy if `/health` returns non-200
- **Prometheus**: `up{job="api"}` metric drops to 0
- **Grafana**: `apdex` score drops during restart window
- **Docker health**: `docker-compose ps api` shows `starting` or `unhealthy`
- **User experience**: Brief period of 502/503 errors from load balancer (typically < 5 seconds)

### Impact
- **Brief service interruption**: In-flight HTTP requests are lost (not idempotent by default)
- **No data loss**: All persistent state is in PostgreSQL/Redis; API is stateless
- **In-flight workflow executions**: Tasks already dispatched to Dramatiq queue continue processing via workers
- **Active WebSocket connections**: Dropped (if any), clients must reconnect
- **Rate limit counters**: Reset (in-memory counters for non-Redis deployments; Redis-backed counters survive)

### RTO Estimate: 1-5 minutes
- **Rolling restart**: 1-2 min per instance (zero-downtime with LB + multiple instances)
- **Hard restart**: 30-60 sec container restart + 10-30 sec app startup (Alembic migrations, LLM validation)
- **Cold start (no cache)**: +10 sec for first request (Pydantic model compilation, DB pool warm-up)

### RPO Estimate: 0 minutes
- **No data loss**: API is stateless. All state is in PostgreSQL, Redis, ChromaDB
- **Unacknowledged requests**: May need retry from client (idempotency keys recommended)

### Recovery Procedure

**Scenario A: Planned rolling restart (deployment)**

1. Verify health of all instances:
   ```bash
   curl -f http://api-1:8000/health
   curl -f http://api-2:8000/health
   ```

2. Remove instance from load balancer:
   ```bash
   # AWS ALB
   aws elbv2 deregister-targets --target-group-arn $TG_ARN --targets Id=api-1,Port=8000
   # Wait for connection draining (30 sec)
   ```

3. Restart instance:
   ```bash
   docker-compose restart api
   # Or: kubectl rollout restart deployment agentwatch-api
   ```

4. Verify instance health:
   ```bash
   curl -f http://api-1:8000/health
   ```

5. Return to load balancer:
   ```bash
   aws elbv2 register-targets --target-group-arn $TG_ARN --targets Id=api-1,Port=8000
   ```

6. Repeat for remaining instances.

**Scenario B: Unplanned crash**

1. Auto-restart by Docker/compose:
   ```bash
   docker-compose ps api
   # Status should show "Up" or "restarting"
   ```

2. If auto-restart fails:
   ```bash
   docker-compose up -d api
   ```

3. Verify:
   ```bash
   docker-compose logs api --tail 20
   curl -f http://localhost:8000/health
   ```

**Scenario C: Stuck/hung process**

1. Force restart:
   ```bash
   docker-compose kill api
   docker-compose up -d api
   ```

2. Check logs for startup errors:
   ```bash
   docker-compose logs api --tail 100
   ```

### Mitigations Available
- **Stateless design**: `app/middleware/rate_limit.py` — Rate limit state in Redis. `app/services/auth_service.py` — Auth state in DB/Redis. API instances are interchangeable.
- **Health check endpoint**: `GET /health` for load balancer probing
- **Graceful shutdown**: Uvicorn handles SIGTERM by finishing in-flight requests (with timeout)
- **Multiple workers per instance**: `docker-compose.staging.yml:162` — `--workers 4` (4 processes per API container)
- **Multiple instances**: Load balancer distributes across ≥2 API instances

### Required Tooling
- Docker Compose / kubectl / AWS CLI
- Load balancer management (AWS ALB/NLB, Nginx, Traefik)
- Health check scripts

### Prevention Measures
- Run ≥2 API instances behind load balancer (N > 1)
- Configure health check grace period (30s start_period in staging)
- Connection draining on LB (30-60 sec) to allow in-flight requests to complete
- Use `--limit-concurrency` (staging: 100) to prevent connection pileup
- Pre-warm connection pool on startup

### Testing Recommendations
- Weekly: Rolling restart in staging, measure downtime per instance
- Monthly: Kill API instance while requests are in-flight, verify LB routes to healthy instance
- Post-deployment: Verify `/health` endpoint and migration run within 30 seconds

---

## 6. Full Region Outage

### Detection
- **Cloud provider status page**: AWS/GCP service health dashboard shows region impairment
- **All services down**: API, DB, Redis, ChromaDB, workers — all unreachable
- **External monitoring**: Pingdom, Better Uptime, or StatusCake alerts show all endpoints down
- **CloudWatch/Azure Monitor**: Region-level incident detected
- **Customer reports**: Influx of support tickets within minutes

### Impact
- **Complete service outage**: 100% of AgentWatch functionality unavailable
- **Data in primary region inaccessible**: PostgreSQL, Redis, ChromaDB in the affected region are down
- **In-flight workflows lost**: Any tasks being processed when region goes down are lost (retry in secondary region)
- **DNS resolution fails**: If DNS points to region-specific load balancer that is down
- **Revenue impact**: Full business interruption

### RTO Estimate: 4-24 hours
- **DNS failover**: 5-30 min (TTL-dependent; recommended: 60 sec TTL)
- **Database replication promotion**: 15-30 min (if cross-region read replica exists)
- **Infrastructure provisioning**: 2-4 hr (if using Infrastructure-as-Code to spin up secondary region)
- **Data restore from backup**: 4-24 hr to restore PostgreSQL + ChromaDB from cross-region backups
- **Full warm standby**: 30-60 min (if secondary region pre-provisioned with synced data)

### RPO Estimate: 24 hours (daily backups to secondary region) / 5 minutes (with WAL shipping)
- **Daily backups to S3 in secondary region**: Up to 24 hr of data loss
- **Cross-region WAL shipping**: ~5 min RPO
- **Synchronous cross-region replication**: 0 RPO (impractical for most deployments due to latency)

### Recovery Procedure

**Scenario A: Warm standby in secondary region (pre-provisioned)**

1. Verify primary region outage:

2. Promote secondary PostgreSQL to primary:
   ```bash
   # If using RDS cross-region replica
   aws rds promote-read-replica --db-instance-identifier agentwatch-dr \
     --region us-west-2
   ```

3. Fail over DNS:
   ```bash
   # Update Route53 DNS record
   aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID \
     --change-batch '{
       "Changes": [{
         "Action": "UPSERT",
         "ResourceRecordSet": {
           "Name": "api.agentwatch.ai",
           "Type": "A",
           "AliasTarget": {
             "HostedZoneId": $DR_LB_ZONE_ID,
             "DNSName": "agentwatch-dr-lb.us-west-2.elb.amazonaws.com",
             "EvaluateTargetHealth": true
           }
         }
       }]
     }'
   ```

4. Scale up secondary region API instances:
   ```bash
   aws ecs update-service --cluster agentwatch-dr --service api --desired-count 4 \
     --region us-west-2
   aws ecs update-service --cluster agentwatch-dr --service worker --desired-count 4 \
     --region us-west-2
   ```

5. Verify service health:
   ```bash
   curl -f https://api.agentwatch.ai/health
   ```

6. Run any pending migrations:
   ```bash
   docker-compose run api alembic upgrade head
   ```

7. Update Sentry DSN environment if region-specific:
   - Update `SENTRY_ENVIRONMENT` to `production-dr`

8. Monitor: Verify all alerting, dashboards, and logging are operational in secondary region.

**Scenario B: Cold recovery from backups (no pre-provisioned infra)**

1. Provision infrastructure in secondary region:
   ```bash
   # Deploy using Terraform / CloudFormation
   terraform workspace select us-west-2
   terraform apply -auto-approve
   ```

2. Restore PostgreSQL from cross-region backup:
   ```bash
   # Copy backup from primary region's S3 bucket
   aws s3 cp s3://agentwatch-backups-us-east-1/postgres/latest.sql.gz \
     s3://agentwatch-backups-us-west-2/postgres/
   
   # Restore to new RDS instance
   gunzip -c latest.sql.gz | psql -h agentwatch-dr.xxx.us-west-2.rds.amazonaws.com -U agentwatch -d agentwatch
   ```

3. Restore ChromaDB embeddings:
   ```bash
   # Copy ChromaDB backup
   aws s3 sync s3://agentwatch-backups-us-east-1/chromadb/latest/ \
     /var/lib/docker/volumes/chroma_data/_data/
   ```

4. Restore Redis (if needed for cache warm-up):
   - Redis is ephemeral — rate limit counters and cache will rebuild
   - If AOF backup exists: copy and replay

5. Deploy API + workers:
   ```bash
   ECR_REPO=xxx.dkr.ecr.us-west-2.amazonaws.com/agentwatch-api
   docker pull $ECR_REPO:latest
   docker-compose -f docker-compose.prod.yml up -d
   ```

6. Update DNS → secondary region load balancer.

7. Verify full functionality:
   ```bash
   # Health check
   curl -f https://api.agentwatch.ai/health
   
   # Smoke test
   curl -X POST https://api.agentwatch.ai/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@agentwatch.ai","password":"test123"}'
   
   # Search
   curl -X POST https://api.agentwatch.ai/retrieval/search \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query":"test","top_k":1}'
   ```

### Mitigations Available
- **Cross-region backups**: PostgreSQL dumps to S3 with cross-region replication (recommended)
- **Container images**: Docker images stored in ECR (region-agnostic)
- **Infrastructure as Code**: Terraform/CloudFormation templates enable rapid provisioning
- **Configuration in env vars**: No hardcoded region-specific configuration
- **Stateless API**: API instances are fully interchangeable across regions
- **DNS-based failover**: Route53 health checks + failover routing policy

### Required Tooling
- **Terraform** or **CloudFormation** for infrastructure provisioning
- **AWS CLI** for RDS, ECS, Route53, S3 operations
- **External monitoring**: Pingdom, Better Uptime, or StatusCake
- **Backup scripts**: Cross-region backup replication
- **Runbook**: Documented DR procedure (this document)

### Prevention Measures
- **Infrastructure as Code**: Full deployment automation (Terraform modules)
- **Cross-region backups**: Automate backup replication to secondary region
- **DNS low TTL**: 60 seconds on production DNS records
- **Warm standby** (recommended for production): Minimal footprint in secondary region (read replica + scaled-down API)
- **Regular DR testing**: Quarterly full-region failover drill
- **Container registry replication**: ECR cross-region replication for Docker images

### Testing Recommendations
- **Quarterly**: Full region failover drill
  - Stage 1 (tabletop): Walk through runbook with team
  - Stage 2 (staging DR): Deploy staging to secondary region, fail over
  - Stage 3 (production DR, read-only): Verify read replica in secondary region
- **Monthly**: Cross-region backup restore test to staging environment
- **Weekly**: Verify DNS failover configuration (Route53 health checks)
- **After each infrastructure change**: Update and validate DR runbook

---

## Appendix: Recovery Tooling Inventory

| Tool | Purpose | Required For |
|------|---------|-------------|
| `docker-compose` | Container orchestration | All scenarios |
| `psql` / `pg_isready` | PostgreSQL management | PostgreSQL failure |
| `redis-cli` | Redis queue/cache management | Redis, Worker failure |
| `curl` | Health check verification | All scenarios |
| AWS CLI | RDS, EBS, Route53, S3 ops | PostgreSQL, Full region |
| Terraform | Infrastructure provisioning | Full region |
| `pg_dump` / `pg_restore` | Database backup/restore | PostgreSQL failure |
| `wal-g` | WAL-based backup/recovery | PostgreSQL failure (recommended) |

## Appendix: Key Contacts and Escalation

| Role | Responsibility |
|------|---------------|
| On-call Engineer | Initial response, triage, recovery execution |
| Infrastructure Lead | Infrastructure provisioning, DNS, cloud provider coordination |
| Database Administrator | PostgreSQL recovery, data integrity verification |
| Security Lead | Security incident coordination (if breach suspected) |
| Engineering Manager | Customer communication, status page updates |
| VP Engineering | Launch decision for full region failover |

## Appendix: Post-Recovery Checklist

- [ ] All smoke tests pass (auth, CRUD, search, workflow execution)
- [ ] Data integrity verified (spot-check user data, documents, executions)
- [ ] Monitoring and alerting operational (Prometheus, Grafana, Sentry)
- [ ] Rate limiting functional (verify 429 on rapid auth requests)
- [ ] Worker queue draining (no backlog; tasks processing normally)
- [ ] Customer communication sent (status update)
- [ ] Post-mortem initiated (incident timeline, root cause, action items)
- [ ] Backup schedule resumed and verified
- [ ] DNS records confirmed pointing to correct endpoints
- [ ] SSL/TLS certificates valid
