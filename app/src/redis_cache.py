"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module redis cache.
"""

# pylint: disable=logging-fstring-interpolation,too-many-statements

import orjson
import logging
from functools import wraps

import redis.asyncio as aioredis
from constants import (
    LUA_REDIS_SCRIPT,
    TTL_EXPIRATION_IN_SECS,
    AICODER_REDIS_SERVER,
    AICODER_REDIS_PORT,
)

# Set up logging
logger = logging.getLogger(__name__)


class RedisCache:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # Initialize flag
        return cls._instance

    def __init__(self):
        if self._initialized:  # Prevent reinitialization
            return

        # Shared connection parameters
        self._redis_params = {
            # "host": AICODER_REDIS_SERVER,
            # "port": AICODER_REDIS_PORT,
            "decode_responses": False,
            "db": 0,
            "socket_connect_timeout": 20,
            "socket_timeout": 20,
            "socket_keepalive": True,
            "retry_on_timeout": True,
        }
        self._redis_url = f"redis://{AICODER_REDIS_SERVER}:{AICODER_REDIS_PORT}"
        # Add conditional TLS parameters
        # redis_params["ssl_ca_certs"] = os.path.join(AICODER_CERTS_PATH, 'server-ca.pem')
        # redis_params["password"] = AICODER_REDIS_AUTH_PASSWORD
        # self._redis_params["ssl"] = True
        # self._redis_url = f"rediss://{AICODER_REDIS_SERVER}:{AICODER_REDIS_PORT}"
        # self._redis_params["ssl_certfile"] = os.path.join(AICODER_CERTS_PATH, 'server.crt')
        # self._redis_params["ssl_keyfile"] = os.path.join(AICODER_CERTS_PATH, 'server.key')
        # self._redis_params["ssl_ca_certs"] = os.path.join(AICODER_CERTS_PATH, 'ca.crt')

        self._redis_client = None
        self._initialized = True  # Set the initialization flag

    async def connect_to_redis(self):
        if self._redis_client is None:  # Only connect if not already connected
            try:
                logger.info(f"Connecting to REDIS server (redis_url={self._redis_url}): with params: {self._redis_params}")
                self._redis_client = await aioredis.from_url(self._redis_url, **self._redis_params)
                await self._redis_client.ping()
                self._get_key_with_hits = self._redis_client.register_script(LUA_REDIS_SCRIPT)
                logger.info(f"Connected to Redis! Redis-Client object: {self._redis_client} ")
            except Exception as e:
                logger.error(f"Could not connect to Redis: {e}")
                self._redis_client = None
        return self._redis_client

    def _check_client_initialized(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if self._redis_client is None:
                raise RuntimeError("Redis client is not initialized")
            return func(self, *args, **kwargs)

        return wrapper

    async def _get_hit_count(self, key):
        hit_counter_key = f"{key}:hits"
        hit_count = await self._redis_client.get(hit_counter_key)
        return int(hit_count) if hit_count else 0

    # @_check_client_initialized
    async def store_redis_key(self, cache_key: str, cache_value: str, ex=TTL_EXPIRATION_IN_SECS) -> None:
        await self._redis_client.set(cache_key, cache_value, ex=ex)

    # @_check_client_initialized
    async def get_redis_key(self, cache_key: str, expect_json: bool = True) -> str:
        logger.debug(f"Trying to retrieve cache key from REDIS: {cache_key}")
        # retrieved_data = self._redis_client.get(cache_key)
        # Execute the Lua script, passing the key and TTL in seconds as arguments
        # reset the TTL every time someone access this key
        ttl = await self._redis_client.ttl(cache_key)  # Get the time-to-live for the key
        retrieved_data = await self._get_key_with_hits(keys=[cache_key], args=[ttl])
        if retrieved_data:
            logger.debug(f"KEY: {cache_key}, CACHE HIT COUNT: {await self._get_hit_count(cache_key)}")
        logger.debug(f"Retrieved data from REDIS: {retrieved_data is not None} for cache_key: {cache_key}")
        if expect_json and retrieved_data:
            return orjson.loads(retrieved_data)
        return retrieved_data if retrieved_data else None

    # @_check_client_initialized
    async def get_all_redis_keys(self) -> dict:
        keys = await self._redis_client.keys("*")
        json_content = {}
        for key in keys:
            value = await self._redis_client.get(key)
            ttl = await self._redis_client.ttl(key)  # Get the time-to-live for the key
            if not isinstance(value, bytes):
                continue
            key = key.decode("utf-8")
            json_content[f"{key}"] = {"value": f"{value.decode('utf-8')[:16] if value else None}", "ttl": ttl}
        json_content["total"] = len(keys)
        return json_content

    async def key_exists(self, key: str) -> bool:
        return await self._redis_client.exists(key)

    async def cleanup_all_redis_entries(self) -> bool:
        json_content = {}
        try:
            await self._redis_client.flushall()
            json_content["status"] = "ok"
        except Exception as ex:
            logger.error(f"Error cleaning up redis entries: {ex}")
            json_content["status"] = str(ex)
        return json_content

    async def delete_entry_by_key(self, key: str) -> dict:
        json_content = {}
        try:
            logger.info(f"Deleting entry by key: {key}")
            deleted_count = await self._redis_client.delete(key)
            json_content["status"] = "ok"
            json_content["deleted_count"] = deleted_count
        except Exception as ex:
            logger.error(f"Error cleaning up redis entry: {ex}")
            json_content["status"] = "error"
            json_content["error"] = str(ex)
            json_content["error_type"] = type(ex).__name__
        return json_content

    async def delete_entries_by_pattern(self, pattern: str) -> dict:
        json_content = {}
        try:
            logger.warning(f"Deleting entries by pattern: {pattern}")
            keys_to_delete = await self._redis_client.keys(pattern)
            if keys_to_delete:
                await self._redis_client.delete(*keys_to_delete)
                json_content["status"] = "ok"
            else:
                json_content["status"] = f"no REDIS keys found for pattern: {pattern}"
        except Exception as ex:
            logger.error(f"Error cleaning up redis entry: {ex}")
            json_content["status"] = str(ex)
        return json_content
