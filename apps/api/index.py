"""
Vercel Serverless Function entry point for FastAPI backend.
Exports `app` instance with sys.path properly configured.
"""
import os
import sys

# Ensure current directory is on sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from main import app
