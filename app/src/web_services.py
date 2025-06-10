"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module: WebServices API Functions
"""

# pylint: disable=logging-fstring-interpolation,too-many-statements

import configparser
import logging
import os
import datetime as dt
import asyncio
import uvloop
import web_models
import uuid
import time

from openai import OpenAI
from contextlib import asynccontextmanager
from math import ceil
from typing import List
from cachetools import TTLCache

from hypercorn.asyncio import serve
from hypercorn.config import Config

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from fastapi.security import APIKeyHeader
from fastapi import Security

from utils import Utils
from aicoder import AICoder
from redis_cache import RedisCache
from constants import LARGE_MAX_LRU_CACHE_SIZE, TTL_EXPIRATION_IN_SECS, OPENAI_API_KEY

logger = logging.getLogger()
client = OpenAI()
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# Custom middleware to add Cache-Control header to all responses
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # if "force_retrieve=true" in request.url.query:
        #     return response
        # if not any(
        #     x in request.url.path
        #     for x in ["/redis/"]
        # ):
        #     response.headers["Cache-Control"] = f"public, max-age={find_seconds_until_next_hour()}"
        logger.debug(f"response headers: {response.headers}")
        return response


class WebServices:
    """WebServices HTTP API Functions"""

    api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

    def __init__(self, http_port: int, redis_cache: RedisCache):
        self.__http_port = http_port
        self.__redis_cache = redis_cache
        self.__aicoder = AICoder()
        # Configure access logger for logging requests
        self.__access_logger = logging.getLogger("access")
        self.__access_logger.setLevel(logging.INFO)
        # Create a file handler for access logs
        access_file_handler = logging.FileHandler("access.log")
        access_file_handler.setLevel(logging.INFO)
        # Create a formatter and set it for the access file handler
        access_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        access_file_handler.setFormatter(access_formatter)
        # Add the file handler to the access logger
        self.__access_logger.addHandler(access_file_handler)
        logger.info(f"HTTP_PORT={self.__http_port}")

    def configure_webapp_routes(self):
        """
        Configures routes for the webapp.
        Returns:
            Response: HTTP response.
        """

        # In-memory request count dictionary
        # Create a TTL cache with max size TTL TTL_EXPIRATION_IN_SECS
        request_counts = TTLCache(maxsize=LARGE_MAX_LRU_CACHE_SIZE, ttl=TTL_EXPIRATION_IN_SECS)

        current_version = "unknown"
        try:
            # Parse the bumpversion.cfg file
            config = configparser.ConfigParser()
            version_file = os.path.join(os.getcwd(), "bumpversion.cfg")
            logger.debug(f"Version file path: {version_file}")
            config.read(version_file)
            # Get the current version from the configuration
            current_version = config["bumpversion"]["current_version"]
        except Exception as ex:
            logger.error(f"Error: {ex}")
            SystemExit(1)

        async def service_name_identifier(request: Request):
            service = request.headers.get("Service-Name")
            return service

        async def custom_callback(request: Request, response: Response, pexpire: int):
            """
            default callback when too many requests
            :param request:
            :param pexpire: The remaining milliseconds
            :param response:
            :return:
            """
            expire = ceil(pexpire / 1000)

            uid = Utils().get_client_ip(request)
            # Log the number of requests that were blocked
            logger.warning(
                "Too many requests from %s. Retry after %d seconds. Total requests: %d",
                uid,
                expire,
                f"{request_counts.get(uid, 0)}",
            )

            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too Many Requests. Retry after {expire} seconds.",
                headers={"Retry-After": str(expire)},
            )

        # Lifespan event handler for setup and teardown
        @asynccontextmanager
        async def lifespan(_: FastAPI):
            await FastAPILimiter.init(
                redis=await self.__redis_cache.connect_to_redis(),
                identifier=service_name_identifier,
                http_callback=custom_callback,
            )
            yield
            await FastAPILimiter.close()

        app = FastAPI(
            lifespan=lifespan,
            title="5G AICoder Server",
            description="HTTP API server that integrates with AI, TTS and News APIs",
            version=current_version,  # Update this version as needed
        )
        # Add Gzip middleware
        app.add_middleware(GZipMiddleware, minimum_size=1024)
        # Add middleware globally
        app.add_middleware(CacheControlMiddleware)

        def verify_api_key(api_key: str = Security(self.api_key_header)):
            if api_key != f"Bearer {OPENAI_API_KEY}":
                raise HTTPException(status_code=403, detail="Invalid API Key")
            return api_key

        @app.get("/v1/models", response_model=web_models.ModelListResponse)
        async def list_models():
            models = [
                {"id": "5g-aicoder", "created": int(time.time()), "owned_by": "QA team"},
                {"id": "text-embedding-ada-002", "created": int(time.time()), "owned_by": "QA team"},
            ]
            return {"object": "list", "data": models}

        @app.post(
            "/v1/chat/completions",
            response_model=web_models.ChatCompletionResponse,
            dependencies=[Depends(RateLimiter(times=10, seconds=60)), Depends(verify_api_key)],
        )
        async def chat_completions(request: web_models.ChatCompletionRequest):
            try:
                user_message = request.messages[0].content
                content = self.__aicoder.ask_aicoder(user_message)
                if content:
                    return {
                        "id": str(uuid.uuid4()),
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": content},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
                    }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.exception_handler(HTTPException)
        async def openai_error_handler(request, exc):
            return JSONResponse(
                status_code=exc.status_code, content={"error": {"message": exc.detail, "type": "server_error"}}
            )

        @app.post(
            "/retrain",
            response_model=List[str],
            dependencies=[
                Depends(RateLimiter(times=1, seconds=10)),
            ],
        )
        async def retrain_from_new_code():
            response = self.__aicoder.retrain_aicoder()
            if response:
                return JSONResponse(content={"status": "OK"}, status_code=status.HTTP_200_OK)
            else:
                return JSONResponse(content={"status": "Not Found"}, status_code=status.HTTP_404_NOT_FOUND)

        @app.get("/", include_in_schema=False)
        @app.get("/health", include_in_schema=False)
        async def health_check():
            """Health Checking"""
            logger.debug("AICoder API WebServices!")
            json_content = {"status": "ok"}
            return JSONResponse(content=json_content, status_code=status.HTTP_200_OK)

        @app.get("/redis/all")
        async def get_all_redis_keys():
            """Get REDIS All Keys"""
            # Get all keys
            json_content = await self.__redis_cache.get_all_redis_keys()
            return JSONResponse(content=json_content, status_code=status.HTTP_200_OK)

        @app.delete(
            "/redis/key/delete",
            dependencies=[
                Depends(RateLimiter(times=1, seconds=10)),
            ],
        )
        async def redis_delete_entry_by_key(request: Request, key: str):
            """Cleanup REDIS entry by key"""
            json_content = await self.__redis_cache.delete_entry_by_key(key)
            return JSONResponse(
                content=json_content,
                status_code=(status.HTTP_200_OK if json_content["status"] == "ok" else status.HTTP_500_INTERNAL_SERVER_ERROR),
            )

        @app.delete(
            "/redis/pattern/delete",
            dependencies=[
                Depends(RateLimiter(times=1, seconds=10)),
            ],
        )
        async def redis_delete_entries_by_pattern(request: Request, pattern: str):
            """Cleanup REDIS entry by pattern"""
            json_content = await self.__redis_cache.delete_entries_by_pattern(pattern)
            return JSONResponse(
                content=json_content,
                status_code=(status.HTTP_200_OK if json_content["status"] == "ok" else status.HTTP_500_INTERNAL_SERVER_ERROR),
            )

        @app.delete(
            "/redis/cleanup",
            dependencies=[
                Depends(RateLimiter(times=1, seconds=10)),
            ],
        )
        async def redis_cleanup(request: Request):
            """Cleanup REDIS entries"""
            json_content = await self.__redis_cache.cleanup_all_redis_entries()
            return JSONResponse(
                content=json_content,
                status_code=(status.HTTP_200_OK if json_content["status"] == "ok" else status.HTTP_500_INTERNAL_SERVER_ERROR),
            )

        @app.get(
            "/server/stats",
            dependencies=[],
        )
        async def server_stats(request: Request):
            """Server statistics"""
            ips = Utils().serialize_cache(request_counts)
            return JSONResponse(
                content={
                    "ips": ips,
                    "users": request_counts.currsize,
                },
                status_code=(status.HTTP_200_OK),
            )

        # Middleware for logging requests
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            uid = Utils().get_client_ip(request)
            # Increment the request count for the client
            value = request_counts.get(uid, 0)
            if isinstance(value, tuple):
                request_counts[uid] = (value[0] + 1, dt.datetime.now().isoformat())
            else:
                request_counts[uid] = (1, dt.datetime.now().isoformat())
            start_time = dt.datetime.now()
            response = await call_next(request)
            process_time = (dt.datetime.now() - start_time).total_seconds()
            self.__access_logger.debug(
                f"UID: {uid} - {request.method} {request.url.path}"
                f"Status: {response.status_code} - Duration: {process_time:.4f}s"
            )
            # Update the user count using the cache's currsize property
            return response

        try:
            # Configure Hypercorn to listen single HTTP/1.1
            # Google Cloud Run, TLS termination happens at the load balancer level, not inside the container.
            # This means your container itself cannot directly manage SSL or enable HTTP/2 through TLS.
            # Instead, Google Cloud Run supports HTTP/2 for the connection between the client and the load balancer,
            # but internally forwards the traffic as HTTP/1.1 to your container.
            config = Config()
            config.bind = [f"0.0.0.0:{self.__http_port}"]  # Host and port
            # config.certfile = os.path.join(AICODER_CERTS_PATH, "cert.pem")  # SSL certificate file
            # config.keyfile = os.path.join(AICODER_CERTS_PATH, "key.pem")  # SSL key file
            config.alpn_protocols = ["h2", "http/1.1"]  # Support HTTP/2 and fallback to HTTP/1.1
            logger.info(f"AICoder WebServices is running on port {self.__http_port} with Hypercorn config: {config}")
            # Run the server
            asyncio.run(serve(app, config))
        except (KeyboardInterrupt, SystemExit):
            logger.warning("Shutting down...")
