"""
Root Vercel Serverless Function entry point for monorepo deployments.
Exports FastAPI `app` from apps/api/main.py.
"""
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
apps_api_dir = os.path.join(root_dir, "apps", "api")
if apps_api_dir not in sys.path:
    sys.path.insert(0, apps_api_dir)

from main import app
