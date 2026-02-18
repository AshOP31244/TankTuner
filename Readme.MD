# 🏭 TankTuner — Industrial Tank Costing & Project Management Platform

> Built for **Shubham Tanks and Liners Pvt. Ltd.** to streamline tank costing, project tracking, and analytics.

🔗 **Live Demo:** [tanktuner-production.up.railway.app](https://tanktuner-production.up.railway.app)

---

## 📌 Overview

TankTuner is a full-stack web application developed specifically for Shubham Tanks and Liners Pvt. Ltd. to digitize and automate their tank costing workflow. The platform replaces manual Excel-based costing with a centralized, intelligent system that allows engineers and managers to upload costing sheets, tune parameters, track project snapshots, and gain analytical insights — all from a single dashboard.

---

## ✨ Key Features

- **📊 Project Dashboard** — Centralized view of all active and past tank projects with status tracking
- **📁 Excel Costing Sheet Upload** — Upload `.xlsx` costing sheets directly into the system with automatic data parsing using `pandas` and `openpyxl`
- **🔧 Model Tuner** — Fine-tune tank parameters (thickness, material, dimensions) and instantly see cost impact
- **📸 Project Snapshots** — Save versioned snapshots of project states for comparison and audit trail
- **📈 Project Analytics** — Visual analytics and cost breakdowns per project
- **👤 User Authentication** — Secure login system with role-based access
- **🔒 Admin Panel** — Django admin interface for managing users, projects, and data
- **📱 Responsive UI** — Clean, professional interface accessible across devices

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.2 (Python) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Data Processing** | Pandas, NumPy, OpenPyXL |
| **Database** | SQLite (dev) / PostgreSQL (prod-ready) |
| **Static Files** | WhiteNoise |
| **Deployment** | Railway (Cloud) |
| **Version Control** | Git + GitHub |
| **Server** | Gunicorn (WSGI) |

---

## 🗂️ Project Structure

```
TankTuner/
├── TankTuner/              # Django project config
│   ├── settings.py         # Environment-based settings
│   ├── urls.py             # Root URL configuration
│   └── wsgi.py             # WSGI entry point
├── costing/                # Core application
│   ├── models.py           # Database models
│   ├── views.py            # Business logic & views
│   ├── urls.py             # App URL routing
│   ├── services/           # Data processing services
│   ├── templates/          # HTML templates
│   └── static/             # CSS, JS, images
├── manage.py
├── requirements.txt
└── build.sh                # Railway/Render build script
```

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.10+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/AshOP31244/TankTuner.git
cd TankTuner

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Start development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

---

## ⚙️ Environment Variables

Create a `.env` file or set these in your deployment platform:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for dev, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DATABASE_URL` | PostgreSQL URL (optional, defaults to SQLite) |

---

## 🌐 Deployment

The app is deployed on **Railway** with automatic deploys from the `main` branch.

Build process is handled by `build.sh`:
```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

---

## 📷 Application Screenshots

| Dashboard | Project Detail | Analytics |
|-----------|---------------|-----------|
| Overview of all projects | Per-project costing view | Visual cost breakdowns |

---

## 👨‍💻 Developer

**Ashwaz** — Designed, developed, and deployed end-to-end for Shubham Tanks and Liners Pvt. Ltd.

- GitHub: [@AshOP31244](https://github.com/AshOP31244)

---

## 🏢 Client

**Shubham Tanks and Liners Pvt. Ltd.**
Industrial tank manufacturer specializing custom tank solutions.

---

## 📄 License

This project is proprietary software developed exclusively for Shubham Tanks and Liners Pvt. Ltd.