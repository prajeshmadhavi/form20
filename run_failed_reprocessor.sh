#!/bin/bash

# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Run the failed PDF reprocessor
python failed_pdf_reprocessor.py --all

echo "Batch reprocessing completed"
