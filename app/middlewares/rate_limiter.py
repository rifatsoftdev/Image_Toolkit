import logging
from datetime import datetime, timedelta, time
from fastapi import Request, HTTPException, status
import redis
from app.core.config import settings

logger = logging.getLogger("dting_toolkit.rate_limiter")

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )
    # Test connection on startup
    redis_client.ping()
    logger.info("Successfully connected to Redis/Valkey for rate limiting.")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}. Rate limiting will fallback to allowing requests.")
    redis_client = None

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"

def get_seconds_until_midnight() -> int:
    now = datetime.now()
    tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min)
    return int((tomorrow - now).total_seconds())

async def check_rate_limit(request: Request):
    if not redis_client:
        # Fallback to allow if Redis is down
        return

    ip = get_client_ip(request)
    today_str = datetime.now().strftime("%Y-%m-%d")
    redis_key = f"image_tool:{ip}:{today_str}"

    try:
        current_count = redis_client.get(redis_key)
        
        if current_count is not None:
            count = int(current_count)
            if count >= settings.RATE_LIMIT_DAILY:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_DAILY} image operations per day."
                )
        
        # Increment the counter
        pipeline = redis_client.pipeline()
        pipeline.incr(redis_key)
        # If key is new, set TTL to midnight
        if current_count is None:
            ttl = get_seconds_until_midnight()
            pipeline.expire(redis_key, ttl)
        pipeline.execute()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking rate limit in Redis: {e}")
        # Allow request to proceed if Redis errors
        pass
