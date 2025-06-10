#!/bin/bash

source common.sh
cd "$(dirname "$0")"
runme src/main.py ${AICODER_HTTP_PORT}
