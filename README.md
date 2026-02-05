``
# Fire Rescue Service DB (FRS_DB_Project)

A web-based multi-tenant application for managing fire rescue service data, 
built with Django 6.0 and containerized using Docker. 
This system supports multiple organizations (companies), user roles, 
and membership handling.

---

## 🚀 Features

- 🔐 **Authentication and User Management**
- 🏢 **Multi-tenant architecture** with `Company` and `CompanyMembership` models
- 🖼️ Company logos and short name identifiers
- 🔒 Role-based access via company-user relationships
- 📄 Customizable landing pages (`home`, `main`, and `under construction`)
- ⚙️ Built-in Django admin support
- 🐳 Docker-based deployment
- 📦 Environment-based configuration using `.env`

---

## 🗂️ Project Structure
FRS_DB_Project/
├── FireService_DB/          # Django project settings, views, URLs
├── companies/               # Company models, views, admin, and middleware
├── users/, persons/         # User and profile management apps (namespaced)
├── Docker/                  # Docker-related configurations (nginx, scripts)
├── db.sqlite3               # SQLite database for development
├── manage.py                # Django CLI entry point
├── docker-compose.yml       # Multi-container Docker config
├── .env                     # Environment variables
├── pyproject.toml           # Python dependencies and project config

---

## 🧪 Requirements

- Python 3.12+
- Django 6.0.1
- Docker & Docker Compose
- `python-dotenv` for environment management

Install Python packages (locally):

pip install -r requirements.txt  # if available


🛠️ Setup Instructions

1. Clone the Repository

git clone https://your-repo-url.git
cd FRS_DB_Project

2. Environment Configuration

Create a .env file in the root:

DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

3. Run with Docker

docker-compose up --build

4. Apply Migrations

docker-compose exec web python manage.py migrate

5. Create Superuser (Admin)

docker-compose exec web python manage.py createsuperuser

🌐 Accessing the App
	•	Web Interface: http://localhost:8000￼
	•	Admin Panel: http://localhost:8000/admin/￼

🧩 Apps Overview
	•	companies: Manages companies, memberships, and associated logic.
	•	users, persons: User authentication and user-profile handling.
	•	FireService_DB: Core Django project (settings, URLs, base views).

🧹 To-Do / Improvements
	•	Add role-based access control to CompanyMembership
	•	Write unit tests for company and membership logic
	•	Add more detailed frontend templates
	•	Add API support (e.g., Django REST Framework)
	•	Replace SQLite with PostgreSQL in production
