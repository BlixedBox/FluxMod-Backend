# AutoMod Backend API

Flask-based REST API for AutoMod rule management with Fluxer OAuth authentication.

## Endpoints

- `GET /api/me` — get current user
- `GET /api/guild-count` — get global guild count
- `GET /api/guilds` — list guilds (authenticated)
- `GET /api/guilds/{guild_id}/rules` — list rules for guild (authenticated)
- `POST /api/guilds/{guild_id}/rules` — create rule (authenticated)
- `PUT /api/rules/{rule_id}` — update rule (authenticated)
- `DELETE /api/rules/{rule_id}` — delete rule (authenticated)
- `GET /login` — OAuth redirect
- `GET /auth` — OAuth callback
- `GET /logout` — clear session

## Local Setup

```bash
uv sync
```

Create `.env` in this directory:

```env
OAUTH_PROVIDER=fluxer
FLUXER_CLIENT_ID=your_client_id
FLUXER_CLIENT_SECRET=your_client_secret
FLUXER_AUTHORIZE_URL=https://api.fluxer.app/v1/oauth2/authorize
FLUXER_TOKEN_URL=https://api.fluxer.app/v1/oauth2/token
FLUXER_API_BASE_URL=https://api.fluxer.app/v1
FLUXER_USER_ENDPOINT=https://api.fluxer.app/v1/oauth2/userinfo
SESSION_SECRET=your_secure_random_secret
OAUTH_REDIRECT_URI=http://localhost:8000/auth
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
# Optional overrides:
# SESSION_SAME_SITE=lax
# SESSION_HTTPS_ONLY=false
# SESSION_LIFETIME_DAYS=7
# MONGODB_URI=mongodb://localhost:27017
# MONGODB_DB_NAME=fluxmod
# MONGODB_COLLECTION_NAME=app_data
# MONGODB_DOCUMENT_ID=singleton
```

For production (HTTPS + cross-site frontend), use:

```env
ENVIRONMENT=production
SESSION_SAME_SITE=none
SESSION_HTTPS_ONLY=true
SESSION_LIFETIME_DAYS=30
FRONTEND_URL=https://fluxmod-frontend.onrender.com/
```

Start the server:

```bash
python api.py
```

## Docker Compose (recommended for local dev)

The easiest way to run the backend locally with MongoDB:

1. Copy `.env.example` to `.env` and fill in your OAuth values.
2. Start everything:

```bash
docker compose up --build
```

This launches two containers on a shared `fluxmod-dev-network` bridge network:

| Service | Container | Address |
|---------|-----------|---------|
| Backend | `fluxmod-backend-dev` | `http://localhost:8000` |
| MongoDB | `fluxmod-mongo-dev` | `mongodb://localhost:27017` |

`MONGODB_URI` is automatically overridden to `mongodb://mongo:27017` inside the backend container so no `.env` change is needed.

Stop containers:

```bash
docker compose down
```

Stop and delete MongoDB data:

```bash
docker compose down -v
```

> **Connecting other services:** The compose file exposes a named network (`fluxmod-dev-network`). In a separate compose project for your frontend or bot, reference it as an external network:
>
> ```yaml
> networks:
>   fluxmod-network:
>     external: true
>     name: fluxmod-dev-network
> ```

## Docker (standalone)

Build and run the backend container without Compose (requires a reachable MongoDB instance):

```bash
# Build
make build
# or: docker build -t fluxmod-backend .

# Run
make run
# or: docker run --rm -p 8000:8000 --env-file .env fluxmod-backend
```

The Dockerfile uses a multi-stage build (builder → runtime) with a non-root `app` user for smaller images and safer defaults.

Health check endpoint: `http://127.0.0.1:8000/healthz`

## Deployment (Render)

This repository includes a Render blueprint at `render.yaml` (repo root).

### Option A: Blueprint deploy (recommended)

1. Push this repo to GitHub.
2. In Render, choose **New +** → **Blueprint**.
3. Select this repository.
4. Render reads `render.yaml` and creates `automod-backend`.
5. In the service environment settings, fill these required secrets:
    - `FLUXER_CLIENT_ID`
    - `FLUXER_CLIENT_SECRET`
    - `OAUTH_REDIRECT_URI` = `https://<your-render-service>.onrender.com/auth`

### Option B: Manual web service

- Root Directory: leave empty (repo root)
- Build Command: `uv sync`
- Start Command: `uv run gunicorn "api2:create_app()" --bind 0.0.0.0:$PORT`

Required environment values:

```env
OAUTH_PROVIDER=fluxer
FLUXER_CLIENT_ID=<from Fluxer>
FLUXER_CLIENT_SECRET=<from Fluxer>
FLUXER_AUTHORIZE_URL=https://api.fluxer.app/v1/oauth2/authorize
FLUXER_TOKEN_URL=https://api.fluxer.app/v1/oauth2/token
FLUXER_API_BASE_URL=https://api.fluxer.app/v1
FLUXER_USER_ENDPOINT=https://api.fluxer.app/v1/oauth2/userinfo
SESSION_SECRET=<long-random-string>
ENVIRONMENT=production
SESSION_SAME_SITE=none
SESSION_HTTPS_ONLY=true
SESSION_LIFETIME_DAYS=30
OAUTH_REDIRECT_URI=https://<your-render-service>.onrender.com/auth
FRONTEND_URL=https://fluxmod-frontend.onrender.com/
ALLOWED_ORIGINS=https://fluxmod-frontend.onrender.com/
MONGODB_URI=<your-mongodb-connection-string>
MONGODB_DB_NAME=fluxmod
MONGODB_COLLECTION_NAME=app_data
MONGODB_DOCUMENT_ID=singleton
```

After deploy, update your Fluxer OAuth app callback URL to match `OAUTH_REDIRECT_URI`.

Python version for Render is pinned via `runtime.txt` (`python-3.12.10`).

## Data Storage

Uses MongoDB for persistence through `api2/services/data_store.py`.

Minimum required config:

```env
MONGODB_URI=mongodb://localhost:27017
```

Optional overrides:

```env
MONGODB_DB_NAME=fluxmod
MONGODB_COLLECTION_NAME=app_data
MONGODB_DOCUMENT_ID=singleton
MONGODB_TLS_CA_FILE=/etc/ssl/certs/ca-certificates.crt
# Only for debugging TLS issues in non-production environments:
# MONGODB_TLS_ALLOW_INVALID_CERTIFICATES=true
# MONGODB_TLS_ALLOW_INVALID_HOSTNAMES=true
```

For MongoDB Atlas, prefer an SRV URI:

```env
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```

If you hit TLS handshake errors (`TLSV1_ALERT_INTERNAL_ERROR`), verify:

- The Atlas URI is correct (prefer `mongodb+srv://...`).
- The deployment server outbound IP is allowed in Atlas Network Access.
- The OS CA bundle is installed/up to date (for Debian/Ubuntu: `ca-certificates`).
- You are not forcing old TLS via proxies/load balancers between app and Atlas.

## Deployment (Ubuntu)

1. Clone repo, navigate to project root directory
2. Create venv and install deps
3. Configure `.env` with Fluxer credentials
4. Run with gunicorn + nginx:

```bash
uv sync
uv run gunicorn -w 4 -b 0.0.0.0:8000 "api2:create_app()"
```

Nginx config example:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Or use systemd service:

```ini
[Unit]
Description=AutoMod Backend API
After=network.target

[Service]
Type=simple
User=automod
WorkingDirectory=/home/automod/FluxMod-Backend
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/automod/FluxMod-Backend/.venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 "api2:create_app()"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable automod-backend
sudo systemctl start automod-backend
```

## CORS

To allow requests from frontend hosted elsewhere, configure origins in `.env`:

```env
ALLOWED_ORIGINS=https://example.com
```

The Flask app uses `Flask-CORS` and combines `ALLOWED_ORIGINS` with localhost defaults.