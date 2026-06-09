# EdTrack3

This repository is now organized as a **3-tier architecture**:

- **Presentation tier (frontend)**: React application running on `localhost:3000`
- **Application tier (backend)**: Django REST API running on `localhost:5000`
- **Data tier**: Django models + SQLite (or optional Postgres) stored in `backend/db.sqlite3`

---

## Running the project (development)

### 1) Start the backend (API server)

```bash
cd backend
python -m venv .venv   # optional: create a virtualenv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 5000
```

The backend will run on `http://localhost:5000` and expose REST endpoints under `/api/`.

### 2) Start the frontend (React app)

```bash
cd frontend
npm install
npm start
```

The frontend will run on `http://localhost:3000` and will proxy API calls to the backend.

---

## Notes

- API calls are handled by `frontend/src/services/api.js` and use a consistent JSON response format.
- Backend CORS is configured to accept requests from `http://localhost:3000`.
- Environment variables can be set via `backend/.env` (see `backend/.env.example`).

---

## Deployment setup

For your current hosting layout, the backend should run on Railway, the database should stay on Render Postgres, and the frontend should run on Vercel.

### Railway backend variables

Set these in the Railway service that runs Django:

- `DJANGO_SECRET_KEY`: a strong random secret
- `DJANGO_DEBUG=False`
- `DJANGO_SETTINGS_MODULE=myserver.settings_production` if you want Railway to use the production settings file
- `DJANGO_ALLOWED_HOSTS=studentattendancetrackingsystem-production-7589.up.railway.app,.railway.app`
- `DATABASE_URL=<your Render Postgres connection string>`
- `CORS_ALLOWED_ORIGINS=https://student-attendance-tracking-system-zeta.vercel.app,http://localhost:3000`
- `CSRF_TRUSTED_ORIGINS=https://student-attendance-tracking-system-zeta.vercel.app,http://localhost:3000`

Optional but recommended for transactional email delivery:

- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_TIMEOUT`

If `SENDGRID_API_KEY` is present, the backend sends announcements through the SendGrid REST API instead of SMTP. Without it, the app falls back to a console backend for local development or incomplete deployments.

Face recognition note for Railway:

- The backend includes `backend/nixpacks.toml` so Railway installs native Linux libraries required by `face_recognition`/`dlib`.
- After pulling this change, trigger a full Railway redeploy so the image is rebuilt with these system packages.
- If Railway still reports missing system libraries (for example `libX11.so.6`), use the included `backend/Dockerfile` as the backend builder and redeploy.

### Vercel frontend variables

Set this in the Vercel project that runs React:

- `REACT_APP_API_BASE=https://studentattendancetrackingsystem-production-7589.up.railway.app`

### What I still need from you

If you want me to verify the final values precisely, send:

- the public Railway backend URL
- the public Vercel frontend URL
- whether Railway is using `myserver.settings` or `myserver.settings_production`
- whether you want email delivery configured now, and if so the SMTP values

---

## Existing Features

The existing AI face recognition attendance flow is still supported via the backend API.

> If you want to run the legacy Django HTML templates instead of the React frontend, you can still visit the Django routes directly (e.g., `http://localhost:5000/login/`).
