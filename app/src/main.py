"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module main: The main application module.
"""

# pylint: disable=logging-fstring-interpolation,too-many-statements

import argparse
import logging
import threading
import signal

from constants import (
    AICODER_LOGLEVEL,
)
from web_services import WebServices
from redis_cache import RedisCache

logger = logging.getLogger()


def signal_handler(sig, frame):
    """Handles signals like SIGINT (Ctrl-C)."""
    logger.info("Signal received: %s. Shutting down...", sig)
    stop_event.set()  # Unblock the wait and allow graceful shutdown


if __name__ == "__main__":
    logger.setLevel(AICODER_LOGLEVEL)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - [%(threadName)s]: %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Create argument parser
    parser = argparse.ArgumentParser(description="Process http_port argument (int).")
    # Add integer argument
    parser.add_argument(
        "http_port",
        type=int,
        nargs="?",
        default=9443,
        help="An integer port number (default: 9443)",
    )
    # Parse arguments
    args = parser.parse_args()

    logger.debug("Starting all threads...")

    redis_cache = RedisCache()
    web_services_app = WebServices(args.http_port, redis_cache)
    web_services_app.configure_webapp_routes()
    # Create an Event and wait forever
    stop_event = threading.Event()
    # Register the signal handler for SIGINT (Ctrl-C)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        logger.info("Application is running. Press Ctrl+C to exit.")
        stop_event.wait()  # Wait indefinitely until the event is set
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught. Exiting...")
    finally:
        logger.info("All Threads joined. Shutting down gracefully.")
