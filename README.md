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

```bash
# Clone repo
git clone https://github.com/AminaAzzmouri/skillfolio-backend.git

# Create virtual environment
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run server
python manage.py runserver
```
