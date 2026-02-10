import asyncio
import json
import logging
import redis
import uuid

log = logging.getLogger(__name__)


async def renew_lock_periodically(
    lock, renewal_interval_secs: int = 300, lock_name: str = "lock"
):
    """
    Periodically renew a Redis lock to keep it alive during long-running operations.

    Args:
        lock: RedisLock instance to renew
        renewal_interval_secs: Interval in seconds between renewal attempts (default: 300 = 5 minutes)
        lock_name: Name of the lock for logging purposes

    This function runs in a loop until the lock is no longer held or renewal fails.
    It should be run as an asyncio task and cancelled when the operation completes.
    """
    try:
        while True:
            await asyncio.sleep(renewal_interval_secs)
            if lock and lock.lock_obtained:
                renewed = lock.renew_lock()
                if renewed:
                    log.debug(f"Renewed {lock_name}")
                else:
                    log.warning(f"Failed to renew {lock_name}")
                    break
    except asyncio.CancelledError:
        log.debug(f"Lock renewal task for {lock_name} cancelled")
        raise
    except Exception as e:
        log.error(f"Error in lock renewal task for {lock_name}: {e}")


class RedisLock:
    def __init__(self, redis_url, lock_name, timeout_secs):
        self.lock_name = lock_name
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs
        self.lock_obtained = False
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def acquire_lock(self):
        try:
            # nx=True will only set this key if it _hasn't_ already been set
            self.lock_obtained = self.redis.set(
                self.lock_name, self.lock_id, nx=True, ex=self.timeout_secs
            )
            return self.lock_obtained
        except Exception as e:
            print(f"Error acquiring Redis lock: {e}")
            return False

    def renew_lock(self):
        try:
            # Verify we own the lock before renewing to prevent other replicas from stealing it
            lock_value = self.redis.get(self.lock_name)
            if lock_value and lock_value == self.lock_id:
                # Only renew if we own the lock
                return self.redis.set(
                    self.lock_name, self.lock_id, xx=True, ex=self.timeout_secs
                )
            else:
                # We don't own this lock, cannot renew
                return False
        except Exception as e:
            print(f"Error renewing Redis lock: {e}")
            return False

    def release_lock(self):
        try:
            lock_value = self.redis.get(self.lock_name)
            if lock_value and lock_value == self.lock_id:
                self.redis.delete(self.lock_name)
        except Exception as e:
            print(f"Error releasing Redis lock: {e}")


class RedisDict:
    def __init__(self, name, redis_url):
        self.name = name
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def __setitem__(self, key, value):
        serialized_value = json.dumps(value)
        self.redis.hset(self.name, key, serialized_value)

    def __getitem__(self, key):
        value = self.redis.hget(self.name, key)
        if value is None:
            raise KeyError(key)
        return json.loads(value)

    def __delitem__(self, key):
        result = self.redis.hdel(self.name, key)
        if result == 0:
            raise KeyError(key)

    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    def __len__(self):
        return self.redis.hlen(self.name)

    def keys(self):
        return self.redis.hkeys(self.name)

    def values(self):
        return [json.loads(v) for v in self.redis.hvals(self.name)]

    def items(self):
        return [(k, json.loads(v)) for k, v in self.redis.hgetall(self.name).items()]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        self.redis.delete(self.name)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if hasattr(other, "items") else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]
