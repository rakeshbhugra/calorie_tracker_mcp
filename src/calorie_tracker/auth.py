"""OAuth token verification for Keycloak."""

import asyncio

from jwt import PyJWKClient, decode, InvalidTokenError
from mcp.server.auth.provider import AccessToken, TokenVerifier

from .config import OAUTH_ISSUER_URL, OAUTH_AUDIENCE


class OAuthTokenVerifier(TokenVerifier):
    """Verifies OAuth tokens using JWKS (works with Keycloak, Auth0, etc.)."""

    def __init__(self, issuer_url: str, audience: str, algorithms: list[str] | None = None):
        self.issuer_url = issuer_url.rstrip("/")
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self.jwks_url = f"{self.issuer_url}/protocol/openid-connect/certs"
        self.jwks_client = PyJWKClient(self.jwks_url)

    def _normalize_issuer(self, issuer: str) -> str:
        """Normalize issuer URL for comparison (ignore http vs https)."""
        return issuer.rstrip("/").replace("https://", "").replace("http://", "")

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify JWT token and return access information."""
        try:
            signing_key = await asyncio.to_thread(
                self.jwks_client.get_signing_key_from_jwt, token
            )

            # First decode without issuer check to get the actual issuer
            payload = decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                options={
                    "verify_signature": True,
                    "verify_aud": False,  # Keycloak uses 'account' as default audience
                    "verify_exp": True,
                    "verify_iss": False,  # We'll check manually to handle http/https
                }
            )

            # Manually verify issuer (normalize http/https)
            token_issuer = payload.get("iss", "")
            if self._normalize_issuer(token_issuer) != self._normalize_issuer(self.issuer_url):
                print(f"Issuer mismatch: expected {self.issuer_url}, got {token_issuer}")
                return None

            # Verify client_id or azp matches expected audience
            token_client = payload.get("azp") or payload.get("client_id")
            if self.audience and token_client != self.audience:
                print(f"Client mismatch: expected {self.audience}, got {token_client}")
                return None

            scopes = []
            if "scope" in payload:
                scopes = payload["scope"].split()

            return AccessToken(
                token=token,
                client_id=payload.get("azp") or payload.get("client_id", "unknown"),
                scopes=scopes,
                expires_at=payload.get("exp"),
            )

        except InvalidTokenError as e:
            print(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            print(f"Token verification error: {e}")
            return None


def create_oauth_verifier() -> OAuthTokenVerifier:
    """Create OAuth verifier from environment variables."""
    return OAuthTokenVerifier(issuer_url=OAUTH_ISSUER_URL, audience=OAUTH_AUDIENCE)
