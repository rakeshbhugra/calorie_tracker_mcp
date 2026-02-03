"""
OAuth Proxy Routes for Claude.ai Integration

These endpoints proxy OAuth requests to Keycloak, allowing Claude.ai to
authenticate through our MCP server which then redirects to Keycloak.

Flow:
1. Claude.ai → GET /.well-known/oauth-authorization-server → Returns our endpoints
2. Claude.ai → GET /authorize → Redirects to Keycloak
3. User authenticates with Keycloak → Redirects to Claude.ai callback
4. Claude.ai → POST /token → We proxy to Keycloak → Returns access token
"""

from urllib.parse import urlencode

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from .config import (
    OAUTH_AUDIENCE,
    OAUTH_CLIENT_SECRET,
    KEYCLOAK_AUTH_URL,
    KEYCLOAK_TOKEN_URL,
)


async def oauth_metadata(request: Request) -> JSONResponse:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    base_url = str(request.base_url).rstrip("/")

    metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
    }
    return JSONResponse(metadata)


async def authorize(request: Request) -> RedirectResponse:
    """Redirect to Keycloak authorization endpoint."""
    params = dict(request.query_params)

    if "client_id" not in params:
        params["client_id"] = OAUTH_AUDIENCE

    # Filter scopes - keep only Keycloak-supported scopes
    # Claude.ai requests 'claudeai' scope which Keycloak doesn't have
    if "scope" in params:
        supported_scopes = {"openid", "profile", "email", "offline_access"}
        requested_scopes = set(params["scope"].split())
        filtered_scopes = requested_scopes & supported_scopes
        filtered_scopes.add("openid")  # Always include openid
        params["scope"] = " ".join(filtered_scopes)
        print(f"Filtered scopes: {requested_scopes} -> {filtered_scopes}")

    keycloak_url = f"{KEYCLOAK_AUTH_URL}?{urlencode(params)}"
    print(f"Redirecting to Keycloak: {keycloak_url}")
    return RedirectResponse(url=keycloak_url, status_code=302)


async def token(request: Request) -> JSONResponse:
    """Proxy token requests to Keycloak."""
    form_data = await request.form()
    data = dict(form_data)

    if "client_id" not in data:
        data["client_id"] = OAUTH_AUDIENCE
    if "client_secret" not in data and OAUTH_CLIENT_SECRET:
        data["client_secret"] = OAUTH_CLIENT_SECRET

    print(f"Proxying token request to Keycloak: grant_type={data.get('grant_type')}")

    async with httpx.AsyncClient() as client:
        response = await client.post(KEYCLOAK_TOKEN_URL, data=data)

    if response.status_code == 200:
        return JSONResponse(response.json())
    else:
        print(f"Token error from Keycloak: {response.text}")
        return JSONResponse(
            response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text},
            status_code=response.status_code
        )


def register_oauth_routes(mcp) -> None:
    """Register OAuth proxy routes with the MCP server."""
    mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(oauth_metadata)
    mcp.custom_route("/authorize", methods=["GET"])(authorize)
    mcp.custom_route("/token", methods=["POST"])(token)
