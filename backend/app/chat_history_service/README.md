Chat History Service

Overview

- Standalone FastAPI service providing user-scoped chat history APIs.
- Secured by shared Firebase auth middleware from `backend/auth`.

Run locally

```bash
cd backend
set PYTHONPATH=%CD%
python chat_history_service/main.py
```

Environment

- FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON
- CHAT_DB_URL (optional, defaults to sqlite+aiosqlite:///./chat_history.db)

Endpoints (prefixed with /api/v1)

- GET /conversations
- POST /conversations
- GET /conversations/{id}
- GET /conversations/{id}/messages
- POST /conversations/{id}/messages
- PUT /conversations/{id}
- DELETE /conversations/{id}
