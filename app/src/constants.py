"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module constants.
"""

# pylint: disable=logging-fstring-interpolation,too-many-statements

import os
from enum import Enum


def get_boolean_env_var(var_name: str, default: bool = False) -> bool:
    """
    Retrieves an environment variable and returns its boolean equivalent.

    Args:
        var_name (str): The name of the environment variable to retrieve.
        default (bool, optional): The default boolean value to use if the
                                  environment variable is not set. Defaults to False.

    Returns:
        bool: True if the environment variable is set to a truthy value
              ('true', '1', 'yes'), otherwise False.
    """
    value = os.getenv(var_name, str(default)).lower()
    return value in ("true", "1", "yes")


HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", None)
AICODER_LOGLEVEL = os.environ.get("AICODER_LOGLEVEL", "INFO")
AICODER_HTTP_PORT = os.environ.get("AICODER_HTTP_PORT", 9443)

AICODER_5GCODE_PATH = os.environ.get("AICODER_5GCODE_PATH", None)
AICODER_5GCODE_EXTENSIONS = os.environ.get("AICODER_5GCODE_EXTENSIONS", None)
AICODER_FAISS_INDEX_FOLDER = os.environ.get("AICODER_FAISS_INDEX_FOLDER", "faiss")
AICODER_FAISS_INDEX_FILE = os.path.join(AICODER_FAISS_INDEX_FOLDER, os.environ.get("AICODER_FAISS_INDEX_FILE", "faiss_index"))
AICODER_FAISS_INDEX_CHUNKS_FILE = AICODER_FAISS_INDEX_FILE + "_chunks.pkl"
HTTP_HEADER_X_FORWARDED_FOR = "x-forwarded-for"

LARGE_MAX_LRU_CACHE_SIZE = 2048
TTL_EXPIRATION_IN_SECS = 3600

AICODER_REDIS_SERVER = os.environ.get("AICODER_REDIS_SERVER", None)
AICODER_REDIS_PORT = int(os.environ.get("AICODER_REDIS_PORT", 6379))
AICODER_CERTS_PATH = os.environ.get("AICODER_CERTS_PATH", None)

OPENAI_API_KEY = "ef19e6b7-d8e3-4a76-91c0-be50029dd332"
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

LUA_REDIS_SCRIPT = """
local key = KEYS[1]
local hit_counter_key = key .. ":hits"
local ttl_seconds = tonumber(ARGV[1])

-- Increment the hit counter
redis.call("INCR", hit_counter_key)

-- Set or refresh the TTL
redis.call("EXPIRE", key, ttl_seconds)
redis.call("EXPIRE", hit_counter_key, ttl_seconds)

-- Get and return the actual value of the key
return redis.call("GET", key)
"""


class LLMModels(str, Enum):
    # https://huggingface.co/deepseek-ai?search_models=coder
    # https://unsloth.ai/blog/deepseekr1-dynamic
    QUERIES_MODEL = "deepseek-ai/deepseek-coder-1.3b-instruct"
    # QUERIES_MODEL = "deepseek-ai/deepseek-coder-6.7b-instruct"
    EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"
