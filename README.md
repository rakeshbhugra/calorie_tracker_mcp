# Calorie Tracker MCP

MCP server for tracking calories with OAuth authentication (Keycloak).

## Quick Start (No Auth)

```bash
uv run calorie-tracker
```

Server runs at `http://localhost:8000/mcp`

## With OAuth (Keycloak)

### 1. Start Keycloak

```bash
docker compose up -d
```

Keycloak runs at `http://localhost:8180` (admin/admin)

### 2. Configure Keycloak

#### Create Realm
1. Open http://localhost:8180 → Login (admin/admin)
2. Click dropdown (top-left, says "Keycloak") → **Create realm**
3. Name: `mcp` → **Create**

#### Create Client
1. Go to **Clients** → **Create client**
2. **General Settings:**
   - Client ID: `calorie-tracker`
   - Click **Next**
3. **Capability config:**
   - Client authentication: **ON**
   - Authorization: **OFF**
   - Authentication flow: Check **Standard flow** and **Direct access grants**
   - Service accounts roles: **ON** (enables client credentials flow)
   - Click **Next**
4. **Login settings:**
   - Valid redirect URIs:
     ```
     http://localhost:8000/*
     https://claude.ai/*
     https://*.trycloudflare.com/*
     ```
   - Valid post logout redirect URIs: `+` (same as redirect URIs)
   - Web origins: `+` (same as redirect URIs)
   - Click **Save**

#### Get Client Secret
1. Go to **Clients** → `calorie-tracker` → **Credentials** tab
2. Copy the **Client secret**

#### (Optional) Create Test User
For browser-based login flow:
1. Go to **Users** → **Add user**
2. Username: `testuser` → **Create**
3. Go to **Credentials** tab → **Set password**
4. Set password, turn OFF "Temporary" → **Save**

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
OAUTH_ISSUER_URL=http://localhost:8180/realms/mcp
OAUTH_AUDIENCE=calorie-tracker
OAUTH_CLIENT_SECRET=your-client-secret-from-keycloak
```

### 4. Run Server

```bash
uv run calorie-tracker
```

### 5. Test with Chat Client

```bash
uv run calorie-chat
```

This uses client credentials flow (machine-to-machine) to get a token from Keycloak.

### 6. Connect to Claude.ai

To connect your MCP server to Claude.ai, both your MCP server and Keycloak need to be publicly accessible.

#### Step 1: Restart Keycloak with Proxy Settings
The docker-compose.yml is already configured with proxy settings. Restart Keycloak:
```bash
docker compose down && docker compose up -d
```

#### Step 2: Start Cloudflare Tunnels
Open **two terminals** and run:

**Terminal 1 - MCP Server Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8000
```
Copy the URL (e.g., `https://abc-xyz.trycloudflare.com`)

**Terminal 2 - Keycloak Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8180
```
Copy the URL (e.g., `https://def-uvw.trycloudflare.com`)

#### Step 3: Update Environment
Edit `.env` with your Keycloak tunnel URL:
```bash
OAUTH_ISSUER_URL=https://your-keycloak-tunnel.trycloudflare.com/realms/mcp
OAUTH_AUDIENCE=calorie-tracker
OAUTH_CLIENT_SECRET=your-client-secret-from-keycloak
```

#### Step 4: Restart MCP Server
```bash
# Stop existing server (Ctrl+C) then:
uv run calorie-tracker
```

#### Step 5: Configure Keycloak Redirect URIs
1. Go to Keycloak (use your tunnel URL) → **Clients** → `calorie-tracker` → **Settings**
2. Add to **Valid redirect URIs**:
   ```
   https://claude.ai/*
   https://*.trycloudflare.com/*
   ```
3. Add to **Web origins**:
   ```
   https://claude.ai
   ```
4. **Save**

#### Step 6: Configure Claude.ai
1. Go to [Claude.ai](https://claude.ai) → **Settings** → **MCP** → **Add Custom Connector**
2. **Name:** `calorie-tracker-mcp`
3. **URL:** `https://your-mcp-tunnel.trycloudflare.com/mcp`
4. Leave OAuth fields **empty** (OAuth discovery is automatic)
5. Click **Add**
6. You'll be redirected to Keycloak login
7. Login with your Keycloak user → Connection complete!

## How OAuth Proxy Works

The MCP server includes OAuth proxy routes that allow Claude.ai to authenticate through our server, which then redirects to Keycloak:

1. Claude.ai → `GET /.well-known/oauth-authorization-server` → Returns our OAuth endpoints
2. Claude.ai → `GET /authorize` → Redirects to Keycloak login
3. User authenticates → Keycloak redirects to `claude.ai/api/mcp/auth_callback`
4. Claude.ai → `POST /token` → We proxy to Keycloak → Returns access token
5. Claude.ai uses token to call MCP tools

## Tools

| Tool | Description |
|------|-------------|
| `log_meal` | Log a meal with calories |
| `get_today_summary` | Get today's meals and totals |

## Project Structure

```
src/calorie_tracker/
├── __init__.py      # Package init
├── config.py        # Configuration (env vars)
├── storage.py       # File-based meal storage
├── auth.py          # OAuth token verification (JWT/JWKS)
├── oauth_proxy.py   # OAuth proxy routes for Claude.ai
├── server.py        # MCP server + tools
└── host.py          # Chat client

data/
└── meals.json       # Meal storage (created automatically)
```

## Troubleshooting

### "The information you're about to submit is not secure"
This warning appears if Keycloak isn't configured for proxy mode. Ensure these environment variables are set in `docker-compose.yml`:
```yaml
environment:
  KC_PROXY: edge
  KC_HOSTNAME_STRICT: "false"
  KC_HOSTNAME_STRICT_HTTPS: "false"
```
Then restart Keycloak: `docker compose down && docker compose up -d`

### "Invalid client or Invalid client credentials"
The client secret in `.env` doesn't match Keycloak. Go to Keycloak → Clients → `calorie-tracker` → Credentials and copy the correct secret.

### OAuth redirects to localhost
Your `.env` still has the localhost URL. Update `OAUTH_ISSUER_URL` to your Keycloak Cloudflare tunnel URL:
```bash
OAUTH_ISSUER_URL=https://your-keycloak-tunnel.trycloudflare.com/realms/mcp
```

### "/sse returns 404"
This MCP server uses streamable HTTP transport, not SSE. Use `/mcp` endpoint:
```
https://your-tunnel.trycloudflare.com/mcp
```

### "Invalid scopes: claudeai"
The server filters out unsupported scopes automatically. If you see this, the server needs to be restarted with the latest code.

### "unauthorized_client: Client not enabled to retrieve service account"
Enable **Service accounts roles** in Keycloak client settings.

### Keycloak data lost on restart
Add volume mount to `docker-compose.yml` (already configured):
```yaml
volumes:
  - keycloak_data:/opt/keycloak/data
```
