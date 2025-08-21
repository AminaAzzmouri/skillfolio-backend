# Skillfolio Backend

This is the backend of **Skillfolio**, a web application that helps self-learners archive their certificates, track skills, and connect achievements to projects.

Built with **Django REST Framework**, the backend provides secure APIs for authentication, certificate management, and project linking.

---

## 🚀 Features (Planned)

- User authentication (register, login, logout, JWT)
- Upload and manage certificates (PDF, with metadata: title, date, specialty)
- CRUD for achievements
- Link projects to certificates (with guided description form)
- REST API endpoints for the frontend

---

## 🛠️ Tech Stack

- Python / Django
- Django REST Framework (DRF)
- MySQL (production) / SQLite (development)
- JWT Authentication

---

## 📅 Project Timeline

- Week 3: Django project setup + authentication
- Week 4: Certificates & achievements models + APIs
- Week 5: Testing, polish, deployment

---

## ⚡ Getting Started

# Project Setup Instructions:

# 1. Clone repo

git clone https://github.com/AminaAzzmouri/skillfolio-backend.git

# 2. Create a virtual environment

python -m venv venv

# 3. Activate the virtual environment:

    - Windows: venv\Scripts\activate
    - macOS/Linux: source venv/bin/activate

# 4. Install dependencies

pip install django
pip install -r requirements.txt

# 5. Start the Django project:

django-admin startproject skillfolio_backend

# 6. Apply migrations:

python manage.py migrate

# 7. Run the server:

python manage.py runserver

---

## Branching Strategy

- chore/django-setup: Initial project setup, including Django project creation, virtual environment, and basic configurations.

- feature/user-model:

\*\*\* Purpose: Prepare the users app and the User model for future customization. This branch ensures the backend is ready for authentication and user-related features.

\*\*\* Current Status: > users app created > models.py includes a placeholder for the User model > No custom fields added yet

\*\*\* Next Steps: > Customize the User model if needed > Setup authentication (register, login, logout, JWT) > Integrate User model with Certificates and Projects when those models are added

- fix/<fix-name>: Bug fixes

- experiment/<experiment-name>: Experimental changes
