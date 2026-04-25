#!/bin/bash

python -m uvicorn app.core.main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude '.venv/*'
