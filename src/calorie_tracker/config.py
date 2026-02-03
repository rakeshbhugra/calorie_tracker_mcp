"""Configuration for Calorie Tracker MCP Server."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Server settings
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
RESOURCE_SERVER_URL = os.getenv("RESOURCE_SERVER_URL", f"http://localhost:{SERVER_PORT}")

# OAuth settings (Keycloak)
OAUTH_ISSUER_URL = os.getenv("OAUTH_ISSUER_URL")  # e.g., http://localhost:8180/realms/mcp
OAUTH_AUDIENCE = os.getenv("OAUTH_AUDIENCE", "calorie-tracker")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")

# Keycloak endpoints (derived from issuer URL)
KEYCLOAK_AUTH_URL = f"{OAUTH_ISSUER_URL}/protocol/openid-connect/auth" if OAUTH_ISSUER_URL else None
KEYCLOAK_TOKEN_URL = f"{OAUTH_ISSUER_URL}/protocol/openid-connect/token" if OAUTH_ISSUER_URL else None

# Storage
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent / "data"))
MEALS_FILE = DATA_DIR / "meals.json"

# Nutrition targets
DAILY_CALORIE_GOAL = int(os.getenv("DAILY_CALORIE_TARGET", "2000"))
