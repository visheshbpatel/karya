# Karya

Karya is a task management REST API built with FastAPI. It provides user authentication, email verification, and user-specific task management with support for priorities, descriptions, and due dates.

The project focuses on learning and implementing practical backend engineering concepts, including database design, authentication, API validation, automated testing, and database migrations.

## Features

### Task Management
- Create, retrieve, update, and delete tasks
- Mark tasks as completed
- Assign task priorities: `urgent`, `important`, and `normal`
- Add task descriptions and due dates
- Partially update task fields
- Filter tasks by completion status and priority
- Search tasks by name
- Sort and paginate task results

### Authentication
- User registration and login
- Email verification using OTPs
- OTP expiration and attempt limits
- Resend cooldown and rate limiting
- Password hashing
- JWT-based authentication
- User-specific task access

### Database and Testing
- SQLAlchemy ORM
- Database schema migrations with Alembic
- SQLite support and PostgreSQL configuration
- Automated tests using pytest

## Tech Stack

- **Language:** Python 3.12
- **API Framework:** FastAPI
- **Database:** SQLite / PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Validation:** Pydantic
- **Authentication:** JWT and Argon2 password hashing
- **Email:** Brevo Transactional Email API
- **Testing:** pytest

## Getting Started

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- A database supported by the project
- A Brevo account configured for transactional email

### 1. Clone the repository

```bash
git clone https://github.com/visheshbpatel/karya.git
cd karya
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

Create a `.env` file in the project root.

```dotenv
DATABASE_URL=your_database_connection_url
SECRET_KEY=your_secret_key

BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=your_verified_sender_email
BREVO_SENDER_NAME=Karya
```

Use a strong, randomly generated `SECRET_KEY`. Configure `DATABASE_URL` for your database; the application defaults to a local SQLite database when it is not provided.

Replace the Brevo placeholders with your actual credentials. The sender email must be verified in Brevo.

**Never commit your `.env` file or expose credentials in your repository.**

### 4. Apply database migrations

```bash
uv run alembic upgrade head
```

### 5. Start the development server

```bash
uv run uvicorn main:app --reload
```

The API will be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/verify-email` | Verify email using OTP |
| POST | `/auth/resend-otp` | Request another verification OTP |
| POST | `/auth/login` | Authenticate and receive a JWT |

### Tasks

| Method | Endpoint | Description |
|---|---|---|
| GET | `/todos` | List the authenticated user's tasks |
| GET | `/todo/{todo_id}` | Retrieve a task |
| POST | `/todo` | Create a task |
| PUT | `/todo/{todo_id}` | Update a task |
| PATCH | `/todo/{todo_id}` | Partially update a task |
| DELETE | `/todo/{todo_id}` | Delete a task |

Protected task endpoints require a valid JWT in the `Authorization` header:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Use `/docs` to inspect request schemas and try the endpoints interactively.

## Running Tests

Run the automated test suite:

```bash
uv run pytest -q
```

Check whether the database models and migrations are synchronized:

```bash
uv run alembic check
```

## Project Status

Karya is under active development. The current version focuses on the backend API, authentication, email verification, database integration, and automated testing.

A frontend and further improvements are planned for future development.

## License

No license has been specified yet.
