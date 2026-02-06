# Fire Rescue Service DB (FRS_DB_Project)

A web-based multi-tenant application for managing Fire Rescue Service data.  
Built with **Django 6.0**, containerized using **Docker**, and designed for
multi-company (multi-tenant) operation with safe backup and restore workflows.

---

## 🚀 Features

- 🔐 **Authentication & User Management**
- 🏢 **Multi-tenant architecture**
  - Companies
  - Company memberships
  - Active company context via middleware
- 👤 Custom user model linked to personnel records
- 🖼️ Company branding (name, short name, logo-ready)
- 🔒 Role-aware access via company-user relationships
- 📄 Multiple entry pages (`home`, `main`, `under construction`)
- ⚙️ Django Admin enabled
- 🐳 Fully Dockerized (PostgreSQL + Django + Nginx)
- 🔐 HTTPS support via Nginx (local dev certs)
- 💾 **Safe database backup & restore**
- ⚙️ Environment-based configuration via `.env`
- 🧠 Automatic DB selection (SQLite locally, PostgreSQL in Docker)

---

## 🗂️ Project Structure
FRS_DB_Project/
├── FireService_DB/          # Django project (settings, URLs, WSGI)
├── companies/               # Company & membership logic + middleware
├── users/                   # Custom user model
├── persons/                 # Personnel profiles
├── Docker/                  # Dockerfiles & nginx config
├── templates/               # HTML templates
├── static/                  # Static source files
├── staticfiles/             # Collected static files (Docker)
├── media/                   # Uploaded media
├── backups/                 # PostgreSQL backups (host-mounted)
├── docker-compose.yml       # Docker services definition
├── Makefile                 # Project control commands
├── manage.py                # Django CLI entry point
├── pyproject.toml           # Python dependencies
├── uv.lock                  # Locked dependency versions
├── .env                     # Environment variables (not committed)

---

## 🧪 Requirements

### Local Development
- Python **3.12+**
- Docker & Docker Compose v2
- `uv` (dependency manager)

### Docker Images
- `postgres:16`
- `nginx:alpine`

---

## 🔐 Environment Configuration

Create a `.env` file in the project root:


DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True

POSTGRES_DB=frs_db
POSTGRES_USER=frs_user
POSTGRES_PASSWORD=strong_password
POSTGRES_PORT=5432

⚠️ Do not commit .env to version control.

⸻

🐳 Running the Project (Recommended)

Start everything

make up

Apply migrations

make migrate

Collect static files

make collectstatic

Create admin user

make createsuperuser

🌐 Access
	•	Web UI (HTTPS): https://localhost
	•	Admin Panel: https://localhost/admin/

Self-signed certificates are used for local development.

⸻

💾 Database Backup & Restore

Create a safe backup

make backup

	•	Stored in ./backups/frs_db_latest.sql.gz
	•	Guaranteed non-empty (fails if dump is invalid)

Restore database (⚠️ destructive)

make restore

What it does automatically:
	1.	Drops public schema
	2.	Recreates schema
	3.	Restores dump
	4.	Fails immediately on any SQL error

✅ No manual cleanup required
❌ Existing data will be fully replaced

⸻

🛠️ Useful Make Commands

make up                 # Start all services
make down               # Stop all services
make restart            # Restart containers
make rebuild            # Full rebuild (no cache)
make logs               # Tail container logs
make shell              # Shell inside web container

make migrate            # Apply Django migrations
make createsuperuser    # Create admin user
make collectstatic      # Collect static files
make test               # Run Django tests

make backup             # Create PostgreSQL backup
make restore            # Restore DB from latest backup
make reset-db           # Drop & recreate public schema (dangerous)

🧠 Database Selection Logic
	•	Local (non-Docker) → SQLite (db.sqlite3)
	•	Docker → PostgreSQL
	•	Controlled automatically via runtime detection (IN_DOCKER)

No manual flags required.

⸻

🧩 Apps Overview
	•	companies
	•	Company model
	•	CompanyMembership
	•	Active company middleware
	•	users
	•	Custom Django user
	•	persons
	•	Personnel records linked to users
	•	FireService_DB
	•	Project configuration, routing, base views

⸻

🧹 Future Improvements
	•	Fine-grained role permissions per company
	•	API layer (Django REST Framework)
	•	Automated scheduled backups
	•	Audit logging
	•	Improved frontend UX
	•	Production hardening (CSP, HSTS, strict ALLOWED_HOSTS)

⸻

📌 Notes

This project is designed for predictability and operational safety:
	•	No silent DB restores
	•	No hidden Docker state
	•	Explicit, repeatable workflows via Makefile

⸻

📄 License

Internal / Private project
(Define license if publishing externally)
---

