#!/usr/bin/env python3
"""
Production Readiness Validation Script

This script validates that the application is ready for production deployment.
It checks:
- Environment configuration
- Database connectivity
- Redis connectivity
- Qdrant connectivity
- Health endpoints
- Metrics endpoint
- Security configuration
"""

import asyncio
import os
import sys
from typing import Any

import httpx


class ProductionValidator:
    def __init__(self) -> None:
        self.results: dict[str, Any] = {
            "checks": [],
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }
    
    def add_check(self, name: str, passed: bool, message: str, severity: str = "error") -> None:
        self.results["checks"].append({
            "name": name,
            "passed": passed,
            "message": message,
            "severity": severity,
        })
        if passed:
            self.results["passed"] += 1
            print(f"✅ {name}: {message}")
        else:
            if severity == "error":
                self.results["failed"] += 1
                print(f"❌ {name}: {message}")
            else:
                self.results["warnings"] += 1
                print(f"⚠️  {name}: {message}")
    
    async def check_environment(self) -> None:
        """Check required environment variables."""
        required_vars = [
            "DATABASE_URL",
            "JWT_SECRET",
            "ENCRYPTION_KEY",
            "REDIS_URL",
            "QDRANT_URL",
        ]
        
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                self.add_check(f"env:{var}", False, f"Required environment variable {var} not set")
            elif var in ("JWT_SECRET", "ENCRYPTION_KEY") and len(value) < 32:
                self.add_check(f"env:{var}", False, f"{var} must be at least 32 characters")
            else:
                self.add_check(f"env:{var}", True, f"{var} is set")
        
        # Check production-specific
        env = os.environ.get("ENV", "development")
        if env == "production":
            # Verify no insecure defaults
            jwt_secret = os.environ.get("JWT_SECRET", "")
            if jwt_secret == "insecure-jwt-secret-change-me-to-a-secure-value":
                self.add_check("env:JWT_SECRET_prod", False, "Insecure default JWT_SECRET used in production")
            
            enc_key = os.environ.get("ENCRYPTION_KEY", "")
            if enc_key == "insecure-dev-key":
                self.add_check("env:ENCRYPTION_KEY_prod", False, "Insecure default ENCRYPTION_KEY used in production")
    
    async def check_database(self) -> None:
        """Check database connectivity."""
        try:
            import asyncpg
            database_url = os.environ.get("DATABASE_URL", "")
            if database_url.startswith("postgresql"):
                # Convert to asyncpg format
                conn = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))
                await conn.execute("SELECT 1")
                await conn.close()
                self.add_check("database:connectivity", True, "PostgreSQL connection successful")
            else:
                self.add_check("database:connectivity", True, f"Using SQLite: {database_url}", "warning")
        except Exception as e:
            self.add_check("database:connectivity", False, f"Database connection failed: {e}")
    
    async def check_redis(self) -> None:
        """Check Redis connectivity."""
        try:
            import redis.asyncio as redis
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            client = redis.from_url(redis_url)
            await client.ping()
            await client.close()
            self.add_check("redis:connectivity", True, "Redis connection successful")
        except Exception as e:
            self.add_check("redis:connectivity", False, f"Redis connection failed: {e}")
    
    async def check_qdrant(self) -> None:
        """Check Qdrant connectivity."""
        try:
            qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{qdrant_url}/health", timeout=5.0)
                if response.status_code == 200:
                    self.add_check("qdrant:connectivity", True, "Qdrant connection successful")
                else:
                    self.add_check("qdrant:connectivity", False, f"Qdrant health check failed: {response.status_code}")
        except Exception as e:
            self.add_check("qdrant:connectivity", False, f"Qdrant connection failed: {e}")
    
    async def check_health_endpoints(self) -> None:
        """Check health endpoints."""
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        endpoints = [
            ("/health", "Full health check"),
            ("/health/live", "Liveness probe"),
            ("/health/ready", "Readiness probe"),
            ("/metrics", "Prometheus metrics"),
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for path, description in endpoints:
                try:
                    response = await client.get(f"{base_url}{path}")
                    if response.status_code == 200:
                        self.add_check(f"http:{path}", True, f"{description} returns 200 OK")
                    else:
                        self.add_check(f"http:{path}", False, f"{description} returned {response.status_code}")
                except Exception as e:
                    self.add_check(f"http:{path}", False, f"{description} failed: {e}")
    
    async def check_security_config(self) -> None:
        """Check security configuration."""
        # Check JWT secret
        jwt_secret = os.environ.get("JWT_SECRET", "")
        if len(jwt_secret) >= 32:
            self.add_check("security:jwt_secret_length", True, "JWT secret is at least 32 characters")
        else:
            self.add_check("security:jwt_secret_length", False, "JWT secret must be at least 32 characters")
        
        # Check encryption key
        enc_key = os.environ.get("ENCRYPTION_KEY", "")
        if enc_key and enc_key != "insecure-dev-key":
            self.add_check("security:encryption_key", True, "Encryption key is set and not default")
        else:
            self.add_check("security:encryption_key", False, "Encryption key is not set or uses default")
        
        # Check CORS
        cors = os.environ.get("CORS_ORIGINS", "")
        if cors and cors != "*":
            self.add_check("security:cors", True, f"CORS origins configured: {cors}")
        else:
            self.add_check("security:cors", False, "CORS origins not properly configured", "warning")
    
    async def run_all(self) -> bool:
        """Run all validation checks."""
        print("=" * 60)
        print("Production Readiness Validation")
        print("=" * 60)
        
        await self.check_environment()
        await self.check_database()
        await self.check_redis()
        await self.check_qdrant()
        await self.check_health_endpoints()
        await self.check_security_config()
        
        print("\n" + "=" * 60)
        print(f"Results: {self.results['passed']} passed, {self.results['failed']} failed, {self.results['warnings']} warnings")
        print("=" * 60)
        
        return self.results["failed"] == 0


async def main() -> int:
    validator = ProductionValidator()
    success = await validator.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
