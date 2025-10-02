import json
import logging
from typing import Dict, Any, Optional
from ..db.redis_client import get_redis_client
import redis

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.redis_client = get_redis_client()
        self.default_ttl = default_ttl
        self.key_prefix = "order:"

    def _get_order_key(self, order_id: str) -> str:
        """Generate cache key for order"""
        return f"{self.key_prefix}{order_id}"

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order from cache"""
        if not self.redis_client:
            logger.warning("Redis client not available, cache miss")
            return None

        try:
            cache_key = self._get_order_key(order_id)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for order {order_id}")
                return json.loads(cached_data)
            
            logger.info(f"Cache miss for order {order_id}")
            return None
            
        except redis.ConnectionError:
            logger.warning(f"Redis connection error when getting order {order_id}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for order {order_id}: {e}")
            self._delete_order(order_id)
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting order {order_id} from cache: {e}")
            return None

    def set_order(self, order_id: str, order_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set order in cache"""
        if not self.redis_client:
            logger.warning("Redis client not available, cannot cache order")
            return False

        try:
            cache_key = self._get_order_key(order_id)
            ttl = ttl or self.default_ttl
            
            serialized_data = json.dumps(order_data, default=str)
            
            result = self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if result:
                logger.info(f"Successfully cached order {order_id} with TTL {ttl}s")
                return True
            else:
                logger.warning(f"Failed to cache order {order_id}")
                return False
                
        except redis.ConnectionError:
            logger.warning(f"Redis connection error when caching order {order_id}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error for order {order_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error caching order {order_id}: {e}")
            return False

    def _delete_order(self, order_id: str) -> bool:
        """Delete order from cache"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._get_order_key(order_id)
            result = self.redis_client.delete(cache_key)
            logger.info(f"Deleted order {order_id} from cache: {bool(result)}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting order {order_id} from cache: {e}")
            return False

    def invalidate_order(self, order_id: str) -> bool:
        """Invalidate order cache (public method for external use)"""
        return self._delete_order(order_id)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}

        try:
            info = self.redis_client.info()
            return {
                "status": "connected",
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}

    def health_check(self) -> bool:
        """Check if cache is healthy"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
