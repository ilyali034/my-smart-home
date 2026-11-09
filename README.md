# my-smart-home

A smart home device control panel by ilyali034.

## Backend

The FastAPI backend provides registration/login and user-owned device CRUD. Device state is stored in SQLite and can be changed through the API. Existing device tables are upgraded automatically when the app starts; legacy device rows are preserved but remain unassigned and are not exposed through user-scoped routes.

### Run locally

Install the packages from `requirements.txt`, then start the server from the repository root with:

```powershell
uvicorn server.api.app:app --reload
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`; `GET /health` is a simple health check. SQLite data is stored in `data/smart_home.db` by default.

### Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `SMART_HOME_DB_PATH` | `data/smart_home.db` | SQLite database path |
| `SMART_HOME_SECRET_KEY` | `dev-secret-change-me` | HMAC key used to sign access tokens; set a long random value outside local development |
| `SMART_HOME_ACCESS_TOKEN_TTL_MINUTES` | `60` | Access-token lifetime |
| `SMART_HOME_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated browser origins |

### API overview

- `POST /api/auth/register` and `POST /api/auth/login` return a bearer access token.
- `GET /api/auth/me` returns the authenticated user.
- `GET/POST /api/devices` list or create devices; list supports `room` and `type` filters.
- `GET/PATCH/DELETE /api/devices/{device_id}` read, update, or remove a device.
- `PATCH /api/devices/{device_id}/state` changes its `is_on` state.

All device routes require `Authorization: Bearer <access_token>`. Each user's devices are isolated from other accounts.
