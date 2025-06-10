"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module: Helper Singleton class
"""

from pathlib import Path
from fastapi import Request
from constants import HTTP_HEADER_X_FORWARDED_FOR


class Utils:
    _instance = None
    base_dir = Path(__file__).parent

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client_ip(self, request: Request):
        client_ip = request.headers.get(HTTP_HEADER_X_FORWARDED_FOR, "")
        if not client_ip or client_ip in ("127.0.0.1", "::1", ""):
            client_ip = request.client.host
        return client_ip

    def serialize_cache(self, cache):
        return [{"ip": key, "requests": str(value)} for key, value in cache.items()]
