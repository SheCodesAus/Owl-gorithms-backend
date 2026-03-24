# KICKIT — Backend API

> Django REST Framework backend for the collaborative bucket list platform.
> Provides authentication, list management, voting, invites, notifications, and reactions.

---

## Table of Contents

- [Mission Statement](#mission-statement)
- [Overview](#overview)
- [Core Workflow](#core-workflow)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Data Models](#data-models)
  - [Database Schema](#database-schema)
- [User Roles & Permissions](#user-roles--permissions)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running Locally](#running-locally)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [Users](#users)
  - [Bucket Lists](#bucket-lists)
  - [Bucket List Items](#bucket-list-items)
  - [Voting](#voting)
  - [Reactions](#reactions)
  - [Invites](#invites)
  - [Members](#members)
  - [Notifications](#notifications)
- [Management Commands](#management-commands)
- [Testing](#testing)
- [Deployment](#deployment)
- [Future Enhancements](#future-enhancements)
- [Known Issues / Gaps](#known-issues--gaps)

---

## Mission Statement

KICKIT enables groups of people to plan and prioritise experiences together through a structured, democratic process. Rather than one person deciding for everyone, KICKIT gives every member a voice — propose activities, vote on what matters most, and let the group's collective preferences shape the plan.

---

## Overview

KICKIT is a collaborative bucket list platform. The backend is a **Django REST Framework API** that handles:

- Secure authentication (JWT via `simplejwt` + Google OAuth via `django-allauth`)
- Collaborative bucket list creation and management
- Role-based permissions (owner / editor / viewer)
- Item proposals with voting and emoji reactions
- Token-based invite links for joining lists
- In-app notifications with background management commands

The API serves a React SPA frontend and is designed for deployment on Heroku/Render with a PostgreSQL database in production.

---

## Core Workflow

1. **Create** — A user creates a bucket list and automatically becomes its owner.
2. **Invite** — The owner generates shareable invite links per role (`editor` or `viewer`) and shares them with friends or collaborators.
3. **Propose** — Members (owners and editors) submit activity ideas as items. Each item starts in `proposed` status.
4. **Vote** — Members vote on proposed items (upvote / downvote). The running score is visible in real time. Owners can optionally extend voting rights to viewers.
5. **Deadline** — The owner sets a `decision_deadline`. When it passes, `send_freeze_reminders` auto-freezes the list and notifies all members.
6. **Lock In** — The owner reviews the scores and changes winning items to `locked_in`, then `complete` as activities are done.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | Django 5.1 |
| API Layer | Django REST Framework 3.15 |
| Authentication | `djangorestframework-simplejwt` 5.5 (JWT) + `django-allauth` 65 (Google OAuth) |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL (`psycopg2-binary`) |
| WSGI Server | Gunicorn 23 |
| Static Files | WhiteNoise 6 |
| CORS | `django-cors-headers` 4 |
| DB URL parsing | `dj-database-url` 2 |
| Environment | `python-dotenv` |
| Version Control | GitHub |
| API Testing | Insomnia (collection: `Insomnia_2026-03-07.yaml`) |
| Hosting | Heroku / Render |

---

## Architecture

```
React SPA (Frontend)
        │
        │  HTTPS / REST + JSON
        │  Authorization: Bearer <access_token>
        ▼
Django REST Framework API (Backend)
        │
        ├── users app         — custom User model, profile, Google OAuth callback
        └── bucketlists app   — lists, items, votes, invites, members,
                                notifications, reactions, signals
        │
        ▼
PostgreSQL (production) / SQLite (development)
```

**Key design decisions:**

- All API views use DRF `APIView` with explicit `permission_classes` and business logic inline.
- Permission checks are performed in `get_object_for_read` / `get_object_for_write` helper methods, keeping view handlers clean.
- JWT access tokens expire in **1 hour**; refresh tokens in **7 days** with rotation and blacklisting on rotation.
- When a bucket list is created, the creator is automatically given an `owner` membership record via `BucketListSerializer.create()` inside a `transaction.atomic` block.
- Notifications are created through a **service layer** (`notification_services.py`) — no code writes `Notification` rows directly.
- Signals (`signals.py`) are not used for notifications; all notification logic is called explicitly from views and management commands.

---

## Features

- **Custom User model** — Extends `AbstractUser` with `email` (unique) and `profile_image` (URL).
- **JWT Authentication** — Access/refresh token pair; refresh tokens rotated and blacklisted on use.
- **Google OAuth** — django-allauth integration with a custom adapter (`CustomSocialAccountAdapter`) that syncs first name, last name, and profile picture from Google on every login.
- **Bucket Lists** — Create, read, update, delete. Support for title, description, decision deadline, scheduling (start/end date + time), public/private visibility, viewer-voting toggle, and freeze state.
- **Items** — Create, read, update, delete items within a list. Scheduling dates/times with full validation. Status lifecycle: `proposed → locked_in → complete`. Completing an item sets `completed_at` automatically.
- **Voting** — Upvote or downvote items (one vote per user per item). `update_or_create` pattern for idempotent voting. Score computed dynamically as `upvotes − downvotes`.
- **Emoji Reactions** — Six reaction types (`fire`, `love`, `sketchy`, `dead`, `hardpass`, `nope`). One reaction per user per item; re-sending the same reaction removes it (toggle).
- **Invite Links** — Owners generate token-based invite links per role (editor / viewer). Tokens are `secrets.token_urlsafe(32)`, expire after 7 days, and can be regenerated (previous token is invalidated). One invite record per role per list.
- **Members** — View, update role (editor ↔ viewer), remove members. Members can leave a list themselves. Owner cannot be removed.
- **Freeze Toggle** — Owner can freeze/unfreeze a list. Freezing prevents new items from being added (owner excepted) and triggers notifications to all members.
- **Notifications** — In-app notifications for item added, item locked in, item completed, list frozen, and freeze reminder. Returned from `GET /notifications/` for last 30 days (non-dismissed). Lightweight `GET /notifications/unread-count/` endpoint for polling.
- **Management Commands** — `send_freeze_reminders` checks lists approaching their decision deadline and sends reminder notifications. `cleanup_notifications` removes old notification records.

---

## Project Structure

```
Owl-gorithms-backend/
├── Procfile                        # Heroku: migrate + gunicorn
├── requirements.txt                # Python dependencies
├── .env                            # Local environment variables (gitignored in production)
├── .python-version                 # Python 3.13
└── main/                           # Django project root (manage.py lives here)
    ├── manage.py
    ├── db.sqlite3                  # Dev database
    │
    ├── main/                       # Django project config package
    │   ├── settings.py             # All settings (JWT, CORS, allauth, database)
    │   ├── urls.py                 # Root URL conf
    │   ├── wsgi.py
    │   └── asgi.py
    │
    ├── users/                      # Custom user app
    │   ├── models.py               # User(AbstractUser) + email + profile_image
    │   ├── serializers.py          # UserSerializer, UserBasicSerializer
    │   ├── views.py                # UserList, UserDetail, CurrentUser, GoogleLoginCallback
    │   ├── urls.py                 # /users/, /users/<pk>/, /users/me/, /api/auth/google/callback/
    │   ├── adapters.py             # CustomSocialAccountAdapter (syncs Google profile data)
    │   ├── admin.py
    │   └── migrations/
    │
    ├── bucketlists/                # Core app
    │   ├── models.py               # BucketList, BucketListMembership, BucketListItem,
    │   │                           # ItemVote, BucketListInvite, Notification, Reaction
    │   ├── serializers.py          # All serializers incl. nested items + members
    │   ├── views.py                # All API views
    │   ├── urls.py                 # All URL patterns
    │   ├── notification_services.py # Notification service layer (never write Notification directly)
    │   ├── signals.py              # Django signals (wired in apps.py)
    │   ├── admin.py
    │   ├── migrations/             # 8 migration files
    │   └── management/
    │       └── commands/
    │           ├── send_freeze_reminders.py   # Checks deadlines, sends reminders + auto-freezes
    │           └── cleanup_notifications.py   # Deletes old notification records
    │
    └── staticfiles/                # Collected static files (WhiteNoise)
```

---

## Data Models

### User

Extends `AbstractUser`.

| Field | Type | Notes |
|-------|------|-------|
| `username` | CharField | Unique |
| `email` | EmailField | Unique |
| `profile_image` | URLField | Populated from Google OAuth |
| `first_name`, `last_name` | CharField | Populated from Google OAuth |

### BucketList

| Field | Type | Notes |
|-------|------|-------|
| `owner` | FK → User | |
| `title` | CharField(200) | |
| `description` | TextField | Optional |
| `decision_deadline` | DateTimeField | Optional; when set, triggers freeze on expiry |
| `allow_viewer_voting` | BooleanField | Default `False` |
| `is_public` | BooleanField | Default `False` |
| `is_frozen` | BooleanField | Default `False`; prevents new items when `True` |
| `start_date`, `end_date` | DateField | Optional event scheduling |
| `start_time`, `end_time` | TimeField | Optional; requires a date |
| `created_at`, `updated_at` | DateTimeField | Auto |

Computed properties: `is_date_range`, `has_time`.

Full date/time validation is enforced in both `clean()` and serializer `validate()`.

### BucketListMembership

| Field | Type | Notes |
|-------|------|-------|
| `bucket_list` | FK → BucketList | |
| `user` | FK → User | |
| `role` | CharField | `owner` / `editor` / `viewer` |
| `joined_at` | DateTimeField | Auto |

Constraint: `unique(bucket_list, user)`.

### BucketListItem

| Field | Type | Notes |
|-------|------|-------|
| `bucket_list` | FK → BucketList | |
| `created_by` | FK → User | |
| `title` | CharField(200) | |
| `description` | TextField | Optional |
| `status` | CharField | `proposed` / `locked_in` / `complete` |
| `completed_at` | DateTimeField | Set automatically when status → `complete` |
| `start_date`, `end_date` | DateField | Optional |
| `start_time`, `end_time` | TimeField | Optional |
| `created_at`, `updated_at` | DateTimeField | Auto |

Computed properties: `upvotes_count`, `downvotes_count`, `score`, `is_date_range`, `has_time`.

### ItemVote

| Field | Type | Notes |
|-------|------|-------|
| `item` | FK → BucketListItem | |
| `user` | FK → User | |
| `vote_type` | CharField | `upvote` / `downvote` |

Constraint: `unique(item, user)`.

### BucketListInvite

| Field | Type | Notes |
|-------|------|-------|
| `bucket_list` | FK → BucketList | |
| `role` | CharField | `editor` / `viewer` |
| `token` | CharField(255) | `secrets.token_urlsafe(32)`, auto-generated |
| `expires_at` | DateTimeField | Default: now + 7 days |
| `is_active` | BooleanField | Default `True` |

Constraint: `unique(bucket_list, role)` — one invite record per role per list.

Computed properties: `is_expired`, `is_valid`.

### Notification

| Field | Type | Notes |
|-------|------|-------|
| `recipient` | FK → User | |
| `actor` | FK → User | nullable |
| `notification_type` | CharField | `item_added`, `item_locked_in`, `item_completed`, `list_frozen`, `freeze_reminder` |
| `bucket_list` | FK → BucketList | nullable |
| `item` | FK → BucketListItem | nullable |
| `message` | TextField | Pre-rendered human-readable string |
| `is_read` | BooleanField | Default `False` |
| `is_dismissed` | BooleanField | Default `False` |

### Reaction

| Field | Type | Notes |
|-------|------|-------|
| `user` | FK → User | |
| `item` | FK → BucketListItem | |
| `reaction_type` | CharField | `fire`, `love`, `sketchy`, `dead`, `hardpass`, `nope` |

Constraint: `unique(user, item)`.

---

### Database Schema

> **TODO:** Replace the placeholder below with a generated schema diagram (e.g. from [drawsql.app](https://drawsql.app) or `django-extensions` `graph_models`).

```
User
 └── BucketList (owner FK)
      ├── BucketListMembership (bucket_list FK, user FK)
      ├── BucketListInvite (bucket_list FK)
      └── BucketListItem (bucket_list FK, created_by FK)
           ├── ItemVote (item FK, user FK)
           ├── Reaction (item FK, user FK)
           └── Notification (item FK, bucket_list FK, recipient FK, actor FK)
```

---

## User Roles & Permissions

| Permission | Owner | Editor | Viewer |
|-----------|:-----:|:------:|:------:|
| View list (private) | ✓ | ✓ | ✓ |
| View list (public) | ✓ | ✓ | ✓ (anyone) |
| Edit list metadata | ✓ | ✗ | ✗ |
| Delete list | ✓ | ✗ | ✗ |
| Freeze / unfreeze list | ✓ | ✗ | ✗ |
| Add items | ✓ | ✓ (unless frozen) | ✗ |
| Edit own items | ✓ | ✓ (unless frozen) | ✗ |
| Delete own items | ✓ | ✓ (unless frozen) | ✗ |
| Change item status | ✓ | ✗ | ✗ |
| Vote on items | ✓ | ✓ | Optional (`allow_viewer_voting`) |
| React to items | ✓ | ✓ | ✓ |
| Generate invite links | ✓ | ✗ | ✗ |
| Manage members | ✓ | ✗ | ✗ |
| Leave list | ✓ (n/a) | ✓ | ✓ |

---

## Getting Started

### Prerequisites

- **Python 3.13** (see `.python-version`)
- `pip`
- (Optional) `virtualenv` or `venv`

### Installation

```bash
git clone <repository-url>
cd Owl-gorithms-backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Apply migrations
cd main
python manage.py migrate

# (Optional) Create a superuser
python manage.py createsuperuser
```

### Environment Variables

Create a `.env` file in the **project root** (i.e. `Owl-gorithms-backend/.env`):

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_SECRET=your-google-client-secret

FRONTEND_URL=http://localhost:5173

# Optional — set to a PostgreSQL URL to override SQLite
DATABASE_URL=postgres://user:password@host:5432/dbname
```

| Variable | Description | Required |
|----------|-------------|:--------:|
| `DJANGO_SECRET_KEY` | Django secret key (random string) | Yes (prod) |
| `DJANGO_DEBUG` | Set to `False` in production | Yes (prod) |
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 client ID | For Google login |
| `GOOGLE_SECRET` | Google OAuth 2.0 client secret | For Google login |
| `FRONTEND_URL` | Base URL of the React frontend (used to build invite + OAuth redirect URLs) | Yes |
| `DATABASE_URL` | Full PostgreSQL connection string | Production |

> The settings file loads `.env` from the directory one level above `main/` (i.e. the project root).

### Running Locally

```bash
cd main
python manage.py runserver
```

API available at **http://127.0.0.1:8000**.

Django admin at **http://127.0.0.1:8000/admin/**.

---

## API Reference

All protected endpoints require:

```
Authorization: Bearer <access_token>
```

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/token/` | Obtain JWT access + refresh tokens | No |
| `POST` | `/api/token/refresh/` | Refresh access token | No |
| `GET` | `/auth/google/login/` | Initiate Google OAuth flow | No |
| `GET` | `/api/auth/google/callback/` | Google OAuth callback → JWT redirect | No |

**POST `/api/token/`**

```json
// Request
{ "username": "jane", "password": "secret" }

// Response 200
{ "access": "<jwt>", "refresh": "<jwt>" }
```

---

### Users

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/users/` | List all users | No |
| `POST` | `/users/` | Register a new user → returns JWT immediately | No |
| `GET` | `/users/<pk>/` | Get user details (own profile only) | Yes |
| `PUT` | `/users/<pk>/` | Update own profile (partial) | Yes |
| `DELETE` | `/users/<pk>/` | Delete own account | Yes |
| `GET` | `/users/me/` | Get current authenticated user | Yes |

**POST `/users/`** — Register

```json
// Request
{ "username": "jane", "email": "jane@example.com", "password": "secret" }

// Response 201
{
  "user": { "id": 1, "username": "jane", "email": "jane@example.com" },
  "access": "<jwt>",
  "refresh": "<jwt>"
}
```

---

### Bucket Lists

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/bucketlists/` | List all bucket lists the user is a member of | Yes |
| `POST` | `/bucketlists/` | Create a new bucket list | Yes |
| `GET` | `/bucketlists/<pk>/` | Get list detail (public: anyone; private: members only) | Optional |
| `PUT` | `/bucketlists/<pk>/` | Update list (owner only, partial) | Yes |
| `DELETE` | `/bucketlists/<pk>/` | Delete list (owner only) | Yes |
| `PUT` | `/bucketlists/<pk>/freeze/` | Freeze or unfreeze a list (owner only) | Yes |

**POST `/bucketlists/`** — Create

```json
// Request
{
  "title": "Road Trip 2026",
  "description": "Things to do on the drive down the coast",
  "decision_deadline_input": "2026-06-01",
  "is_public": false
}

// Response 201
{
  "id": 3,
  "owner": { "id": 1, "username": "jane" },
  "title": "Road Trip 2026",
  "description": "Things to do on the drive down the coast",
  "decision_deadline": "2026-06-01",
  "is_frozen": false,
  "is_public": false,
  "allow_viewer_voting": false,
  "memberships": [...],
  "items": [],
  "created_at": "2026-03-22T10:00:00Z"
}
```

**PUT `/bucketlists/<pk>/freeze/`**

```json
// Request
{ "is_frozen": true }
```

---

### Bucket List Items

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/bucketlists/<bucket_list_id>/items/` | List all items (public: anyone; private: members) | Optional |
| `POST` | `/bucketlists/<bucket_list_id>/items/` | Create item (owner/editor, list not frozen) | Yes |
| `GET` | `/items/<pk>/` | Get single item | Yes |
| `PUT` | `/items/<pk>/` | Update item (partial); owner can change status | Yes |
| `DELETE` | `/items/<pk>/` | Delete item (owner or item creator) | Yes |

**POST `/bucketlists/<id>/items/`** — Create

```json
// Request
{
  "title": "Sunrise swim at Bondi",
  "description": "Pack towels and get there early",
  "start_date": "2026-07-15",
  "start_time": "05:30:00",
  "end_time": "07:00:00"
}

// Response 201
{
  "id": 12,
  "title": "Sunrise swim at Bondi",
  "status": "proposed",
  "score": 0,
  "upvotes_count": 0,
  "downvotes_count": 0,
  "user_vote": null,
  "reactions_summary": { "fire": 0, "love": 0, "sketchy": 0, "dead": 0, "hardpass": 0, "nope": 0 },
  "user_reaction": null,
  ...
}
```

Item status lifecycle:

```
proposed → locked_in → complete
proposed → (delete)
locked_in → (delete, owner only)
```

---

### Voting

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/items/<pk>/vote/` | Submit or update a vote | Yes |
| `DELETE` | `/items/<pk>/vote/` | Remove vote | Yes |

**POST `/items/<pk>/vote/`**

```json
// Request
{ "vote_type": "upvote" }   // or "downvote"

// Response 201 (new) or 200 (updated)
{ "id": 5, "item": 12, "user": 1, "vote_type": "upvote", ... }
```

Vote permission rules:

- Public list with `allow_viewer_voting=True` → any authenticated user can vote
- Private list → member must be owner or editor (or viewer if `allow_viewer_voting=True`)
- Frozen list → voting is blocked for everyone

---

### Reactions

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/items/<item_id>/react/` | Add, replace, or toggle off a reaction | Yes |

**POST `/items/<item_id>/react/`**

```json
// Request
{ "reaction_type": "fire" }

// Response 200
{
  "user_reaction": "fire",          // null if toggled off
  "reactions_summary": {
    "fire": 3, "love": 1, "sketchy": 0,
    "dead": 0, "hardpass": 0, "nope": 0
  }
}
```

Valid `reaction_type` values: `fire`, `love`, `sketchy`, `dead`, `hardpass`, `nope`.

---

### Invites

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/bucketlists/<id>/invites/<role>/` | Get invite for a role (owner only) | Yes |
| `POST` | `/bucketlists/<id>/invites/<role>/` | Generate invite for a role (owner only) | Yes |
| `PUT` | `/bucketlists/<id>/invites/<role>/` | Regenerate invite token (owner only) | Yes |
| `GET` | `/invites/<token>/` | Preview invite by token (anyone) | No |
| `POST` | `/invites/<token>/accept/` | Accept invite | Yes |

`<role>` must be `editor` or `viewer`.

**GET `/invites/<token>/`** — Preview (public)

```json
// Response 200
{
  "role": "editor",
  "token": "abc123...",
  "invite_url": "http://localhost:5173/invites/abc123...",
  "expires_at": "2026-03-29T10:00:00Z",
  "is_valid": true,
  "bucket_list_title": "Road Trip 2026",
  "bucket_list_description": "...",
  "owner_email": "jane@example.com",
  "already_member": false
}
```

**POST `/invites/<token>/accept/`**

```json
// Request
{ "accept": true }

// Response 201
{
  "detail": "Invite accepted successfully.",
  "bucket_list_id": 3,
  "membership_id": 7,
  "role": "editor"
}
```

---

### Members

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `PUT` | `/bucketlists/<bl_id>/members/<membership_id>/` | Update member role (owner only) | Yes |
| `DELETE` | `/bucketlists/<bl_id>/members/<membership_id>/` | Remove member (owner) or leave list (self) | Yes |

**PUT** — Update role

```json
// Request
{ "role": "viewer" }   // or "editor"
```

Rules: owner cannot change their own role; owner membership cannot be deleted.

---

### Notifications

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/notifications/` | List notifications (last 30 days, non-dismissed) | Yes |
| `GET` | `/notifications/unread-count/` | Lightweight unread count for polling | Yes |
| `POST` | `/notifications/read/` | Mark read or dismiss | Yes |

**POST `/notifications/read/`** — Mark one as read

```json
{ "id": 42 }
```

**POST `/notifications/read/`** — Mark all as read

```json
{ "all": true }
```

**POST `/notifications/read/`** — Dismiss all

```json
{ "all": true, "dismiss": true }
```

---

## Management Commands

Run from the `main/` directory (inside the virtual environment):

```bash
# Send freeze reminder notifications to lists approaching their decision_deadline
python manage.py send_freeze_reminders

# Clean up old dismissed or read notifications
python manage.py cleanup_notifications
```

`send_freeze_reminders` also **auto-freezes** lists whose `decision_deadline` has passed and are not yet frozen, then notifies all members.

These commands are intended to be scheduled via a cron job or Heroku Scheduler.

---

## Testing

API testing is done with [Insomnia](https://insomnia.rest/).

A pre-built collection is included in the repository:

```
Insomnia_2026-03-07.yaml
```

**Setup:**

1. Open Insomnia and select **Import** → **From File**.
2. Select `Insomnia_2026-03-07.yaml` from the project root.
3. Set the base URL environment variable to `http://127.0.0.1:8000`.

**Recommended testing workflow:**

1. `POST /users/` — Register a new user and copy the returned `access` token.
2. Set the `access` token as the `Bearer` token in the Insomnia environment.
3. `POST /bucketlists/` — Create a bucket list.
4. `POST /bucketlists/<id>/items/` — Add items to the list.
5. `POST /items/<id>/vote/` — Vote on items.
6. `POST /bucketlists/<id>/invites/editor/` — Generate an editor invite link.
7. Register a second user and use their token to `POST /invites/<token>/accept/`.
8. Test role-based restrictions by attempting owner-only actions with the editor token.

> **Note:** No automated test suite is currently in place. `users/tests.py` and `bucketlists/tests.py` exist but are empty. See [Known Issues](#known-issues--gaps).

---

## Deployment

The project includes a `Procfile` for Heroku:

```
release: python main/manage.py migrate
web: gunicorn --pythonpath main main.wsgi --log-file -
```

**Deployment checklist:**

1. Set all required environment variables (see [Environment Variables](#environment-variables)).
2. Set `DJANGO_DEBUG=False`.
3. Set `DJANGO_SECRET_KEY` to a strong random value.
4. Set `DATABASE_URL` to a PostgreSQL connection string.
5. Add the production frontend URL to `CORS_ALLOWED_ORIGINS` in `settings.py` (or pass it via env var).
6. Run `python manage.py collectstatic` (handled by WhiteNoise on startup).
7. Ensure Google OAuth redirect URIs are updated in the Google Cloud Console and in the `GoogleLoginCallback` view.
8. Schedule `send_freeze_reminders` and `cleanup_notifications` management commands.

**Note:** `ALLOWED_HOSTS = ["*"]` is set in `settings.py` for convenience. Restrict this to specific hostnames before going live.

---

## Future Enhancements

- **Item comments** — Allow members to leave threaded comments on proposed items to discuss before voting.
- **Real-time updates** — WebSocket support (Django Channels) for live vote score updates without polling.
- **Image uploads** — Cover photos for lists and item images, stored via a cloud provider (e.g. S3 / Cloudinary).
- **Public list discovery** — A browseable directory of public lists so users can find and join community lists.
- **Activity analytics** — Aggregate data on the most popular activity categories and voting patterns across the platform.
- **Automated test suite** — Unit and integration tests for all views, serializers, and permission logic.
- **Rate limiting** — Throttle invite generation and voting endpoints to prevent abuse.

---

## Known Issues / Gaps

- **`ALLOWED_HOSTS = ["*"]`** — This is a security risk in production. It should be set to the actual hostname(s) before deployment.

- **Google OAuth callback hardcodes localhost** — `users/views.py → GoogleLoginCallback` has `http://localhost:5173` hardcoded as the redirect URL. This should use the `FRONTEND_URL` environment variable in both success and failure redirects.

- **CORS not production-ready** — `settings.py` only lists `localhost:5173` in `CORS_ALLOWED_ORIGINS`. The production frontend URL must be added via configuration before deployment.

- **No `cancelled` status in code** — The original README documents a `cancelled` item status, but the `BucketListItem` model only has `proposed`, `locked_in`, and `complete` in `StatusChoices`. The old README was aspirational.

- **Legacy `api-token-auth` reference** — `src/context/AuthContext.jsx` (frontend) references `/api-token-auth/` which does not exist in the backend URL conf. The active login endpoint is `/api/token/`. This appears to be dead code in the frontend.

- **`SESSION_COOKIE_SECURE = True` in development** — This setting requires HTTPS, which may cause issues when testing the Django session / allauth flow locally over HTTP. It is likely fine in production but may need to be conditionally disabled in development.

- **No automated tests** — `users/tests.py` and `bucketlists/tests.py` exist but are empty. No test suite is in place.

- **Freeze reminder scheduling not configured** — The `send_freeze_reminders` management command must be scheduled externally (cron / Heroku Scheduler). No scheduling infrastructure is set up.
