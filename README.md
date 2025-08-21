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

# 8. Create the users app (feature/user-model branch):

# Inside the Django project folder (where manage.py is located), run:

python manage.py startapp users

**App Explanation:**  
 The `users` app serves as the central place for user-related models and functionality. By keeping all user, certificate, project, and goal-related models in this single app, we avoid unnecessary app fragmentation. This approach simplifies relationships between models, reduces overhead in project structure, and keeps the code easier to maintain, especially in a project where all features are tightly related to users’ achievements and certificates.

# Make sure to add 'users' to INSTALLED_APPS in settings.py:

INSTALLED_APPS = [
...,
'rest_framework',
'users', # <-- newly created app
]

---

## Branching Strategy

- **chore/django-setup:**  
  Initial project setup, including Django project creation, virtual environment, and basic configurations.

---

- **feature/user-model:**

  **Purpose:** Prepare the `users` app and the User model for future customization. This branch ensures the backend is ready for authentication and user-related features.

  **Current Status:**

  - `users` app created
  - `models.py` includes a placeholder for the User model (no custom fields yet)
  - Added `users` to `INSTALLED_APPS` in settings.py

  **Next Steps:**

  - Customize the User model if needed
  - Setup authentication (register, login, logout, JWT)
  - Integrate User model with Certificates and Projects when those models are added

---

- **feature/certificate-model:**

  **Purpose:** Implement the Certificate model, enabling users to upload, manage, and associate certificates with their accounts. This branch sets up the model, serializers, views, and API endpoints for certificates.

  **Current Status:**

  - Certificate model created in `users/models.py`
  - Admin registration completed
  - Serializer and views prepared
  - URLs configured for CRUD operations

  **Next Steps:**

  - Test certificate APIs
  - Add validations or additional fields if needed
  - Integrate with frontend endpoints

---

- **feature/project-model:**

  **Purpose:** Implement the Project model, allowing users to document their projects and link them with certificates. This branch focuses on building a structure where achievements and certificates can be contextualized with practical applications (projects).

  **Current Status:**

  - Project model created in `users/models.py`
  - Admin registration completed
  - Serializer and views prepared
  - URLs configured for CRUD operations
  - Initial fields: title, description, related certificate, created_at

  **Next Steps:**

  - Add guided questions to help users describe their projects (e.g., problem solved, tools used, impact achieved)
  - Introduce project status (planned, in progress, completed)
  - Connect projects to specific skills for better tracking
  - Test API endpoints for projects and prepare for frontend integration

---

- **fix/<fix-name>:** Bug fixes

---

- **experiment/<experiment-name>:** Experimental changes
