import os
import redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls) -> 'RedisClient':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        """Initialize Redis connection"""
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        try:
            self._client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self._client.ping()
            logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self._client = None

    @property
    def client(self) -> Optional[redis.Redis]:
        """Get Redis client instance"""
        if self._client is None:
            self._connect()
        return self._client

    def is_connected(self) -> bool:
        """Check if Redis is connected and available"""
        try:
            if self._client is None:
                return False
            self._client.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking Redis connection: {e}")
            return False

# Global Redis client instance
redis_client = RedisClient()

def get_redis_client() -> Optional[redis.Redis]:
    """Dependency function to get Redis client"""
    return redis_client.client
