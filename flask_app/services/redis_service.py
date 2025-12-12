import redis
import time
import uuid
from functools import wraps
from flask import request, jsonify
from config import Config

# Connect to Redis container
r = redis.from_url(Config.REDIS_URL)

def rate_limit(limit=10, window=60):
    """
    Sliding Window Rate Limiter using Redis Sorted Sets (ZSET).

    Args:
        limit (int): Max requests allowed.
        window (int): Time window in seconds.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                ip = request.remote_addr
                key = f"rate_limit:{ip}"

                now = time.time()
                window_start = now - window

                pipe = r.pipeline()

                # Remove all requests older than the window start
                pipe.zremrangebyscore(key, 0, window_start)

                # Add the current request
                request_id = f"{now}:{uuid.uuid4()}"
                pipe.zadd(key, {request_id: now})

                # Count how many requests are currently in the set (the window)
                pipe.zcard(key)

                # Set the key to expire slightly after the window (auto-cleanup)
                pipe.expire(key, window + 1)

                # Execute pipeline
                results = pipe.execute()

                # results[0] = number of removed items
                # results[1] = number of added items (always 1)
                # results[2] = current count (ZCARD result)
                current_request_count = results[2]

                # Check against limit
                if current_request_count > limit:
                    return jsonify({
                        "error": "Too many requests",
                        "message": f"Limit is {limit} requests per {window} seconds."
                    }), 429

            except redis.ConnectionError:
                # If Redis is down, allow the request
                print("Warning: Redis connection failed, rate limiting skipped.")
                pass

            return f(*args, **kwargs)
        return wrapper
    return decorator