# Surplus Share Architecture

Surplus Share is a Flask web application backed by PostgreSQL. The application separates presentation, application logic, persistence, and browser-side mapping assets while keeping the deployment footprint small.

## Request flow

```text
Browser
  │
  ├── Jinja templates
  ├── CSS / JavaScript
  └── Leaflet map
        │
        ▼
     Flask app
        │
        ├── Authentication and sessions
        ├── Food listing workflow
        ├── Requests and pickup scheduling
        ├── Messaging
        └── Location matching / geocoding
        │
        ▼
   SQLAlchemy
        │
        ▼
    PostgreSQL
```

## Main workflows

### Donor workflow

A donor registers, creates a food listing, provides quantity/category/expiry information, and receives requests from nearby recipients or charities.

### Recipient workflow

A recipient or charity browses available listings, sees proximity information, submits a request, and uses messaging to coordinate pickup.

### Location workflow

Addresses are geocoded through OpenStreetMap Nominatim. Latitude/longitude values are stored with users and listings so the application can calculate approximate proximity and populate the map.

### Messaging workflow

Users can open conversations with other participants, exchange pickup-related messages, and mark received messages as read.

## Repository layout

- `app.py` — Flask routes, models, business logic, and application startup
- `seed.py` — local/demo database seed data
- `templates/` — Jinja HTML views
- `static/css/` — application styles
- `static/js/` — browser-side behavior and map logic
- `static/img/` — project branding and visual assets
- `requirements.txt` — Python dependencies
- `.env.example` — required environment variables

## Data model

The core entities are:

- `User` — donor, recipient, or charity account
- `FoodListing` — surplus food available for pickup
- `FoodRequest` — request and pickup lifecycle
- `Message` — participant-to-participant communication
