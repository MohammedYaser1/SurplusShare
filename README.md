# Surplus Share

A web platform for connecting surplus food from businesses with charities and individuals who need it, helping coordinate discovery, requests, communication, and pickup.

[![CI](https://github.com/MohammedYaser1/SurplusShare/actions/workflows/ci.yml/badge.svg)](https://github.com/MohammedYaser1/SurplusShare/actions/workflows/ci.yml)

## Overview

Surplus Share is a Flask and PostgreSQL application built around a simple workflow:

```text
List surplus food
      ↓
Discover nearby availability
      ↓
Submit a request
      ↓
Coordinate pickup
      ↓
Complete the transfer
```

The application supports both sides of the exchange. Donors can publish available food, while recipients and charities can discover listings, request them, communicate with donors, and coordinate pickup.

## Features

- Donor, recipient, and charity accounts
- Food listings with quantity, category, description, and expiry
- Location-based proximity matching
- Interactive map using Leaflet and OpenStreetMap
- Request and approval workflow
- Pickup scheduling and completion tracking
- In-app conversations and messaging
- PostgreSQL persistence through SQLAlchemy
- Password hashing with Werkzeug
- Geocoding through OpenStreetMap Nominatim

## Technology

| Layer | Technology |
| --- | --- |
| Backend | Python, Flask |
| ORM | Flask-SQLAlchemy |
| Database | PostgreSQL |
| Frontend | HTML, CSS, JavaScript, Jinja |
| Mapping | Leaflet, OpenStreetMap |
| Geocoding | Nominatim |
| Deployment server | Gunicorn |

## Repository structure

```text
SurplusShare/
├── app.py
├── seed.py
├── requirements.txt
├── .env.example
├── SECURITY.md
├── docs/
│   └── architecture.md
├── static/
│   ├── css/
│   ├── js/
│   └── img/
└── templates/
```

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/MohammedYaser1/SurplusShare.git
cd SurplusShare
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and set:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/surplus_share
SECRET_KEY=replace-with-a-long-random-secret
```

Use a real PostgreSQL database for the application. Do not commit the resulting `.env` file.

### 5. Initialize the database

The application creates its tables when started directly:

```bash
python app.py
```

For demo data, run:

```bash
python seed.py
```

> The seed script resets the application tables before inserting sample users and listings. Use it only with a development/demo database.

### 6. Run the application

```bash
python app.py
```

Open the local address printed by Flask in your browser.

For a production-style server:

```bash
gunicorn app:app
```

## Demo accounts

The seed script creates sample donor, charity, and recipient accounts for local demonstrations. Credentials are defined in `seed.py` and are intended only for development/demo use.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the request flow, core workflows, and repository layout.

## Project status

Surplus Share is a completed collaborative project demonstrating a full-stack workflow for surplus-food discovery and pickup coordination.

## Authors

Developed collaboratively by **Mohammed Yaser** and **Abdullah Ghouri**.

## Notes

This repository contains the application source and supporting assets. Production credentials, deployment secrets, and private service-account files should be supplied through the hosting environment rather than stored in Git.
