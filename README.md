# Collaborative Bucket List App – Backend

> Group Project – Owl-gorithms Bucket List for Client

---

# Table of Contents

- [Collaborative Bucket List App – Backend](#collaborative-bucket-list-app--backend)
- [Table of Contents](#table-of-contents)
- [Mission Statement](#mission-statement)
- [Project Overview](#project-overview)
- [Core Features](#core-features)
  - [User Management](#user-management)
  - [Collaborative Bucket Lists](#collaborative-bucket-lists)
  - [Item Proposals](#item-proposals)
  - [Voting System](#voting-system)
  - [Invite Links](#invite-links)
- [User Roles \& Permissions](#user-roles--permissions)
- [System Architecture](#system-architecture)
    - [Components](#components)
- [Technology Stack](#technology-stack)
  - [Backend](#backend)
  - [Database](#database)
  - [Frontend (Planned)](#frontend-planned)
  - [Development Tools](#development-tools)
- [Backend Implementation](#backend-implementation)
  - [API Specification](#api-specification)
    - [Authentication](#authentication)
  - [User Endpoints](#user-endpoints)
  - [Bucket List Endpoints](#bucket-list-endpoints)
  - [Bucket List Item Endpoints](#bucket-list-item-endpoints)
- [Object Definitions](#object-definitions)
  - [BucketList](#bucketlist)
  - [BucketListMembership](#bucketlistmembership)
  - [BucketListItem](#bucketlistitem)
  - [ItemVote](#itemvote)
  - [BucketListInvite](#bucketlistinvite)
- [Database Schema](#database-schema)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Deployment](#deployment)
- [Future Enhancements](#future-enhancements)

# Mission Statement

The Collaborative Bucket List App enables groups of people to plan and prioritise experiences together.

Instead of individuals maintaining isolated lists, the platform allows **friends, families, and teams to create shared bucket lists**, propose activities, and vote collectively on what experiences they want to complete.

The backend API powers the collaboration system by providing:

* secure authentication
* collaborative list management
* role-based permissions
* item proposals
* voting
* deadline-based decision making

The system encourages group participation while ensuring clear ownership and structured decision-making.

# Project Overview

The backend is built as a **REST API using Django and Django REST Framework**.

The API supports the following key workflows:

1. A user creates a bucket list.
2. The owner invites collaborators via invite links.
3. Members propose activities.
4. Members vote on proposed items.
5. A decision deadline closes voting.
6. The owner locks in the final selected items.

This structure allows collaborative planning with transparent decision-making.

---

# Core Features

## User Management

* User registration
* Secure authentication (JWT)
* User profile management
* Token-based API access

## Collaborative Bucket Lists

Users can:

* create bucket lists
* invite collaborators
* manage list metadata
* define decision deadlines

Each list contains:

* owner
* collaborators
* items
* votes
* invite links

## Item Proposals

Collaborators can propose activities within a bucket list.

Examples:

* Visit Bondi Beach
* Go skydiving
* Road trip down the coast

Items contain:

* title
* description
* creator
* status
* timestamps

Item lifecycle:

```
proposed → locked_in → complete
proposed → cancelled
locked_in → cancelled
```

---

## Voting System

Members can vote on items to prioritise experiences.

Supported states:

* **Upvote**
* **Downvote**
* **No vote**

Rules:

* One vote per user per item
* Votes can be updated before the decision deadline
* Voting closes when the deadline passes
* Viewer voting can be enabled by the owner

Vote totals are **computed dynamically**.

---

## Invite Links

Owners can invite collaborators via secure invite links.

Invite types:

| Type   | Role                            |
| ------ | ------------------------------- |
| Editor | Can add items and vote          |
| Viewer | Read-only unless voting enabled |

Invite behaviour:

* Unique token-based links
* Default expiry: **7 days**
* Regenerating invalidates previous links
* Accepting an invite creates a membership record

---

# User Roles & Permissions

| Permission         | Owner | Editor              | Viewer   |
| ------------------ | ----- | ------------------- | -------- |
| View bucket list   | ✓     | ✓                   | ✓        |
| Edit bucket list   | ✓     | ✗                   | ✗        |
| Delete bucket list | ✓     | ✗                   | ✗        |
| Add items          | ✓     | ✓ (before deadline) | ✗        |
| Edit own items     | ✓     | ✓ (before deadline) | ✗        |
| Delete own items   | ✓     | ✓ (before deadline) | ✗        |
| Change item status | ✓     | ✗                   | ✗        |
| Vote               | ✓     | ✓                   | Optional |
| Manage members     | ✓     | ✗                   | ✗        |
| Generate invites   | ✓     | ✗                   | ✗        |

---

# System Architecture

The application follows a **client-server architecture**.

```
Frontend (React)
        |
        | REST API
        |
Django REST Framework Backend
        |
        |
Relational Database
(PostgreSQL / SQLite)
```

### Components

**Frontend**

* React application
* Communicates with backend API

**Backend**

* Django REST Framework
* Handles authentication, business logic, permissions

**Database**

* Stores users, lists, items, votes, invites

---

# Technology Stack

## Backend

* Python
* Django
* Django REST Framework
* JWT Authentication

## Database

* PostgreSQL (production)
* SQLite (development)

## Frontend (Planned)

* React
* JavaScript
* HTML/CSS

## Development Tools

* GitHub
* Insomnia (API testing)
* Heroku / Render (deployment)

---

# Backend Implementation

## API Specification

### Authentication

| Method | Endpoint      | Purpose          |
| ------ | ------------- | ---------------- |
| POST   | `/api/token/` | Obtain JWT token |

Example request:

```json
{
  "email": "user@email.com",
  "password": "password"
}
```

## User Endpoints

| Method | Endpoint       | Description    |
| ------ | -------------- | -------------- |
| GET    | `/users/`      | List all users |
| POST   | `/users/`      | Create user    |
| GET    | `/users/<pk>`  | Retrieve user  |
| PUT    | `/users/<pk>/` | Update user    |
| DELETE | `/users/<pk>/` | Delete user    |
| GET    | `/users/me`    | Current user   |

## Bucket List Endpoints

| Method | Endpoint            | Description        |
| ------ | ------------------- | ------------------ |
| POST   | `/bucketlists/`     | Create bucket list |
| GET    | `/bucketlists/`     | Retrieve lists     |
| GET    | `/bucketlists/<pk>` | Retrieve list      |
| PUT    | `/bucketlists/<pk>` | Update list        |
| DELETE | `/bucketlists/<pk>` | Delete list        |

Example request:

```json
{
  "title": "Travel Ideas",
  "description": "Things we want to do together"
}
```

## Bucket List Item Endpoints

| Method | Endpoint                   | Description    |
| ------ | -------------------------- | -------------- |
| GET    | `/bucketlists/<pk>/items/` | Retrieve items |
| POST   | `/bucketlists/<pk>/items/` | Create item    |

Example request:

```json
{
  "bucket_list": 2,
  "title": "Visit Bondi Beach",
  "description": "Sunrise swim and breakfast"
}
```

# Object Definitions

## BucketList

Stores:

* list metadata
* owner
* deadline
* viewer voting setting

Responsible for:

* collaboration rules
* voting configuration

---

## BucketListMembership

Connects users to lists.

Fields include:

* user
* bucket_list
* role
* joined_at

Constraint:

```
unique(bucket_list, user)
```

---

## BucketListItem

Represents proposed activities.

Fields:

* title
* description
* status
* creator
* timestamps

Statuses:

```
proposed
locked_in
complete
cancelled
```

---

## ItemVote

Stores user votes.

Fields:

* user
* item
* vote_type

Constraint:

```
unique(item, user)
```

---

## BucketListInvite

Stores invite tokens.

Fields:

* role
* token
* expiry
* active state

---

# Database Schema

Placeholder diagram:

```
User
 │
 │
 ├── BucketList (owner)
 │
 │
 ├── BucketListMembership
 │       │
 │       └── Role
 │
 ├── BucketListItem
 │       │
 │       └── ItemVote
 │
 └── BucketListInvite
```

*(Final diagram to be added once schema is finalised.)*

---

# Development Setup

Clone repository:

```
git clone <repository-url>
```

Create virtual environment:

```
python -m venv venv
```

Activate environment:

Mac/Linux

```
source venv/bin/activate
```

Windows

```
venv\Scripts\activate
```

Install dependencies:

```
pip install -r requirements.txt
```

Run migrations:

```
python manage.py migrate
```

Run server:

```
python manage.py runserver
```

---

# Testing

API endpoints are tested using **Insomnia**.

Import the provided collection:

```
Insomnia_2026-03-07.yaml
```

Base URL:

```
http://127.0.0.1:8000
```

Testing workflow:

1. Authenticate using `/api/token/`
2. Copy returned token
3. Use token for protected endpoints
4. Create bucket lists
5. Add items
6. Test permissions

---

# Deployment

Backend:

* Heroku or Render

Frontend:

* Netlify or Vercel

Database:

* PostgreSQL

---

# Future Enhancements

Planned improvements:

* Item comments
* Real-time voting updates
* Notifications
* Image uploads
* Public bucket lists
* Analytics for most popular activities