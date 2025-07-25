#!/bin/bash

# Resolve the absolute path to the project root directory (one level up from script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Add the project root directory to the PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Change to the project root directory
cd "$PROJECT_ROOT" || exit 1

# Run the synthetic data server script
python src/synthetic/api/chat_endpoint.py
