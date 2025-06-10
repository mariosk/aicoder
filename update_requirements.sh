#!/bin/bash
set -e

# Ensure pip-tools is installed
if ! command -v pip-compile &>/dev/null; then
    echo "pip-tools is not installed. Please install it with 'pip install pip-tools'."
    exit 1
fi

# Check if requirements.in exists
if [ ! -f app/requirements.in ]; then
    cp app/requirements.txt app/requirements.in
fi

# Update requirements.txt from requirements.in
pip-compile --output-file=app/requirements.txt app/requirements.in

# Stage the updated requirements.txt if it changed
if ! git diff --quiet app/requirements.txt; then
    echo "app/requirements.txt has been updated."
    git add app/requirements.txt
fi

exit 0
