# Karya

**Karya** (कार्य, "work, a deed done") is a task manager with a FastAPI backend and a plain HTML/CSS/JavaScript frontend. It covers accounts, email verification, password reset and per-user tasks with priorities, descriptions and due dates.

**Live demo:** https://karya-9bym.onrender.com/

> The demo runs on a free Render instance, so the first request after a period of inactivity can take up to a minute while it wakes up.

The project started as a way to learn practical backend engineering (database design, authentication, validation, migrations and testing). The longer-term goal is to turn it into an AI task agent that can be controlled from chat apps. See the [Roadmap](#roadmap).

## Features

### Tasks
- Create, read, update and delete tasks
- Priorities: `urgent`, `important`, `normal`
- Optional description and due date
- Mark tasks done, and partially update any field with `PATCH`
- Filter by status and priority, search by title
- Sort by newest, oldest or priority, with pagination
- Every task belongs to one user; users can only see and change their own

### Accounts and security
- Registration and login with email **or** username
- Email verification with a six-digit OTP (10-minute expiry, 5 attempts, 60-second resend cooldown, 5 sends per hour)
- **Password reset**: request a code, verify it, then set a new password with a short-lived reset token
- `GET /auth/me` returns the signed-in user's profile
- Argon2 password hashing and JWT access tokens (30 minutes, no refresh token)
- Reset and resend endpoints give the same reply whether or not an account exists

### Frontend
- Plain HTML, CSS and ES modules. No framework and no build step
- Sign in, register, verify, reset password and tasks pages
- Light, dark and system themes, saved in the browser
- Account panel with username and email
- Responsive layout, keyboard shortcuts (`/` search, `N` new task) and accessible dialogs and menus
- Served by FastAPI from the same origin, so no CORS setup is needed

### Engineering
- SQLAlchemy ORM with Alembic migrations
- SQLite for local development, PostgreSQL in production
- Automated tests with pytest

## Tech stack

| Area | Tools |
|---|---|
| Language | Python 3.12 |
| API | FastAPI, Pydantic |
| Database | SQLAlchemy, Alembic, SQLite / PostgreSQL |
| Auth | PyJWT, Argon2 (pwdlib) |
| Email | Brevo transactional email API |
| Frontend | HTML5, CSS3, vanilla JavaScript |
| Tests | pytest |
| Hosting | Render |

## Project structure

```
karya/
├── main.py                          app setup; mounts the frontend at /app
├── routes.py                        all API routes
├── schemas.py                       request and response models
├── database.py                      SQLAlchemy models and engine
├── auth.py, security.py             JWT and password hashing
├── otp_*.py, email_service.py       verification codes and email delivery
├── password_reset_*.py              password-reset flow
├── migrations/                      Alembic migrations
├── tests/                           pytest suite
└── frontend/
    ├── index.html                   tasks
    ├── login.html, register.html,
    │   verify.html, reset.html      account pages
    ├── css/                         tokens, components, page rules
    └── js/                          api client, pages, theme, OTP helpers
```

## Getting started

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- A [Brevo](https://www.brevo.com/) account with a verified sender (needed to send OTP emails)

### 1. Clone and install

```bash
git clone https://github.com/visheshbpatel/karya.git
cd karya
uv sync
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```dotenv
DATABASE_URL=sqlite:///./karya.db
SECRET_KEY=replace_with_a_long_random_string

BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=your_verified_sender_email
BREVO_SENDER_NAME=Karya
```

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Signs JWTs. Use a long random value, for example `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | No | Defaults to `sqlite:///./karya.db`. Use a PostgreSQL URL in production |
| `BREVO_API_KEY` | For email | Without it, registration and reset emails cannot be sent |
| `BREVO_SENDER_EMAIL` | For email | Must be verified in Brevo |
| `BREVO_SENDER_NAME` | No | Defaults to `Karya` |

Never commit `.env`.

### 3. Run migrations

```bash
uv run alembic upgrade head
```

### 4. Start the server

```bash
uv run uvicorn main:app --reload
```

| What | URL |
|---|---|
| App | http://127.0.0.1:8000/ (redirects to `/app`) |
| API docs (Swagger) | http://127.0.0.1:8000/docs |

## API reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create an account and send a verification code |
| POST | `/auth/verify-email` | Verify the email with the OTP |
| POST | `/auth/resend-otp` | Send another verification code |
| POST | `/auth/login` | Sign in with email or username; returns a JWT |
| GET | `/auth/me` | Current user profile (requires a token) |
| POST | `/auth/forgot-password` | Send a password-reset code |
| POST | `/auth/verify-reset-otp` | Check the reset code; returns a `reset_token` |
| POST | `/auth/reset-password` | Set a new password using the `reset_token` |

### Tasks

All task endpoints require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/todos` | List your tasks |
| GET | `/todo/{id}` | Get one task |
| POST | `/todo` | Create a task |
| PUT | `/todo/{id}` | Replace a task (all fields required) |
| PATCH | `/todo/{id}` | Update only the fields you send |
| DELETE | `/todo/{id}` | Delete a task |

`GET /todos` query parameters: `completed`, `priority`, `search`, `sort_by` (`id` or `priority`), `order` (`asc` or `desc`), `skip`, `limit`. It returns a plain array without a total count.

Try everything interactively at `/docs`.

## Tests

```bash
uv run pytest -q
uv run alembic check      # models and migrations are in sync
```

Tests need `SECRET_KEY` to be set (for example in `.env`).

## Deployment notes

The live demo runs on Render. For a similar setup:

- Build command: `uv sync`
- Start command: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set the environment variables above, with a PostgreSQL `DATABASE_URL`.

The frontend is served by the same app, so one service is enough.

## Known limitations

- Access tokens last 30 minutes and cannot be refreshed; users sign in again afterwards.
- Existing tokens stay valid after a password reset.
- `/todos` returns no total count, so the UI offers Previous and Next only.
- Resend cooldowns and hourly limits for codes are enforced by the server, and mirrored in the browser for display.
