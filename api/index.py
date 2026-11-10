"""Ponto de entrada da API no Vercel (função serverless Python). Localmente use:
    uvicorn backend.main:app --port 8000
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app  # noqa: E402,F401  (o Vercel procura a variável `app`)
