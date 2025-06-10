"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module rate limiter.
"""

# pylint: disable=logging-fstring-interpolation,too-many-statements

import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class RateLimiter:
    def __init__(self, max_requests, per_seconds):
        self._semaphore = asyncio.Semaphore(max_requests)
        self._interval = per_seconds / max_requests

    async def request(self, task, *args):
        # Acquire the semaphore to limit concurrency
        async with self._semaphore:
            # Call the task and apply a delay for rate limiting
            result = await task(*args)
            await asyncio.sleep(self._interval)
            return result
