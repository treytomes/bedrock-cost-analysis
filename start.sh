#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
pip install -q -e .
python -m bedrock_monitor.main
