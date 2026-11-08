# Deployment Guide

PlacementSync can be deployed in three ways:

1. **Docker Compose** (recommended) — full stack with PostgreSQL
2. **Manual** — Python backend + Node frontend on a server
3. **Cloud** — deploy to any platform that supports Docker

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker and Docker Compose installed

### Steps

```bash
# Clone the repo
git clone https://github.com/JosephJonathanFernandes/placementsync-mis.git
cd placementsync-mis

# Configure environment
cp .env.example .env
# Edit .env with your values (especially SECRET_KEY and Gmail OAuth credentials)

# Start all services
docker compose up -d

# Verify
curl http://localhost:8000/health
```

### Services
| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI API |
| Database | 5432 | PostgreSQL 15 |
| Frontend | 80 | React app (nginx) |

### Stopping
```bash
docker compose down
```

### Backing up data
The PostgreSQL data is stored in a Docker volume (`placementsync-db-data`).
To back it up:

```bash
docker run --rm \
  -v placementsync-db-data:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/db-backup.tar.gz -C /source .
```

## Option 2: Manual Deployment

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with production values
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For production, use a process manager (systemd, supervisor) or a WSGI/ASGI server:
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000
```

### Frontend

```bash
cd frontend
npm ci
npm run build
# Serve dist/ with nginx, Apache, or any static file host
```

### Database (PostgreSQL)

If using PostgreSQL instead of SQLite:

1. Create a PostgreSQL database and user
2. Set `DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname` in `.env`
3. Run migrations: `alembic upgrade head` (optional, tables are auto-created on startup)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `change-me-in-production` | App secret key (change in production!) |
| `APP_ENV` | No | `development` | `development` or `production` |
| `DEBUG` | No | `true` | Debug mode |
| `DATABASE_URL` | No | `sqlite:///./placement_sync.db` | Database connection string |
| `EXCEL_FILE_PATH` | No | `./exports/placement_register.xlsx` | Path to Excel register |
| `ACADEMIC_YEAR` | No | `2024-25` | Current academic year |
| `GOOGLE_CLIENT_ID` | No (Gmail only) | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No (Gmail only) | — | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | `http://localhost:8000/api/auth/gmail/callback` | OAuth redirect URI |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL for OAuth redirects |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Security Checklist

- [ ] Change `SECRET_KEY` from the default value
- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Use HTTPS in production (configure reverse proxy)
- [ ] Restrict CORS origins in `app/main.py`
- [ ] Set strong PostgreSQL password in Docker Compose
- [ ] Never commit `.env` — it's gitignored

## CI/CD

GitHub Actions runs on every push to `main`:
- **Backend**: installs dependencies, runs 66 tests against PostgreSQL
- **Frontend**: installs dependencies, runs type-check and production build

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | Check `.env` has `SECRET_KEY` set; check `DATABASE_URL` |
| Database connection failed | Ensure PostgreSQL is running; check credentials |
| Frontend can't reach API | Verify `vite.config.ts` proxy points to correct backend URL |
| OAuth fails | Verify `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and redirect URI match Google Cloud Console |

## Support

Open an issue on GitHub for bugs or feature requests.