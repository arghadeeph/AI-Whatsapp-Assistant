# AI WhatsApp Assistant

AI WhatsApp Assistant is a Django-based multi-tenant WhatsApp automation app for businesses. It combines:

- WhatsApp Cloud API webhook handling
- AI-powered auto replies
- business-specific FAQs
- chat inbox and conversation history
- JWT-authenticated API endpoints
- HTML dashboard and auth pages

The app is organized around a `Business` tenant, and authenticated users are linked to a single business through the `UserBusiness` model.

## Features

- WhatsApp webhook verification and inbound message handling
- Automatic AI replies to incoming WhatsApp messages
- Manual outbound messaging from the inbox
- FAQ management per business
- JWT auth with access and refresh tokens
- Email or business phone number login
- Tenant-aware APIs via middleware
- Basic dashboard and chat UI

## Tech Stack

- Python 3.11
- Django 4.2
- Django REST Framework
- Simple JWT
- PostgreSQL
- WhatsApp Cloud API
- OpenAI API
- Tailwind CSS via CDN for templates

## Project Structure

- `config/` - Django project settings and root URL routing
- `users/` - registration, login, JWT auth, and user-business linking
- `businesses/` - business and FAQ models plus FAQ APIs
- `messaging/` - conversation list, message history, and outbound messaging
- `whatsapp/` - WhatsApp webhook receiver and AI reply flow
- `dashboard/` - dashboard page and summary API
- `templates/` - HTML pages for auth, dashboard, chat, and FAQ views

## Requirements

- Python 3.11+
- PostgreSQL database
- WhatsApp Cloud API credentials
- OpenAI API key

## Environment Variables

Create a `.env` file in the project root with:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

POSTGRES_DB=your_database_name
POSTGRES_USER=your_database_user
POSTGRES_PASSWORD=your_database_password
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432

WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_VERSION=v18.0

OPENAI_API_KEY=your_openai_api_key
```

Notes:

- `POSTGRES_HOST=host.docker.internal` is used by default in `config/settings.py`, especially for Docker-based development.
- `WHATSAPP_VERIFY_TOKEN` must match the token configured in Meta when you register the webhook.
- The code currently uses `gpt-4.1-mini` as the OpenAI model in settings.

## Local Setup

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd ai-whatsapp-assistant
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run database migrations

Make sure PostgreSQL is running and the `.env` values are set, then:

```bash
python manage.py migrate
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`.

## Docker Setup

The repository includes a `Dockerfile` and `docker-compose.yml`.

### Build and run

```bash
docker compose up --build
```

The service exposes port `8000`.

### Docker notes

- The container runs `python manage.py runserver 0.0.0.0:8000` by default.
- `docker-compose.yml` mounts the project into `/app`, so code changes are reflected immediately.
- `extra_hosts` maps `host.docker.internal` for local database connectivity.

## Authentication

The app supports JWT authentication with refresh token rotation.

### Login methods

- Email address
- Business phone number

### Auth pages

- `/auth/login/`
- `/auth/register/`

### Auth APIs

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `POST /api/auth/token/refresh/`

## Core URLs

### HTML pages

- `/dashboard/`
- `/chat/`
- `/chat/<signed_phone>/`
- `/business/faq`
- `/auth/login/`
- `/auth/register/`

### API endpoints

- `/api/dashboard/`
- `/api/messages/conversations/`
- `/api/messages/chat/<signed_phone>/`
- `/api/messages/send-message/`
- `/api/business/faq/`
- `/api/business/faq/<pk>/`
- `/api/business/faq/<pk>/toggle/`
- `/api/whatsapp/webhook/`

## WhatsApp Flow

1. Meta verifies the webhook with `GET /api/whatsapp/webhook/`.
2. Incoming WhatsApp messages arrive on the same webhook via `POST`.
3. The webhook identifies the business from WhatsApp metadata.
4. The incoming message is stored in `Messages`.
5. `whatsapp.ai_service.get_ai_response(...)` generates a reply.
6. The reply is sent through the WhatsApp Cloud API.
7. The outbound AI message is also stored in `Messages`.

## Data Model Overview

### `Business`

- business name
- WhatsApp phone number
- WhatsApp `phone_number_id`
- tone
- AI enabled flag

### `FAQ`

- belongs to a business
- question and answer text
- active/inactive status

### `Messages`

- belongs to a business
- sender phone number
- sender type: user, ai, or business
- incoming/outgoing direction
- WhatsApp message ID
- delivery status

### `UserBusiness`

- links a Django `User` to a `Business`
- stores role: owner, admin, or staff

## Middleware

`businesses.middleware.TenantMiddleware`:

- authenticates JWT tokens for API requests
- resolves the current business for the logged-in user
- attaches `request.business`, `request.business_id`, and `request.user_role`
- skips public paths such as auth pages and the WhatsApp webhook

## Development Notes

- The project currently uses PostgreSQL in settings; SQLite is not the default runtime database.
- HTML templates rely on the browser storing `access_token` and `refresh_token` in `localStorage`.
- Some template navigation items point to future routes such as `/leads/` and `/campaigns/`, which are not implemented in the current codebase.
- The project includes a committed `db.sqlite3`, but the settings file is configured for PostgreSQL.

## Troubleshooting

### Webhook verification fails

- Confirm `WHATSAPP_VERIFY_TOKEN` matches the token configured in Meta.
- Make sure the webhook URL is publicly reachable.
- Check that `/api/whatsapp/webhook/` is allowed in your deployment.

### Login works in API but not in the UI

- Ensure the frontend stores `access_token` and `refresh_token` in `localStorage`.
- Verify the auth response includes the business fields expected by the templates.

### Messages are not being associated with the right business

- Check that the WhatsApp `phone_number_id` in Meta matches the one saved on the `Business`.
- Review the fallback logic in `whatsapp/views.py`, which can default to business ID `4` if no match is found.

## Security Notes

- `DEBUG` is enabled in `config/settings.py`; turn it off for production.
- The Django `SECRET_KEY` in settings is a hardcoded development value and should be overridden in production.
- WhatsApp and OpenAI credentials should stay in environment variables, not in source control.

## License

This project is licensed under the [MIT License](/data/html/CodePayground/ai-whatsapp-assistant/LICENSE).
