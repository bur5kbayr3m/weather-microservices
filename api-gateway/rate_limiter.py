"""
Rate limiting module for API endpoints.
Implements:
- Request rate limiting with sliding window algorithm
- Per-user and per-IP rate limiting
- Configurable limits per endpoint
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional, Any, Callable
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify


class RateLimitConfig:
    """Rate limiting configuration."""
    
    def __init__(self):
        """Initialize rate limit configuration from environment."""
        self.ENABLE_RATE_LIMITING = os.getenv(
            'ENABLE_RATE_LIMITING', 'true'
        ).lower() == 'true'
        
        # Default limits (requests per minute)
        self.DEFAULT_REQUESTS_PER_MINUTE = int(
            os.getenv('DEFAULT_REQUESTS_PER_MINUTE', 60)
        )
        
        # Endpoint-specific limits
        self.LOGIN_REQUESTS_PER_MINUTE = int(
            os.getenv('LOGIN_REQUESTS_PER_MINUTE', 5)
        )
        
        self.WEATHER_REQUESTS_PER_MINUTE = int(
            os.getenv('WEATHER_REQUESTS_PER_MINUTE', 30)
        )
        
        # Rate limit by user or IP
        self.RATE_LIMIT_BY = os.getenv('RATE_LIMIT_BY', 'ip')  # 'ip' or 'user'
        
        # Storage backend type
        self.BACKEND = os.getenv('RATE_LIMIT_BACKEND', 'memory')  # 'memory' or 'redis'


class SlidingWindowCounter:
    """
    Sliding window counter for rate limiting.
    Tracks requests in a time window using FIFO queue.
    """
    
    def __init__(self, window_minutes: int = 1):
        """
        Initialize sliding window counter.
        
        Args:
            window_minutes: Size of the time window in minutes
        """
        self.window_minutes = window_minutes
        self.requests: deque[datetime] = deque()  # Stores timestamps of requests
    
    def add_request(self) -> int:
        """
        Add a request timestamp to the counter.
        
        Returns:
            Number of requests in the current window
        """
        now = datetime.now(timezone.utc)
        
        # Remove requests outside the window
        cutoff_time = now - timedelta(minutes=self.window_minutes)
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
        
        # Add current request
        self.requests.append(now)
        
        return len(self.requests)
    
    def get_request_count(self) -> int:
        """Get current number of requests in the window."""
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=self.window_minutes)
        
        # Count requests within window
        return sum(1 for t in self.requests if t > cutoff_time)
    
    def get_reset_time(self) -> datetime:
        """Get when the oldest request in the window will expire."""
        if self.requests:
            oldest = self.requests[0]
            return oldest + timedelta(minutes=self.window_minutes)
        
        return datetime.now(timezone.utc) + timedelta(minutes=self.window_minutes)


class RateLimiter:
    """
    Rate limiter using in-memory sliding window counter.
    For production, consider using Redis backend.
    """
    
    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter."""
        self.config = config
        self.counters: Dict[str, SlidingWindowCounter] = defaultdict(
            lambda: SlidingWindowCounter(window_minutes=1)
        )
    
    def _get_identifier(self) -> str:
        """
        Get client identifier (IP address or user ID).
        
        Returns:
            Client identifier string
        """
        if self.config.RATE_LIMIT_BY == 'user':
            # Use user from request context if available
            user_id = getattr(request, 'user_id', None)
            if user_id:
                return f"user:{user_id}"
        
        # Fall back to IP address
        return f"ip:{self._get_client_ip()}"
    
    @staticmethod
    def _get_client_ip() -> str:
        """Get client IP address from request, considering proxies."""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or '0.0.0.0'
    
    def check_rate_limit(
        self,
        limit: int,
        window_minutes: int = 1
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if request should be allowed based on rate limit.
        
        Args:
            limit: Maximum requests allowed in the window
            window_minutes: Time window in minutes
            
        Returns:
            Tuple of (is_allowed, response_headers)
            response_headers contains rate limit info
        """
        if not self.config.ENABLE_RATE_LIMITING:
            return True, None
        
        identifier = self._get_identifier()
        counter = self.counters[identifier]
        
        # For proper sliding window with different windows,
        # we should create separate counters per window
        # This is a simplified version
        request_count = counter.add_request()
        
        reset_time = counter.get_reset_time()
        reset_timestamp = int(reset_time.timestamp())
        
        remaining = max(0, limit - request_count)
        
        headers = {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_timestamp),
        }
        
        if request_count > limit:
            return False, headers
        
        return True, headers
    
    def get_status(self, identifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Get rate limit status for a client.
        
        Args:
            identifier: Client identifier (uses current client if None)
            
        Returns:
            Dictionary with rate limit info
        """
        if identifier is None:
            identifier = self._get_identifier()
        
        counter = self.counters.get(identifier)
        
        if not counter:
            return {
                'identifier': identifier,
                'request_count': 0,
                'reset_time': None
            }
        
        return {
            'identifier': identifier,
            'request_count': counter.get_request_count(),
            'reset_time': counter.get_reset_time().isoformat(),
        }


class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed systems.
    Use this for production with multiple API Gateway instances.
    """
    
    def __init__(self, config: RateLimitConfig, redis_client: Any) -> None:
        """
        Initialize Redis rate limiter.
        
        Args:
            config: Rate limit configuration
            redis_client: Redis client instance
        """
        self.config = config
        self.redis = redis_client
    
    def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_minutes: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit using Redis.
        
        Args:
            identifier: Client identifier
            limit: Maximum requests
            window_minutes: Time window
            
        Returns:
            Tuple of (is_allowed, headers)
        """
        key = f"rate_limit:{identifier}:{window_minutes}"
        current = self.redis.incr(key)
        
        if current == 1:
            # First request, set expiration
            self.redis.expire(key, window_minutes * 60)
        
        ttl = self.redis.ttl(key)
        reset_timestamp = int(datetime.now(timezone.utc).timestamp()) + ttl
        
        remaining = max(0, limit - current)
        
        headers = {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_timestamp),
        }
        
        if current > limit:
            return False, headers
        
        return True, headers


def rate_limit(requests_per_minute: Optional[int] = None) -> Callable:  # type: ignore[return-value]
    """
    Decorator to apply rate limiting to an endpoint.
    
    Args:
        requests_per_minute: Max requests per minute (uses default if None)
    
    Usage:
        @app.route('/api/weather')
        @rate_limit(requests_per_minute=30)
        def get_weather():
            ...
    """
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[no-untyped-def]
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
            from flask import current_app
            
            config: Any = getattr(current_app, 'rate_limit_config', None)
            rate_limiter: Any = getattr(current_app, 'rate_limiter', None)
            if config is None or rate_limiter is None:
                return jsonify({'error': 'Rate limiter unavailable'}), 500
            
            limit = (
                requests_per_minute
                if requests_per_minute is not None
                else int(getattr(config, 'DEFAULT_REQUESTS_PER_MINUTE', 60))
            )
            
            is_allowed: bool
            headers: Dict[str, Any]
            is_allowed, headers = rate_limiter.check_rate_limit(limit)
            
            if not is_allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {limit} requests per minute allowed',
                    'retry_after': headers.get('X-RateLimit-Reset')
                })
                response.status_code = 429
                
                # Add rate limit headers
                if headers:
                    for key, value in headers.items():
                        response.headers[key] = value
                
                return response
            
            # Add rate limit headers to response
            if headers:
                from flask import make_response
                
                @wraps(f)
                def with_headers(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
                    resp = make_response(f(*args, **kwargs))
                    for key, value in headers.items():
                        resp.headers[key] = value
                    return resp
                
                return with_headers(*args, **kwargs)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


class RateLimitStatus:
    """Helper class to provide rate limit status endpoints."""
    
    @staticmethod
    def get_limits_info(rate_limiter: RateLimiter) -> Dict[str, Any]:
        """Get rate limit information for current client."""
        return rate_limiter.get_status()
