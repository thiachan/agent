#!/bin/bash
echo "Starting GSSE AI Center Backend Server..."
cd "$(dirname "$0")"
source venv/bin/activate
python main.py

