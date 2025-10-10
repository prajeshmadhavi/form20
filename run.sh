#!/bin/bash
set -a
source .env
set +a
source venv/bin/activate
python gemini_vision_extractor.py "$@"
