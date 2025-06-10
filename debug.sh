#!/bin/bash

echo "============== Starting REDIS server =============="
docker-compose --env-file .env.devel up redis -d
echo "============== REDIS server started ==============="

export PYTHON_VER=3.11.3
set -a
source .env.devel
source app/common.sh
update_git_commit_hash
set +a
if [ ! -d ".venv" ]; then
    pyenv install -s ${PYTHON_VER}
    ~/.pyenv/versions/${PYTHON_VER}/bin/python -m venv .venv
fi
source .venv/bin/activate
pip install pip-tools
pip install -r app/requirements.txt
pre-commit install
runme app/src/main.py ${AICODER_HTTP_PORT}
